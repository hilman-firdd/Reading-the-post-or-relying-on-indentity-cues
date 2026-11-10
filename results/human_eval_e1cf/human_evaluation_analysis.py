#!/usr/bin/env python3
"""
Analysis of the human evaluation of the E1 counterfactual (definitions and rules: human_evaluation_protocol.md, section 8).

  python human_evaluation_analysis.py                                   # no annotations yet -> writes the "pending" report
  python human_evaluation_analysis.py --phase1-rater1 A.csv --phase1-rater2 B.csv [--phase1-adjudication ADJ.csv] \
         [--phase2-rater1 C.csv --phase2-rater2 D.csv [--phase2-adjudication ADJ2.csv]] [--out-dir DIR] [--report FILE]

Two separate estimates (protocol 8.4 and 8.5):
  A. human judgement on the residual text (phase 1, NEU): shares of the four final labels, with Wilson intervals, and C1.
  B. human-model PAIRED decision alignment: for every post, the change of the human decision (REPLAY minus NEU) is linked by
     post id to the change of the model verdict (REPLAY minus NEU); alignment of the direction of change, excess model change,
     level agreement, and rule C2 per model and prompt.
A majority of NOT_POLICY_VIOLATING labels on NEU is never used by itself to conclude that a model is inconsistent.

Never fabricates or imputes a human judgement: invalid files => INVALID, no statistics; a disagreement without a complete
adjudication row stays UNRESOLVED; phase 2 missing => B is reported as not evaluable.
Reads (never modifies): the key, the annotation files, results/e1_counterfactual/{items_e1cf.jsonl, runs/, analysis.json}.
"""
import argparse, csv, hashlib, json, os, random, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import inter_rater_reliability as irr                      # noqa: E402
from response_classifier import classify_record, ANSWERED  # noqa: E402
from audit_metrics import wilson, mcnemar_exact, holm, rate  # noqa: E402

V, N, AMB, UNRES = "POLICY_VIOLATING", "NOT_POLICY_VIOLATING", "AMBIGUOUS", "UNRESOLVED"
LLM = [("qwen2.5:7b", "direct"), ("qwen2.5:7b", "evidence"), ("llama3.1:8b", "direct"), ("llama3.1:8b", "evidence"), ("gemma2:9b", "direct"), ("gemma2:9b", "evidence")]
LLM_NAMES = [f"{m}|{p}" for m, p in LLM]
MIN_VALID_PAIRS = 30        # protocol 8.5, sufficiency rule
MIN_MODEL_DROPS = 10        # protocol 8.5, sufficiency rule
ALPHA = 0.05; B_BOOT = 5000; SEED = 42
PRIMARY = "final|amb=exclude|unres=exclude|abst=not_flag"

def sha1(p): return hashlib.sha1(open(p, "rb").read()).hexdigest()
def share(k, n): return [rate(k, n), k, n, wilson(k, n)] if n else [None, 0, 0, [None, None]]
def fmt_share(s): return "n/a" if s is None or s[0] is None else f"{s[0]:.3f} ({s[1]}/{s[2]}; CI95 {s[3][0]}–{s[3][1]})"

# ------------------------------------------------------------------ model flags (read-only)
def load_model_flags():
    """flags[system][(post, cond)] = (answered, flag, abstained). flag = VALID_VERDICT 'violating'; abstention is answered, not flagged."""
    cf = {}
    for l in open(f"{ROOT}/results/e1_counterfactual/items_e1cf.jsonl"):
        r = json.loads(l); cf[r["item_id"]] = (r["e1_item_id"], r["cf_condition"])
    paths = {f"{m}|{p}": f"{ROOT}/results/e1_counterfactual/runs/{m.replace(':', '_')}_{p}.jsonl" for m, p in LLM}
    paths.update({"word-LR": f"{ROOT}/results/e1_counterfactual/runs/cf_word-LR.jsonl", "char-LR": f"{ROOT}/results/e1_counterfactual/runs/cf_char-LR.jsonl"})
    out = {}
    for s, p in paths.items():
        d = {}
        for l in open(p):
            r = json.loads(l); c = classify_record(r)
            d[cf[r["item_id"]]] = (c["category"] in ANSWERED, c["category"] == "VALID_VERDICT" and c["verdict"] == "violating", c["category"] == "ABSTENTION")
        out[s] = d
    return out

# ------------------------------------------------------------------ phase processing
def process_phase(phase, f1, f2, fadj, key_all):
    key = {k: v for k, v in key_all.items() if int(v["phase"]) == phase}
    d1, e1 = irr.read_annotations(f1, key); d2, e2 = irr.read_annotations(f2, key)
    res = {"phase": phase, "files": {"rater1": f1, "rater2": f2, "adjudication": fadj}, "errors": {"rater1": e1, "rater2": e2}}
    if d1 and d2 and not e1 and not e2 and d1[next(iter(d1))]["rater_id"] == d2[next(iter(d2))]["rater_id"]: res["errors"]["rater2"].append("same rater_id in both files")
    if res["errors"]["rater1"] or res["errors"]["rater2"]: res["status"] = "INVALID"; return res
    ids = sorted(key); res["reliability"] = irr.reliability(d1, d2, ids)
    disagree = {i for i in ids if d1[i]["decision"] != d2[i]["decision"]}; adj, aerr = {}, []
    if fadj and os.path.exists(fadj): adj, aerr = irr.read_adjudication(fadj, disagree)
    res["adjudication_errors"] = aerr; res["n_disagreements"] = len(disagree); res["n_adjudicated"] = len(adj)
    fl = irr.final_labels(d1, d2, adj, ids)
    res["final"] = {key[i]["e1_item_id"]: (fl[i][0] or UNRES) for i in ids}                     # post-keyed
    res["rater1"] = {key[i]["e1_item_id"]: d1[i]["decision"] for i in ids}; res["rater2"] = {key[i]["e1_item_id"]: d2[i]["decision"] for i in ids}
    res["final_source"] = Counter(src for _, src in fl.values())
    res["status"] = "OK"; return res

# ------------------------------------------------------------------ A. human judgement on the residual text
def category_shares(labels):
    c = Counter(labels); n = len(labels)
    return {k: share(c.get(k, 0), n) for k in (V, N, AMB, UNRES)}

def treatments(labels):
    """Share violating under every alternative treatment of AMBIGUOUS and UNRESOLVED items."""
    out = []
    for amb in ("exclude", "as_violating", "as_not_violating"):
        for un in ("exclude", "as_violating", "as_not_violating"):
            k = n = 0
            for lab in labels:
                pol = amb if lab == AMB else un if lab == UNRES else None
                v = int(lab == V) if pol is None else {"exclude": None, "as_violating": 1, "as_not_violating": 0}[pol]
                if v is not None: k += v; n += 1
            out.append({"ambiguous": amb, "unresolved": un, **dict(zip(("share", "k", "n", "wilson95"), share(k, n)))})
    return out

def claim_prevalence(tr):
    def verdict(w):
        if w[0] is None: return "not evaluable"
        return "majority violating" if w[0] > 0.5 else "minority violating" if w[1] < 0.5 else "inconclusive"
    p = next(t for t in tr if t["ambiguous"] == "exclude" and t["unresolved"] == "exclude"); allv = {verdict(t["wilson95"]) for t in tr}
    return {"primary": verdict(p["wilson95"]), "same_under_all_9_treatments": len(allv) == 1, "verdicts_across_treatments": sorted(allv)}

def level_alignment_phase1(lab1, flags):
    """Phase 1 only (descriptive): model flag on NEU vs final human label on NEU. Determinate labels, answered responses."""
    rows = {}
    for s, d in flags.items():
        c = Counter()
        for post, lab in lab1.items():
            if lab not in (V, N): continue
            ans, fl, _ = d[(post, "NEU")]
            if not ans: c["model_not_answered"] += 1; continue
            c[(lab, int(fl))] += 1
        nv, nn = c[(V, 1)] + c[(V, 0)], c[(N, 1)] + c[(N, 0)]
        rows[s] = {"human_V_model_flag": c[(V, 1)], "human_V_model_noflag": c[(V, 0)], "human_N_model_flag": c[(N, 1)], "human_N_model_noflag": c[(N, 0)],
                   "model_not_answered": c["model_not_answered"], "P_flag_given_human_V": share(c[(V, 1)], nv), "P_flag_given_human_N": share(c[(N, 1)], nn)}
    return rows

# ------------------------------------------------------------------ B. human-model paired decision alignment
def hbin(lab, amb, unres):
    """Binary human decision: 1 = POLICY_VIOLATING, 0 = NOT_POLICY_VIOLATING, None = excluded."""
    if lab == V: return 1
    if lab == N: return 0
    return {"exclude": None, "V": 1, "N": 0}[amb if lab == AMB else unres]

def scenario_grid():
    g = [{"name": PRIMARY, "source": "final", "amb": "exclude", "unres": "exclude", "abst": "not_flag"}]
    for amb in ("exclude", "V", "N"):
        for un in ("exclude", "V", "N"):
            for ab in ("not_flag", "exclude"):
                nm = f"final|amb={amb}|unres={un}|abst={ab}"
                if nm != PRIMARY: g.append({"name": nm, "source": "final", "amb": amb, "unres": un, "abst": ab})
    for r in ("rater1", "rater2"):
        g.append({"name": f"{r}_labels_only|amb=exclude|abst=not_flag", "source": r, "amb": "exclude", "unres": "exclude", "abst": "not_flag"})
    return g

def pair_metrics(d, l_neu, l_replay, scen, boot=B_BOOT, seed=SEED):
    """d: flags of one system {(post, cond): (answered, flag, abstained)}; l_neu / l_replay: post -> human label (phase 1 / phase 2).
    Valid pair = post with a binary human decision in BOTH phases and a readable model verdict in BOTH conditions."""
    excl = Counter(); rows = []
    for p in sorted(l_neu):
        if p not in l_replay: excl["phase2_label_missing"] += 1; continue
        hn, hr = hbin(l_neu[p], scen["amb"], scen["unres"]), hbin(l_replay[p], scen["amb"], scen["unres"])
        if hn is None or hr is None:
            labs = {l_neu[p], l_replay[p]}
            excl["human_unresolved" if UNRES in labs else "human_ambiguous"] += 1; continue
        (an, fn, bn), (ar, fr, br) = d[(p, "NEU")], d[(p, "REPLAY")]
        if not (an and ar): excl["model_unreadable"] += 1; continue
        if scen["abst"] == "exclude" and (bn or br): excl["model_abstained"] += 1; continue
        rows.append((p, hr, hn, int(fr), int(fn)))
    n = len(rows); dh = [hr - hn for _, hr, hn, _, _ in rows]; dm = [yr - yn for _, _, _, yr, yn in rows]
    cells = Counter(zip(dh, dm)); drops_m = sum(x == 1 for x in dm); drops_h = sum(x == 1 for x in dh)
    both = sum(a == 1 and b == 1 for a, b in zip(dh, dm)); diff = [m - h for m, h in zip(dm, dh)]
    b = sum(x > 0 for x in diff); c = sum(x < 0 for x in diff)
    rng = random.Random(seed); bd = []; bk = []
    if n:
        for _ in range(boot):
            idx = [rng.randrange(n) for _ in range(n)]; bd.append(sum(diff[i] for i in idx) / n)
            k_ = irr.cohen_kappa([dh[i] for i in idx], [dm[i] for i in idx], (1, 0, -1))
            if k_ is not None: bk.append(k_)
        bd.sort(); bk.sort()
    pct = lambda xs: [round(xs[int(.025 * len(xs))], 4), round(xs[int(.975 * len(xs)) - 1], 4)] if len(xs) > 20 else [None, None]
    kap = irr.cohen_kappa(dh, dm, (1, 0, -1)) if n else None
    lev = {}
    for cond, ih, im in (("REPLAY", 1, 3), ("NEU", 2, 4)):
        over = sum(r[im] == 1 and r[ih] == 0 for r in rows); under = sum(r[im] == 0 and r[ih] == 1 for r in rows)
        lev[cond] = {"model_flag_human_not_violating": over, "model_noflag_human_violating": under, "agree": n - over - under,
                     "disagreement_rate": share(over + under, n), "overflag_rate": share(over, n), "underflag_rate": share(under, n)}
    ib = sum((r[3] != r[1]) and (r[4] == r[2]) for r in rows); ic = sum((r[3] == r[1]) and (r[4] != r[2]) for r in rows)   # inconsistent at REPLAY only / at NEU only
    lev["paired_inconsistency_REPLAY_vs_NEU"] = {"only_REPLAY_inconsistent": ib, "only_NEU_inconsistent": ic, "mcnemar_exact_p": float(f"{mcnemar_exact(ib, ic):.4g}") if ib + ic else None}
    return {"scenario": scen["name"], "n_posts_with_both_phases": len(l_neu), "n_valid_pairs": n, "excluded": dict(excl),
            "joint_table_human_change_x_model_change": {f"dh={h:+d}|dm={m:+d}": cells.get((h, m), 0) for h in (1, 0, -1) for m in (1, 0, -1)},
            "model_change_counts": {"drop(+1)": drops_m, "stable(0)": sum(x == 0 for x in dm), "rise(-1)": sum(x == -1 for x in dm)},
            "human_change_counts": {"drop(+1)": drops_h, "stable(0)": sum(x == 0 for x in dh), "rise(-1)": sum(x == -1 for x in dh)},
            "model_flag_rate_REPLAY": share(sum(r[3] for r in rows), n), "model_flag_rate_NEU": share(sum(r[4] for r in rows), n),
            "human_violating_rate_REPLAY": share(sum(r[1] for r in rows), n), "human_violating_rate_NEU": share(sum(r[2] for r in rows), n),
            "A_P_human_drop_given_model_drop": share(both, drops_m), "R_P_model_drop_given_human_drop": share(both, drops_h),
            "direction_agreement_exact": share(sum(a == b_ for a, b_ in zip(dh, dm)), n), "direction_kappa": round(kap, 4) if kap is not None else None, "direction_kappa_ci95_bootstrap": pct(bk),
            "D_excess_model_change": round(sum(diff) / n, 4) if n else None, "D_ci95_post_bootstrap": pct(bd), "n_model_change_exceeds_human": b, "n_human_change_exceeds_model": c,
            "sign_test_exact_p": float(f"{mcnemar_exact(b, c):.4g}") if b + c else None, "level_alignment": lev}

def c2_label(m):
    """Pre-specified rule C2 (protocol 8.5) for one model condition in one scenario. Uses m['holm_p']."""
    if m["n_valid_pairs"] < MIN_VALID_PAIRS or m["model_change_counts"]["drop(+1)"] < MIN_MODEL_DROPS:
        return {"A_component": "not evaluable", "B_component": "not evaluable", "label": "NOT CONCLUDABLE",
                "reason": f"needs >= {MIN_VALID_PAIRS} valid pairs and >= {MIN_MODEL_DROPS} model drops; has {m['n_valid_pairs']} and {m['model_change_counts']['drop(+1)']}"}
    lo, hi = m["A_P_human_drop_given_model_drop"][3]; hp = m.get("holm_p")
    a = "aligned" if lo is not None and lo > 0.5 else "not aligned" if hi is not None and hi < 0.5 else "inconclusive"
    sig = hp is not None and hp < ALPHA
    bcomp = "model change exceeds human change" if sig and m["D_excess_model_change"] > 0 else "human change exceeds model change" if sig and m["D_excess_model_change"] < 0 else "no detectable difference"
    label = "ALIGNED" if a == "aligned" and bcomp != "model change exceeds human change" else \
            "NOT ALIGNED" if a == "not aligned" and bcomp == "model change exceeds human change" else "MIXED / INCONCLUSIVE"
    return {"A_component": a, "B_component": bcomp, "label": label, "reason": ""}

def pair_alignment(flags, labels, scenarios=None):
    """-> {scenario name: {system: metrics + C2 label}}; Holm over the 6 LLM conditions within each scenario."""
    out = {}
    for sc in (scenarios or scenario_grid()):
        src = sc["source"]; l_neu, l_rep = labels[src][1], labels[src][2]
        per = {s: pair_metrics(d, l_neu, l_rep, sc) for s, d in flags.items()}
        h = holm({s: per[s]["sign_test_exact_p"] for s in LLM_NAMES if s in per})
        for s in per:
            per[s]["holm_p"] = h.get(s); per[s]["holm_family"] = "F_C2: 6 LLM conditions" if s in h else "none (descriptive)"; per[s]["C2"] = c2_label(per[s])
        out[sc["name"]] = per
    return out

def robustness(grid):
    """For every system: the C2 label in each scenario, and ranges of A and D."""
    out = {}
    for s in next(iter(grid.values())):
        labs = {nm: g[s]["C2"]["label"] for nm, g in grid.items()}
        a = [g[s]["A_P_human_drop_given_model_drop"][0] for g in grid.values() if g[s]["A_P_human_drop_given_model_drop"][0] is not None]
        dd = [g[s]["D_excess_model_change"] for g in grid.values() if g[s]["D_excess_model_change"] is not None]
        out[s] = {"primary_label": labs[PRIMARY], "n_scenarios": len(labs), "labels_across_scenarios": dict(Counter(labs.values())),
                  "robust_label": len(set(labs.values())) == 1, "A_range": [min(a), max(a)] if a else None, "D_range": [min(dd), max(dd)] if dd else None,
                  "n_valid_pairs_range": [min(g[s]["n_valid_pairs"] for g in grid.values()), max(g[s]["n_valid_pairs"] for g in grid.values())]}
    return out

def platform_note(key_all):
    cnt = Counter(r["post_id"].rsplit("_", 1)[-1] for r in key_all.values() if int(r["phase"]) == 1)
    return {"n_posts": sum(cnt.values()), "distinct_post_ids": len({r["post_id"] for r in key_all.values() if int(r["phase"]) == 1}), "by_platform": dict(cnt)}

# ------------------------------------------------------------------ report
def e1cf_section():
    a = json.load(open(f"{ROOT}/results/e1_counterfactual/analysis.json")); L = ["| System | n pairs | Flag, placebo | Flag, identity replaced | Risk difference [CI95] | Holm p |", "|---|---|---|---|---|---|"]
    for s, v in a["systems"].items():
        if s.endswith("-LR") or v.get("status") != "complete": continue
        h = v["H1_PLC_minus_NEU"]; L.append(f"| {s.replace('|', ' / ')} | {h['n_pairs']} | {h['rate_x']} | {h['rate_y']} | {h['risk_difference']:+.3f} {h['rd_ci95_post_bootstrap']} | {h['holm_p_F_CF']:.2g} |")
    return a["decision"]["verdict"], "\n".join(L)

def write_report(path, ctx):
    verdict, table = e1cf_section(); L = []; A = L.append; st = ctx["status"]; has = bool(ctx.get("phases")) and not st.startswith(("PENDING", "INVALID"))
    A("# Human Evaluation of the Counterfactual E1 — Report\n")
    A(f"**Status: {st}**\n")
    A("Generated by `human_evaluation_analysis.py` (rules: `human_evaluation_protocol.md`, section 8). It contains no human judgement unless annotation files were supplied and passed validation.\n")
    A("The report keeps four constructs apart: **identity-cue sensitivity** (a property of the model, section 1), **human policy judgment** (section 2A), **human–model decision alignment** (section 2B) and **policy-inconsistent moderation** (section 5). Sensitivity is not bias and is not, by itself, a policy violation.\n")
    A("## 1. Observed experimental findings: identity-cue sensitivity (completed; no human data)\n")
    A("Counterfactual E1 (`results/e1_counterfactual/PROTOCOL.md`, 88 posts): placebo replacement of random content words (PLC) vs replacement of the identity terms (NEU); flag = verdict `violating`:\n")
    A(table + "\n")
    A(f"Pre-specified decision-rule outcome: **{verdict}**. llama3.1 is excluded from the decision (low coverage). The LR baselines show no identity-specific effect (`results/e1_counterfactual/RESULTS.md`). These findings show that the verdict **depends on the identity term**. They do not say whether the dependence is justified.\n")
    A("## 2. Human annotation findings\n")
    if st.startswith("PENDING"):
        A("**Not evaluated.** No annotation files have been supplied. No human judgement has been simulated, imputed or assumed. Rater identities, qualifications, independence and adjudication are *not documented*.\n")
    elif st.startswith("INVALID"):
        A("**Not evaluated: an annotation file failed validation.** Errors:\n")
        for ph, r in ctx["phases"].items():
            for who, errs in r["errors"].items():
                for e in errs[:15]: A(f"- phase {ph} {who}: {e}")
        A("")
    else:
        A("### 2A. Human judgment on the residual text\n")
        for ph, r in ctx["phases"].items():
            rel = r["reliability"]; sh = ctx["shares"][ph]
            A(f"**Phase {ph} — {'NEU (identity terms replaced): primary object of C1' if ph == 1 else 'REPLAY (identity terms present): descriptive only'}.** Final labels come from rater agreement ({r['final_source'].get('agreement', 0)}), adjudication ({r['final_source'].get('adjudicated', 0)}) or stay unresolved ({r['final_source'].get('unresolved', 0)}); n = {rel['n_items']} posts.\n")
            A("| Label | Share of all posts (k/n; Wilson CI95) |\n|---|---|")
            for k in (V, N, AMB, UNRES): A(f"| {k} | {fmt_share(sh[k])} |")
            A("")
            if ph == 1:
                A(f"Rule C1 (primary treatment: ambiguous and unresolved excluded): **{ctx['claim1']['primary']}**; same conclusion under all 9 treatments: {ctx['claim1']['same_under_all_9_treatments']} ({ctx['claim1']['verdicts_across_treatments']}).\n")
                A("| Ambiguous | Unresolved | Share violating | k/n | CI95 |\n|---|---|---|---|---|")
                for t in ctx["treat"][ph]: A(f"| {t['ambiguous']} | {t['unresolved']} | {t['share']} | {t['k']}/{t['n']} | {t['wilson95']} |")
                A("")
        A("A majority of `NOT_POLICY_VIOLATING` labels on NEU is a statement about the residual text. It is **not** used to conclude that a model is policy-inconsistent.\n")
        A("### 2B. Human–model paired decision alignment\n")
        pa = ctx.get("pairs")
        if not pa: A("**Not evaluable: phase 2 (REPLAY) annotations are missing.** The paired comparison needs the human label of the same post with and without the identity term.\n")
        else:
            P = pa["grid"][PRIMARY]
            A("Definitions (protocol 8.2–8.5): per post, human change Δh = b(REPLAY) − b(NEU) with b = 1 for POLICY_VIOLATING, 0 for NOT_POLICY_VIOLATING; model change Δm = flag(REPLAY) − flag(NEU) with flag = 1 for a readable `violating` verdict, 0 for a readable `not_violating` or abstention. +1 = the decision drops when the identity term is replaced. A pair is valid only if both human decisions are determinate and both model verdicts are readable.\n")
            A("| Condition | Posts | Valid pairs | Excluded (reason: n) | Model drops | Human drops | A = P(human drops \\| model drops) | D = mean(Δm − Δh) [CI95] | sign test Holm p | A / B components | **C2** |\n|---|---|---|---|---|---|---|---|---|---|---|")
            for s, m in P.items():
                lab = m["C2"]; A(f"| {s.replace('|', ' / ')} | {m['n_posts_with_both_phases']} | {m['n_valid_pairs']} | {m['excluded'] or '—'} | {m['model_change_counts']['drop(+1)']} | {m['human_change_counts']['drop(+1)']} | {fmt_share(m['A_P_human_drop_given_model_drop'])} | "
                  f"{m['D_excess_model_change']} {m['D_ci95_post_bootstrap']} | {m['holm_p'] if m['holm_p'] is not None else 'n/a'} | {lab['A_component']} / {lab['B_component']} | **{lab['label']}**{(' — ' + lab['reason']) if lab['reason'] else ''} |")
            A("\nLR rows are descriptive (no Holm family). `NOT CONCLUDABLE` means the data do not allow a C2 conclusion for that condition; it is not evidence of alignment or misalignment.\n")
            A("**Level alignment on the valid pairs** (model decision vs human decision on the same text; disagreement = over-flag + under-flag):\n")
            A("| Condition | REPLAY: model violating, human not | REPLAY: model not, human violating | NEU: model violating, human not | NEU: model not, human violating | paired McNemar p (REPLAY-only vs NEU-only disagreement) |\n|---|---|---|---|---|---|")
            for s, m in P.items():
                lv = m["level_alignment"]; A(f"| {s.replace('|', ' / ')} | {lv['REPLAY']['model_flag_human_not_violating']} | {lv['REPLAY']['model_noflag_human_violating']} | {lv['NEU']['model_flag_human_not_violating']} | {lv['NEU']['model_noflag_human_violating']} | {lv['paired_inconsistency_REPLAY_vs_NEU']['mcnemar_exact_p']} |")
            A("\n**Robustness of the C2 label** across the 20 scenarios (ambiguous × unresolved × abstention treatments; each rater's own labels as a descriptive check, not as a resolution):\n")
            A("| Condition | Primary label | Labels across scenarios | Robust | Range of A | Range of D | Valid pairs (min–max) |\n|---|---|---|---|---|---|---|")
            for s, r_ in pa["robustness"].items(): A(f"| {s.replace('|', ' / ')} | {r_['primary_label']} | {r_['labels_across_scenarios']} | {r_['robust_label']} | {r_['A_range']} | {r_['D_range']} | {r_['n_valid_pairs_range']} |")
            A("")
    A("## 3. Statistical inference\n")
    if not has: A("Not performed (no valid annotations).\n")
    else:
        for ph, r in ctx["phases"].items():
            rel = r["reliability"]
            A(f"**Inter-rater reliability, phase {ph}** (n = {rel['n_items']}): raw agreement {rel['raw_agreement']} ({rel['n_agree']}/{rel['n_items']}); Cohen's kappa {rel['cohen_kappa']} (bootstrap CI95 {rel['cohen_kappa_ci95_bootstrap']}); Krippendorff's alpha (nominal) {rel['krippendorff_alpha_nominal']}; Gwet's AC1 {rel['gwet_ac1']} (CI95 {rel['gwet_ac1_ci95_bootstrap']}). Binary (violating vs other): agreement {rel['binary_violating_vs_other']['raw_agreement']}, kappa {rel['binary_violating_vs_other']['cohen_kappa']}. "
              f"Prevalence rater 1 {rel['prevalence']['rater1']}, rater 2 {rel['prevalence']['rater2']}. Confusion matrix (rows rater 1): {rel['confusion_matrix_rows_rater1_cols_rater2']}.\n")
        if ctx.get("pairs"):
            P = ctx["pairs"]["grid"][PRIMARY]
            A(f"Unit of analysis: the post (one NEU–REPLAY pair per post and model condition; {ctx['platform']['distinct_post_ids']} distinct posts from platforms {ctx['platform']['by_platform']}). Intervals for proportions are Wilson; for D and the direction kappa they are percentile bootstrap over posts (B = {B_BOOT}, seed {SEED}). The six model conditions share the same posts, so they are analysed one at a time with Holm over the 6 LLM conditions; no pooled inference over conditions is made. The 88 posts are the E1 items that retain an identity token, not a random sample of a population, so the inference is conditional on that selection. Two platforms are too few for a cluster bootstrap; the platform split is reported as a description only.\n")
            A("**Direction of change (primary scenario).**\n")
            A("| Condition | direction agreement (exact) | kappa (3 classes) [CI95] | P(model drops \\| human drops) | joint counts (dh/dm) |\n|---|---|---|---|---|")
            for s, m in P.items(): A(f"| {s.replace('|', ' / ')} | {fmt_share(m['direction_agreement_exact'])} | {m['direction_kappa']} {m['direction_kappa_ci95_bootstrap']} | {fmt_share(m['R_P_model_drop_given_human_drop'])} | {m['joint_table_human_change_x_model_change']} |")
            A("")
    A("## 4. Limitations\n")
    for x in ("88 posts, one dataset, three small models; intervals are wide, and C2 may be NOT CONCLUDABLE for several conditions.",
              "The posts are the E1 items that keep an identity token after erasure (74 Gab, 14 Twitter), a selected set, not a random sample.",
              "Two raters; identity, background, training and independence are not documented unless supplied by the study team.",
              "The same posts appear in phase 1 (NEU) and phase 2 (REPLAY); memory effects cannot be excluded even with a gap. A shared rater bias would affect both phases and cancel in Δh, but a phase-specific order effect would not.",
              "Only NEU was rated by humans, not DEL. The NEU text can be ungrammatical or cut off.",
              "Exclusions (ambiguous, unresolved, unreadable) shrink the set of valid pairs and can bias it; they are listed per condition and varied in the robustness grid.",
              "Kappa and alpha depend on category prevalence; AC1 and the confusion matrix are reported next to them.",
              "Disagreements are never resolved by selecting one rater; unresolved items stay unresolved.",
              "Rules C1 and C2 and their thresholds are conventions fixed in the protocol, not tests with a calibrated error rate."): A(f"- {x}")
    A("\n## 5. Claims by construct\n")
    A("| Construct | Claim | Status |\n|---|---|---|")
    A("| Identity-cue sensitivity | The verdicts of qwen2.5 and gemma2 on E1 texts depend on residual identity terms | **Supported** (completed counterfactual, pre-specified rule: SUPPORT) |")
    if has:
        A(f"| Human policy judgment | Residual NEU text: {ctx['claim1']['primary']} | Rule C1; robust under all treatments: {ctx['claim1']['same_under_all_9_treatments']} |")
        if ctx.get("pairs"):
            labs = {s: m["C2"]["label"] for s, m in ctx["pairs"]["grid"][PRIMARY].items() if s in LLM_NAMES}
            A(f"| Human–model decision alignment | Per condition (rule C2): {labs} | See section 2B; robustness table |")
            na = [s.replace('|', ' / ') for s, l in labs.items() if l == "NOT ALIGNED"]
            A(f"| Policy-inconsistent moderation | Claimed only for conditions labelled NOT ALIGNED | {'claimed descriptively for: ' + ', '.join(na) if na else '**Not supported** for any condition'} |")
        else:
            A("| Human–model decision alignment | — | **Not evaluable**: phase 2 missing |")
            A("| Policy-inconsistent moderation | — | **Not evaluable** |")
    else:
        A("| Human policy judgment | Residual NEU text still contains a violating attack (or not) | **Not evaluated** |")
        A("| Human–model decision alignment | The model's identity-driven change matches the human change | **Not evaluated** |")
        A("| Policy-inconsistent moderation | The identity dependence contradicts human application of the policy | **Not evaluated; not assumed** |")
    A("\nSensitivity to an identity cue is established by the counterfactual experiment. Whether that sensitivity is aligned with, or contradicts, human application of the policy is a separate question answered only by the paired human data. A model that changes its decision when the cue is replaced is not thereby biased, and one that does not change is not thereby correct.")
    open(path, "w").write("\n".join(L) + "\n")

def main():
    ap = argparse.ArgumentParser()
    for n in ("phase1-rater1", "phase1-rater2", "phase1-adjudication", "phase2-rater1", "phase2-rater2", "phase2-adjudication"): ap.add_argument(f"--{n}")
    ap.add_argument("--key", default=None); ap.add_argument("--out-dir", default=os.path.join(HERE, "analysis")); ap.add_argument("--report", default=os.path.join(HERE, "human_evaluation_report.md"))
    a = ap.parse_args(); os.makedirs(a.out_dir, exist_ok=True)
    ctx = {"phases": {}, "treat": {}, "shares": {}}; out = {"inputs_sha1": {}}
    if not (a.phase1_rater1 and a.phase1_rater2):
        ctx["status"] = "PENDING — no human annotations supplied"
        out["status"] = ctx["status"]; json.dump(out, open(f"{a.out_dir}/human_evaluation_analysis.json", "w"), indent=1); write_report(a.report, ctx); print(ctx["status"]); return 0
    key_all = irr.load_key(a.key); flags = None
    for ph in (1, 2):
        f1, f2, fa = getattr(a, f"phase{ph}_rater1"), getattr(a, f"phase{ph}_rater2"), getattr(a, f"phase{ph}_adjudication")
        if not (f1 and f2): continue
        for f in (f1, f2, fa):
            if f and os.path.exists(f): out["inputs_sha1"][f] = sha1(f)
        ctx["phases"][ph] = process_phase(ph, f1, f2, fa, key_all)
    bad = [ph for ph, r in ctx["phases"].items() if r["status"] != "OK"]
    if bad:
        ctx["status"] = "INVALID — annotation file(s) failed validation; no statistics computed"
        out.update(status=ctx["status"], validation_errors={ph: ctx["phases"][ph]["errors"] for ph in bad})
    else:
        flags = load_model_flags(); lab1 = ctx["phases"][1]["final"]; ph2 = ctx["phases"].get(2)
        for ph, r in ctx["phases"].items(): ctx["shares"][ph] = category_shares(list(r["final"].values())); ctx["treat"][ph] = treatments(list(r["final"].values()))
        ctx["claim1"] = claim_prevalence(ctx["treat"][1]); ctx["platform"] = platform_note(key_all)
        if ph2:
            labels = {"final": (None, lab1, ph2["final"]), "rater1": (None, ctx["phases"][1]["rater1"], ph2["rater1"]), "rater2": (None, ctx["phases"][1]["rater2"], ph2["rater2"])}
            grid = pair_alignment(flags, labels); ctx["pairs"] = {"grid": grid, "robustness": robustness(grid)}
        unres = sum(1 for r in ctx["phases"].values() for v in r["final"].values() if v == UNRES)
        ctx["status"] = "COMPLETE" if (ph2 and unres == 0) else "PARTIAL — " + ("phase 2 missing" if not ph2 else "") + ("; " if (not ph2 and unres) else "") + (f"{unres} unresolved disagreement(s)" if unres else "")
        out.update(status=ctx["status"], A_human_judgement_on_residual_text={"category_shares": ctx["shares"], "treatments": ctx["treat"], "rule_C1_phase1": ctx["claim1"]},
                   level_alignment_phase1_descriptive=level_alignment_phase1(lab1, flags), platform=ctx["platform"],
                   B_paired_alignment=({"primary_scenario": PRIMARY, "primary": ctx["pairs"]["grid"][PRIMARY], "robustness": ctx["pairs"]["robustness"], "all_scenarios": ctx["pairs"]["grid"]}
                                       if ph2 else "not evaluable: phase 2 missing"),
                   reliability={ph: r["reliability"] for ph, r in ctx["phases"].items()},
                   phases={ph: {k: v for k, v in r.items() if k not in ("final", "rater1", "rater2", "reliability")} | {"final_label_counts": dict(Counter(r["final"].values()))} for ph, r in ctx["phases"].items()})
    json.dump(out, open(f"{a.out_dir}/human_evaluation_analysis.json", "w"), indent=1, default=str)
    if ctx.get("pairs"):
        with open(f"{a.out_dir}/pair_alignment_primary.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["system", "n_valid_pairs", "model_drops", "human_drops", "A", "A_lo", "A_hi", "D", "D_lo", "D_hi", "holm_p", "C2_label"])
            for s, m in ctx["pairs"]["grid"][PRIMARY].items():
                A_ = m["A_P_human_drop_given_model_drop"]; w.writerow([s, m["n_valid_pairs"], m["model_change_counts"]["drop(+1)"], m["human_change_counts"]["drop(+1)"], A_[0], A_[3][0], A_[3][1],
                                                                        m["D_excess_model_change"], m["D_ci95_post_bootstrap"][0], m["D_ci95_post_bootstrap"][1], m["holm_p"], m["C2"]["label"]])
    write_report(a.report, ctx); print(ctx["status"]); return 0

if __name__ == "__main__":
    sys.exit(main())
