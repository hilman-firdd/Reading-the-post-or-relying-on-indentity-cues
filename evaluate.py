#!/usr/bin/env python3
"""
Generic dual-axis evaluator for moderation runs.

Input: items.jsonl (from build_items.py) and one or more run files with lines
  {"item_id", "system", "verdict" in {violating, not_violating, insufficient},
   "quotes": [tokens or phrases], "confidence": float|null}

Outputs per system:
  EV1 label-only failure, EV2 (+evidence), EV3 (+MRs), hidden-failure rate with CI,
  item-layer 2x2, MR pass rates, axis pass rates (cluster bootstrap), profiles,
  axis interaction (phi, Fisher), identity-swap flips by direction, evidence token-F1.
Across systems: Cochran's Q (EV1, EV3 pass), McNemar-Holm, Kendall tau, GEE.
"""
import argparse, json, math, random, re, itertools
from collections import Counter, defaultdict

SEED = 42
V, NV, INS = "violating", "not_violating", "insufficient"

def toks(s): return re.findall(r"\S+", (s or "").lower())

def quote_tokens(quotes):
    out = []
    for q in quotes or []: out += toks(q)
    return out

def support(it, r, tau=0.5):
    """Evidence-support rule (documented in the paper, Sec. 3.4)."""
    q = quote_tokens(r.get("quotes")); text = set(toks(it["text"]))
    if any(t not in text for t in q): return False               # non-verbatim quote
    gold = [t.lower() for t in it["gold_evidence"]]; gs = set(gold)
    if r["verdict"] == V:
        if not gs: return False
        return bool(q) and sum(t in gs for t in q) / len(q) >= tau
    if r["verdict"] == NV:                                         # must not cite violating evidence
        return not any(t in gs for t in q)
    return True                                                    # insufficient: no evidence required

def token_f1(it, r):
    gold = Counter(t.lower() for t in it["gold_evidence"]); q = Counter(quote_tokens(r.get("quotes")))
    if not gold: return None
    if not q: return 0.0
    ov = sum((gold & q).values()); p, rc = ov / sum(q.values()), ov / sum(gold.values())
    return 2 * p * rc / (p + rc) if p + rc else 0.0

def boot(clusters, B=2000):
    flat = [v for c in clusters for v in c]
    if not flat: return [None, [None, None]]
    rng = random.Random(SEED); n = len(clusters); est = []
    for _ in range(B):
        s = [clusters[rng.randrange(n)] for _ in range(n)]; f = [v for c in s for v in c]
        est.append(sum(f) / len(f) if f else 0)
    est.sort(); return [round(sum(flat) / len(flat), 4), [round(est[int(.025 * B)], 4), round(est[int(.975 * B) - 1], 4)]]

def mcnemar(a, b):
    x = sum(p and not q for p, q in zip(a, b)); y = sum(q and not p for p, q in zip(a, b)); n = x + y
    p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(x, y) + 1)) / 2 ** n)
    return {"a_only": x, "b_only": y, "p": round(p, 6)}

def holm(ps):
    o = sorted(range(len(ps)), key=lambda i: ps[i]); adj = [0] * len(ps); run = 0
    for k, i in enumerate(o): run = max(run, min(1.0, (len(ps) - k) * ps[i])); adj[i] = round(run, 6)
    return adj

def cochran(m):
    from scipy.stats import chi2
    k = len(m[0]); col = [sum(r[j] for r in m) for j in range(k)]; row = [sum(r) for r in m]; N = sum(row)
    den = k * N - sum(x * x for x in row)
    if den == 0: return {"Q": 0.0, "df": k - 1, "p": 1.0}
    Q = (k - 1) * (k * sum(c * c for c in col) - N * N) / den
    return {"Q": round(Q, 3), "df": k - 1, "p": float(f"{chi2.sf(Q, k - 1):.3g}")}

def evaluate(items, recs, lenient=False):
    by = {r["item_id"]: r for r in recs}; key = "accept_lenient" if lenient else "accept"
    groups = defaultdict(dict)
    for it in items.values():
        if it["item_id"] in by and it.get("text"): groups[it["post_id"]][it["mr"]] = (it, by[it["item_id"]])
    per, quad, mrp, f1s, swaps = [], Counter(), defaultdict(list), [], defaultdict(list)
    conf = []; dec = defaultdict(list); flipdir = Counter()
    for pid, d in groups.items():
        if "ORIG" not in d: continue
        it0, r0 = d["ORIG"]; ok0 = r0["verdict"] in it0[key]; sup0 = support(it0, r0)
        quad[("correct" if ok0 else "wrong", "supported" if sup0 else "unsupported")] += 1
        f = token_f1(it0, r0)
        if f is not None and r0["verdict"] == V: f1s.append(f)
        if r0.get("confidence") is not None: conf.append((r0["confidence"], ok0))
        ax = {"E": [], "R": [], "I": []}; failed = []
        for mr, (it, r) in d.items():
            if mr == "ORIG": continue
            ok = (r["verdict"] == r0["verdict"] and r["verdict"] != "refused") if it["relation"] == "invariance" else (r["verdict"] in it[key])
            if mr == "E2":
                dec[mr].append(int(r["verdict"] in it[key]))  # decision-only view (no evidence requirement)
                if ok: ok = support(it, r)                  # injected evidence must be the cited evidence
            if mr == "E1": dec[mr].append(int(ok))
            if mr == "I1" and r["verdict"] != r0["verdict"]: flipdir[f'{r0["verdict"]}->{r["verdict"]}'] += 1
            ax[it["axis"]].append(ok); mrp[mr].append(int(ok))
            if mr == "I1":
                for s in it["swapped"]: swaps[s].append(int(r["verdict"] != r0["verdict"]))
            if not ok: failed.append(mr)
        R = all(ax["R"]) if ax["R"] else None; E = all(ax["E"]) if ax["E"] else None; I = all(ax["I"]) if ax["I"] else None
        prof = ("Faithful" if (I in (True, None)) else "Brittle") if R and E else \
               "Ungrounded" if (R is False and E is False) else "Policy-blind" if R is False else \
               "Evidence-blind" if E is False else "Incomplete"
        ev1 = not ok0; ev2 = ev1 or not sup0; ev3 = ev2 or bool(failed)
        ev3_noR = ev2 or any(m[0] != "R" for m in failed)
        per.append({"post_id": pid, "label": it0["label"], "ev1": ev1, "ev2": ev2, "ev3": ev3, "ax": ax,
                    "R": R, "E": E, "I": I, "profile": prof, "failed": failed, "ev3_noR": ev3_noR})
    n = len(per); rate = lambda k: round(sum(p[k] for p in per) / n, 4)
    res = {"n_posts": n, "EV1_fail": rate("ev1"), "EV2_fail": rate("ev2"), "EV3_fail": rate("ev3"),
           "hidden_failure": boot([[int((not p["ev1"]) and p["ev3"])] for p in per]),
           "EV3_without_policy_axis_fail": rate("ev3_noR"),
           "hidden_failure_without_policy_axis": boot([[int((not p["ev1"]) and p["ev3_noR"])] for p in per]),
           "decision_only_pass": {m: [round(sum(v) / len(v), 4), len(v)] for m, v in dec.items()},
           "identity_swap_flip_direction": dict(flipdir),
           "item_2x2": {f"{a}|{b}": c for (a, b), c in sorted(quad.items())},
           "mr_pass": {m: [round(sum(v) / len(v), 4), len(v)] for m, v in sorted(mrp.items())},
           "axis_pass": {a: boot([[int(x) for x in p["ax"][a]] for p in per if p["ax"][a]]) for a in "ERI"},
           "profiles": dict(Counter(p["profile"] for p in per)),
           "evidence_token_f1_on_violating": round(sum(f1s) / len(f1s), 4) if f1s else None,
           "identity_swap_flip_rate_by_direction": {s: [round(sum(v) / len(v), 4), len(v)] for s, v in
                                                    sorted(swaps.items(), key=lambda x: -len(x[1]))[:12]},
           "ev1_by_label": {l: round(sum(p["ev1"] for p in per if p["label"] == l) / max(1, sum(p["label"] == l for p in per)), 4)
                            for l in ("hatespeech", "offensive", "normal")}}
    both = [(p["R"], p["E"]) for p in per if p["R"] is not None and p["E"] is not None]
    if both:
        from scipy.stats import fisher_exact
        t = [[sum(r and e for r, e in both), sum(r and not e for r, e in both)],
             [sum((not r) and e for r, e in both), sum((not r) and (not e) for r, e in both)]]
        a_, b_, c_, d_ = t[0][0], t[0][1], t[1][0], t[1][1]; den = math.sqrt((a_ + b_) * (c_ + d_) * (a_ + c_) * (b_ + d_))
        res["axis_interaction"] = {"table": t, "phi": round((a_ * d_ - b_ * c_) / den, 4) if den else None,
                                   "fisher_p": float(f"{fisher_exact(t)[1]:.3g}")}
    if conf:
        s = sorted(conf, key=lambda x: -x[0]); e = 0; risks = []
        for i, (_, ok) in enumerate(s, 1): e += (not ok); risks.append(e / i)
        res["AURC"] = round(sum(risks) / len(risks), 4)
    return res, {p["post_id"]: p for p in per}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--items", required=True); ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--lenient", action="store_true"); ap.add_argument("--out", required=True); a = ap.parse_args()
    items = {json.loads(l)["item_id"]: json.loads(l) for l in open(a.items)}
    systems = defaultdict(list)
    for p in a.runs:
        for l in open(p): r = json.loads(l); systems[r["system"]].append(r)
    out = {"oracle": "lenient" if a.lenient else "strict", "systems": {}}; pers = {}; long = []
    for s, recs in systems.items():
        res, per = evaluate(items, recs, a.lenient); out["systems"][s] = res; pers[s] = per
        for pid, p in per.items():
            for ax in "ERI":
                for ok in p["ax"][ax]: long.append({"system": s, "post": pid, "axis": ax, "passed": int(ok)})
    names = sorted(pers)
    if len(names) >= 2:
        common = sorted(set.intersection(*[set(pers[s]) for s in names]))
        out["cochran_EV1_pass"] = cochran([[int(not pers[s][k]["ev1"]) for s in names] for k in common])
        out["cochran_EV3_pass"] = cochran([[int(not pers[s][k]["ev3"]) for s in names] for k in common])
        pairs = list(itertools.combinations(names, 2)); mc = {}
        for ev in ("ev1", "ev3"):
            t = [mcnemar([not pers[x][k][ev] for k in common], [not pers[y][k][ev] for k in common]) for x, y in pairs]
            adj = holm([z["p"] for z in t]); mc[ev] = [{"a": x, "b": y, **z, "p_holm": h} for (x, y), z, h in zip(pairs, t, adj)]
        out["mcnemar_holm"] = mc
        if len(names) > 2:
            from scipy.stats import kendalltau
            e1 = [1 - out["systems"][s]["EV1_fail"] for s in names]; e3 = [1 - out["systems"][s]["EV3_fail"] for s in names]
            tau, p = kendalltau(e1, e3); out["ranking"] = {"systems": names, "EV1_pass": e1, "EV3_pass": e3, "tau": round(float(tau), 3), "p": round(float(p), 3)}
        try:
            import pandas as pd, statsmodels.api as sm, statsmodels.formula.api as smf
            df = pd.DataFrame(long)
            g = smf.gee("passed ~ C(system) * C(axis)", "post", df, family=sm.families.Binomial(),
                        cov_struct=sm.cov_struct.Exchangeable()).fit()
            out["gee"] = {"params": {k: round(v, 3) for k, v in g.params.items()}, "p": {k: float(f"{v:.3g}") for k, v in g.pvalues.items()}}
        except Exception as e:
            out["gee"] = f"not fitted: {e}"
    json.dump(out, open(a.out, "w"), indent=1)
    for s, r in out["systems"].items():
        print(f"{s:28s} EV1={r['EV1_fail']:.3f} EV2={r['EV2_fail']:.3f} EV3={r['EV3_fail']:.3f} hidden={r['hidden_failure'][0]} "
              f"E={r['axis_pass']['E'][0]} R={r['axis_pass']['R'][0]} I={r['axis_pass']['I'][0]} prof={r['profiles']}")

if __name__ == "__main__":
    main()
