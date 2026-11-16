#!/usr/bin/env python3
"""
Refusal-aware, oracle-aware re-evaluation of the llm600 runs.  READ-ONLY on runs/, items, validation sheet.

  python audit_metrics.py            (writes results/audited/*; ~1 min)

Unit of analysis
  * Each MR has at most one item per post (checked below), so within one MR an item IS a post and Wilson
    intervals are not pseudoreplicated.
  * Anything pooled over several MRs of the same post (the "ALL" rows, kappa over the validation sample)
    uses a cluster bootstrap that resamples posts.
  * Paired comparisons (I1 vs I2, direct vs evidence, LLM vs LR) pair on the post and use exact McNemar
    tests plus a post-level bootstrap CI for the risk difference.

Categories come from response_classifier.py. Only VALID_VERDICT and ABSTENTION carry a verdict
("answered"); REFUSAL / UNPARSEABLE / EMPTY_RESPONSE / GENERATION_ERROR never count as correct.
"""
import csv, hashlib, json, math, os, random, sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from response_classifier import classify_record, CATEGORIES, ANSWERED  # noqa: E402

OUT = "results/audited"
SEED, B_POOLED, B_TEST = 42, 2000, 5000
RUNS = [("qwen2.5:7b", "direct", "runs/qwen2.5_7b_direct.jsonl"), ("qwen2.5:7b", "evidence", "runs/qwen2.5_7b_evidence.jsonl"),
        ("llama3.1:8b", "direct", "runs/llama3.1_8b_direct.jsonl"), ("llama3.1:8b", "evidence", "runs/llama3.1_8b_evidence.jsonl"),
        ("gemma2:9b", "direct", "runs/gemma2_9b_direct.jsonl"), ("gemma2:9b", "evidence", "runs/gemma2_9b_evidence.jsonl"),
        ("word-LR", "-", "runs/llm600_word-LR.jsonl"), ("char-LR", "-", "runs/llm600_char-LR.jsonl")]
MRS = ["ORIG", "E1", "E2", "R1", "R2", "R3", "I1", "I2", "I3"]
V, NV, INS = "violating", "not_violating", "insufficient"
OPP = {V: NV, NV: V}
SHORT = {"REFUSAL": "REF", "UNPARSEABLE": "UNP", "EMPTY_RESPONSE": "EMP", "GENERATION_ERROR": "ERR"}
VALIDATED_MRS = ("E1", "E2", "R2", "I1", "I3")

# ------------------------------------------------------------------ statistics helpers
def wilson(k, n, z=1.96):
    if not n: return [None, None]
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0, c - h), 4), round(min(1, c + h), 4)]

def rate(k, n): return round(k / n, 4) if n else None

def cluster_boot(per_post, B=B_POOLED, seed=SEED):
    """per_post: list of (numerator, denominator) per post -> percentile CI of sum(num)/sum(den)."""
    if not per_post or not sum(d for _, d in per_post): return [None, None]
    rng = random.Random(seed); n = len(per_post); est = []
    for _ in range(B):
        s = [per_post[rng.randrange(n)] for _ in range(n)]; den = sum(d for _, d in s)
        if den: est.append(sum(x for x, _ in s) / den)
    est.sort(); return [round(est[int(.025 * len(est))], 4), round(est[int(.975 * len(est)) - 1], 4)]

def mcnemar_exact(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)

def holm(pvals):
    """Holm over the tests that exist; untestable entries (p=None) are reported as None and do not count."""
    out = {k: None for k, p in pvals.items() if p is None}; pvals = {k: p for k, p in pvals.items() if p is not None}
    names = sorted(pvals, key=lambda k: pvals[k]); m = len(names); run = 0.0
    for i, k in enumerate(names): run = max(run, min(1.0, (m - i) * pvals[k])); out[k] = round(run, 6)
    return out

def clopper_pearson(k, n, a=0.05):
    from scipy.stats import beta
    lo = 0.0 if k == 0 else beta.ppf(a / 2, k, n - k + 1); hi = 1.0 if k == n else beta.ppf(1 - a / 2, k + 1, n - k)
    return lo, hi

def paired(pairs, B=B_TEST, seed=SEED):
    """pairs: list of (x, y) 0/1 per post. Effect = mean(x) - mean(y)."""
    n = len(pairs)
    if not n: return {"n_pairs": 0, "rate_x": None, "rate_y": None, "b_only_x": 0, "c_only_y": 0, "risk_difference": None,
                      "rd_ci95_post_bootstrap": [None, None], "conditional_odds_ratio_b_over_c": None, "or_ci95_exact": [None, None],
                      "mcnemar_exact_p": None, "note": "no complete pairs: not testable"}
    b = sum(1 for x, y in pairs if x and not y); c = sum(1 for x, y in pairs if y and not x)
    rng = random.Random(seed); est = []
    for _ in range(B):
        s = [pairs[rng.randrange(n)] for _ in range(n)]; est.append(sum(x - y for x, y in s) / n)
    est.sort()
    if b + c:
        lo, hi = clopper_pearson(b, b + c)
        orr = [round(b / c, 3) if c else None, round(lo / (1 - lo), 3) if lo < 1 else None, round(hi / (1 - hi), 3) if hi < 1 else None]
    else: orr = [None, None, None]
    return {"n_pairs": n, "rate_x": rate(sum(x for x, _ in pairs), n), "rate_y": rate(sum(y for _, y in pairs), n),
            "b_only_x": b, "c_only_y": c, "risk_difference": round((b - c) / n, 4),
            "rd_ci95_post_bootstrap": [round(est[int(.025 * B)], 4), round(est[int(.975 * B) - 1], 4)],
            "conditional_odds_ratio_b_over_c": orr[0], "or_ci95_exact": orr[1:], "mcnemar_exact_p": float(f"{mcnemar_exact(b, c):.4g}")}

def kappa(pairs):
    n = len(pairs)
    if not n: return None
    po = sum(a == b for a, b in pairs) / n; p1 = sum(a for a, _ in pairs) / n; p2 = sum(b for _, b in pairs) / n
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    return None if pe == 1 else (po - pe) / (1 - pe)

def toks(s): return [t for t in (s or "").lower().split() if t]

# ------------------------------------------------------------------ load
def load():
    items = {}
    for l in open("items_llm600.jsonl"):
        it = json.loads(l); items[it["item_id"]] = it
    run_items = {k: it for k, it in items.items() if it.get("text")}
    key = Counter((it["post_id"], it["mr"]) for it in run_items.values())
    assert max(key.values()) == 1, "an MR has >1 item for some post: item-level CIs would be pseudoreplicated"
    orig = {it["post_id"]: it for it in run_items.values() if it["mr"] == "ORIG"}
    systems, records = [], []
    for model, prompt, path in RUNS:
        recs = [json.loads(l) for l in open(path)]
        name = recs[0]["system"]; systems.append({"system": name, "model": model, "prompt": prompt, "file": path,
                                                   "sha1": hashlib.sha1(open(path, "rb").read()).hexdigest()})
        assert len({r["item_id"] for r in recs}) == len(recs) == len(run_items), path
        for r in recs:
            c = classify_record(r)
            records.append({"system": name, "item_id": r["item_id"], "category": c["category"],
                            "verdict": c["verdict"] if c["category"] in ANSWERED else None,
                            "recovered_verdict": c["recovered_verdict"], "needs_manual_review": c["needs_manual_review"],
                            "reason": c["reason"], "truncated": c["truncated"], "stored_verdict": r["verdict"],
                            "quotes": r.get("quotes") or [], "raw_sha1": hashlib.sha1((r.get("raw") or "").encode()).hexdigest()[:12] if "raw" in r else None,
                            "raw_excerpt": (r.get("raw") or "")[:240] if c["needs_manual_review"] else None})
    by = defaultdict(dict)
    for x in records: by[x["system"]][x["item_id"]] = x
    return items, run_items, orig, systems, records, by

def load_validation(items):
    import hitl_sheet
    rows = hitl_sheet.read("human_validation_filled.xlsx")
    groups = json.load(open("human_validation_r2_groups.json"))
    out = {}
    for r in rows:
        fin = r["r1"] if (r["r1"] is not None and r["r1"] == r["r2"]) else r["adj"]
        out[r["item_id"]] = {"mr": r["mr"], "r1": r["r1"], "r2": r["r2"], "adj": r["adj"], "final": fin,
                             "status": "pending" if fin is None else ("valid" if fin == 1 else "invalid"),
                             "r2_group": groups.get(r["item_id"]), "post_id": items[r["item_id"]]["post_id"]}
    return out

def r2_strata(items):
    d = json.load(open("data/dataset.json")); s = {}
    for it in items.values():
        if it["mr"] != "R2" or not it.get("text"): continue
        if it["label"] == "offensive":
            s[it["item_id"]] = "offensive_ambiguous" if any(a["label"] == "hatespeech" for a in d[it["post_id"]]["annotators"]) else "offensive_control"
        else: s[it["item_id"]] = it["label"]
    return s

# ------------------------------------------------------------------ per-item helpers
def lab(x): return x["verdict"] if x["verdict"] else SHORT.get(x["category"], x["category"])
def ok(it, x, lenient=False): return x["verdict"] is not None and x["verdict"] in it["accept_lenient" if lenient else "accept"]
def ok_corrected(it, x, valid):
    """Binary-gold MRs: an invalid oracle means the opposite verdict is the right one (strict)."""
    if valid: return ok(it, x)
    return x["verdict"] == OPP.get(it["gold"])

def block(items_list, X, unit):
    """Category counts and accuracies for one set of items of one system."""
    n = len(items_list); cat = Counter(X[it["item_id"]]["category"] for it in items_list)
    xs = [X[it["item_id"]] for it in items_list]
    valid = [(it, x) for it, x in zip(items_list, xs) if x["category"] == "VALID_VERDICT"]
    ans = [(it, x) for it, x in zip(items_list, xs) if x["category"] in ANSWERED]
    cv = sum(ok(it, x) for it, x in valid); ca = sum(ok(it, x) for it, x in ans); cl = sum(ok(it, x, True) for it, x in ans)
    rec_ok = sum(ok(it, x) or (x["category"] == "UNPARSEABLE" and x["recovered_verdict"] in it["accept"]) for it, x in zip(items_list, xs))
    row = {"unit": unit, "n_total": n, **{f"n_{c.lower()}": cat.get(c, 0) for c in CATEGORIES},
           "coverage_valid": rate(len(valid), n), "answered_rate": rate(len(ans), n),
           "refusal_rate": rate(cat.get("REFUSAL", 0), n), "abstention_rate": rate(cat.get("ABSTENTION", 0), n),
           "unparseable_rate": rate(cat.get("UNPARSEABLE", 0), n), "generation_error_rate": rate(cat.get("GENERATION_ERROR", 0), n),
           "empty_rate": rate(cat.get("EMPTY_RESPONSE", 0), n),
           "n_correct_valid": cv, "cond_acc_valid": rate(cv, len(valid)), "n_correct_answered": ca, "cond_acc_answered": rate(ca, len(ans)),
           "overall_acc_nonanswer_wrong": rate(ca, n), "overall_acc_lenient": rate(cl, n),
           "overall_acc_with_recovered_unparseable": rate(rec_ok, n), "n_manual_review": sum(x["needs_manual_review"] for x in xs)}
    if unit == "post":
        row.update({"coverage_ci95": wilson(len(valid), n), "cond_acc_valid_ci95": wilson(cv, len(valid)),
                    "cond_acc_answered_ci95": wilson(ca, len(ans)), "overall_acc_ci95": wilson(ca, n), "refusal_ci95": wilson(cat.get("REFUSAL", 0), n)})
    return row

def consistency(it, X, orig):
    """Invariance MRs: (both answered, flipped) relative to the model's own ORIG verdict."""
    o = X[orig[it["post_id"]]["item_id"]]; x = X[it["item_id"]]
    if o["category"] in ANSWERED and x["category"] in ANSWERED: return True, x["verdict"] != o["verdict"]
    return False, None

# ------------------------------------------------------------------ main analyses
def main():
    os.makedirs(OUT, exist_ok=True)
    items, run_items, orig, systems, records, by = load()
    val = load_validation(items); strata = r2_strata(items)
    names = [s["system"] for s in systems]; llms = names[:6]
    per_mr = defaultdict(list)
    for it in run_items.values(): per_mr[it["mr"]].append(it)
    posts = sorted(orig)

    # ---------- 1. response classification
    rc = {"classifier": "response_classifier.py", "categories": CATEGORIES, "answered_categories": ANSWERED,
          "systems": systems, "summary": {}, "summary_by_mr": {}, "manual_review": [], "records": []}
    for s in names:
        X = by[s]; rc["summary"][s] = dict(Counter(x["category"] for x in X.values()))
        rc["summary_by_mr"][s] = {m: dict(Counter(X[it["item_id"]]["category"] for it in per_mr[m])) for m in MRS}
        rc["summary"][s]["stored_verdict_changed_by_audit"] = sum(1 for x in X.values() if (x["verdict"] or "-") != x["stored_verdict"])
    for x in records:
        if x["needs_manual_review"]:
            rc["manual_review"].append({k: x[k] for k in ("system", "item_id", "category", "reason", "recovered_verdict", "stored_verdict", "raw_excerpt")})
        rc["records"].append({k: x[k] for k in ("system", "item_id", "category", "verdict", "recovered_verdict", "needs_manual_review", "reason", "stored_verdict", "raw_sha1")})
    json.dump(rc, open(f"{OUT}/response_classification.json", "w"), indent=1)
    with open(f"{OUT}/manual_review_queue.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["system", "item_id", "category", "reason", "recovered_verdict", "stored_verdict", "raw_excerpt"]); w.writeheader(); w.writerows(rc["manual_review"])

    # ---------- 2. audited metrics (system x MR)
    rows = []
    for meta in systems:
        s = meta["system"]; X = by[s]
        pp = defaultdict(lambda: [0, 0, 0, 0])  # per post: valid, refusal, correct_answered, total
        for it in run_items.values():
            x = X[it["item_id"]]; p = pp[it["post_id"]]
            p[0] += x["category"] == "VALID_VERDICT"; p[1] += x["category"] == "REFUSAL"; p[2] += ok(it, x); p[3] += 1
        allr = block(list(run_items.values()), X, "post-cluster")
        allr.update({"coverage_ci95": cluster_boot([(v[0], v[3]) for v in pp.values()]),
                     "refusal_ci95": cluster_boot([(v[1], v[3]) for v in pp.values()]),
                     "overall_acc_ci95": cluster_boot([(v[2], v[3]) for v in pp.values()])})
        rows.append({"system": s, "model": meta["model"], "prompt": meta["prompt"], "mr": "ALL", **allr})
        for m in MRS:
            r = block(per_mr[m], X, "post")
            if m in ("I1", "I2", "I3"):
                cs = [consistency(it, X, orig) for it in per_mr[m]]; both = [f for a, f in cs if a]
                r.update({"n_pairs_both_answered": len(both), "n_flip_vs_own_orig": sum(both),
                          "flip_rate_vs_own_orig": rate(sum(both), len(both)), "flip_ci95": wilson(sum(both), len(both))})
            rows.append({"system": s, "model": meta["model"], "prompt": meta["prompt"], "mr": m, **r})
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(f"{OUT}/audited_metrics.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in rows: w.writerow({k: (json.dumps(v) if isinstance(v, list) else v) for k, v in r.items()})
    M = {(r["system"], r["mr"]): r for r in rows}

    stats = {"units_of_analysis": {
        "per_MR_metrics": "post (one item per post per MR, verified); Wilson 95% CI",
        "ALL_rows": "post-cluster bootstrap (posts resampled, B=%d)" % B_POOLED,
        "paired_tests": "post-paired exact McNemar; risk difference with post bootstrap CI (B=%d); conditional OR with exact CI" % B_TEST,
        "kappa": "validation items, post-cluster bootstrap CI"}, "seed": SEED}

    # ---------- 3. E1 / E2 / R1 / R2 / R3 behaviour
    beh = {}
    for s in names:
        X = by[s]; o = lambda it: X[orig[it["post_id"]]["item_id"]]; d = {}
        # E1: evidence removal
        e1 = per_mr["E1"]; tr = Counter(f"{lab(o(it))}->{lab(X[it['item_id']])}" for it in e1)
        base = [it for it in e1 if o(it)["verdict"] == V and X[it["item_id"]]["category"] in ANSWERED]
        kept = sum(X[it["item_id"]]["verdict"] == V for it in base)
        vio = [it for it in e1 if X[it["item_id"]]["verdict"] == V]
        def cites_removed(it):
            text = set(toks(it["text"])); er = {t.lower() for t in it.get("erased", [])}
            return any(t in er and t not in text for q in X[it["item_id"]]["quotes"] for t in toks(q))
        def nonverbatim(it):
            text = set(toks(it["text"])); return any(t not in text for q in X[it["item_id"]]["quotes"] for t in toks(q))
        withq = [it for it in vio if X[it["item_id"]]["quotes"]]
        d["E1"] = {"transition_orig_to_E1": dict(tr), "n_orig_violating_and_E1_answered": len(base),
                   "retained_violating_after_removal": [rate(kept, len(base)), kept, len(base), wilson(kept, len(base))],
                   "moved_to_not_violating": rate(sum(X[it["item_id"]]["verdict"] == NV for it in base), len(base)),
                   "moved_to_insufficient": rate(sum(X[it["item_id"]]["verdict"] == INS for it in base), len(base)),
                   "E1_violating_with_quotes": len(withq),
                   "quotes_cite_removed_words": [rate(sum(map(cites_removed, withq)), len(withq)), sum(map(cites_removed, withq))],
                   "quotes_nonverbatim": [rate(sum(map(nonverbatim, withq)), len(withq)), sum(map(nonverbatim, withq))]}
        # E2: evidence insertion
        e2 = per_mr["E2"]; tr = Counter(f"{lab(o(it))}->{lab(X[it['item_id']])}" for it in e2)
        base = [it for it in e2 if o(it)["verdict"] in (NV, INS) and X[it["item_id"]]["category"] in ANSWERED]
        turned = sum(X[it["item_id"]]["verdict"] == V for it in base)
        vio = [it for it in e2 if X[it["item_id"]]["verdict"] == V and X[it["item_id"]]["quotes"]]
        inj = lambda it: any(t in {w.lower() for w in it.get("injected", [])} for q in X[it["item_id"]]["quotes"] for t in toks(q))
        d["E2"] = {"transition_orig_to_E2": dict(tr), "n_orig_not_violating_and_E2_answered": len(base),
                   "turned_violating_after_insertion": [rate(turned, len(base)), turned, len(base), wilson(turned, len(base))],
                   "E2_violating_with_quotes": len(vio), "quotes_cite_injected_words": [rate(sum(map(inj, vio)), len(vio)), sum(map(inj, vio))]}
        # R1: policy deleted -> should abstain
        r1 = per_mr["R1"]; ans = [it for it in r1 if X[it["item_id"]]["category"] in ANSWERED]
        ab = sum(X[it["item_id"]]["verdict"] == INS for it in ans)
        d["R1"] = {"n": len(r1), "n_answered": len(ans), "abstained_among_answered": [rate(ab, len(ans)), ab, wilson(ab, len(ans))],
                   "refused": M[(s, "R1")]["n_refusal"], "pass_overall_nonanswer_wrong": M[(s, "R1")]["overall_acc_nonanswer_wrong"],
                   "note": "LR baselines cannot abstain by construction" if "LR" in s else ""}
        # R2: narrowed policy, split by whether the reference label changes
        r2 = {}
        for g in ("offensive_ambiguous", "offensive_control", "hatespeech", "normal"):
            its = [it for it in per_mr["R2"] if strata[it["item_id"]] == g]; a = [it for it in its if X[it["item_id"]]["category"] in ANSWERED]
            k = sum(ok(it, X[it["item_id"]]) for it in a)
            pv = [it for it in its if o(it)["verdict"] == V and X[it["item_id"]]["category"] in ANSWERED]
            r2[g] = {"n": len(its), "n_answered": len(a), "pass_among_answered": [rate(k, len(a)), k, wilson(k, len(a))],
                     "orig_violating_switched_to_not_violating": [rate(sum(X[it["item_id"]]["verdict"] == NV for it in pv), len(pv)), len(pv)],
                     "transition_orig_to_R2": dict(Counter(f"{lab(o(it))}->{lab(X[it['item_id']])}" for it in its))}
        d["R2"] = r2
        # R3: negated policy (all reference labels flip; confounded with fixed-verdict behaviour)
        r3 = per_mr["R3"]; pr = [(it, X[it["item_id"]]) for it in r3 if X[it["item_id"]]["category"] in ANSWERED and o(it)["category"] in ANSWERED]
        ch = sum(x["verdict"] != o(it)["verdict"] for it, x in pr); ps = [(it, x) for it, x in pr if ok(it, x)]
        d["R3"] = {"n_pairs_answered": len(pr), "verdict_changed_vs_orig": [rate(ch, len(pr)), ch, wilson(ch, len(pr))],
                   "pass_among_answered": rate(len(ps), len(pr)),
                   "passes_without_changing_verdict": sum(x["verdict"] == o(it)["verdict"] for it, x in ps),
                   "note": "a pass without a verdict change means the ORIG verdict was wrong; R3 pass is not policy sensitivity on its own"}
        beh[s] = d
    stats["behaviour_E_R"] = beh

    # ---------- 4. I1 vs I2 (family F_I: one test per system)
    inv_items = {m: {it["post_id"]: it for it in per_mr[m]} for m in ("I1", "I2", "I3")}
    i1_posts = sorted(inv_items["I1"])
    def triples(s, exclude_invalid=False):
        X = by[s]; out, cov = [], Counter()
        for p in i1_posts:
            o, a, b = X[orig[p]["item_id"]], X[inv_items["I1"][p]["item_id"]], X[inv_items["I2"][p]["item_id"]]
            if exclude_invalid and val.get(inv_items["I1"][p]["item_id"], {}).get("status") == "invalid": continue
            cov["posts"] += 1
            if all(x["category"] in ANSWERED for x in (o, a, b)): out.append((p, o, a, b))
            else: cov["incomplete"] += 1; cov["any_refusal"] += any(x["category"] == "REFUSAL" for x in (o, a, b))
        return out, cov
    fam, fam_sens = {}, {}
    for s in names:
        t, cov = triples(s); pairs = [(int(a["verdict"] != o["verdict"]), int(b["verdict"] != o["verdict"])) for _, o, a, b in t]
        res = paired(pairs); res["coverage_complete_triples"] = [rate(len(t), cov["posts"]), len(t), cov["posts"]]
        res["incomplete_triples_with_refusal"] = cov["any_refusal"]
        res["transition_orig_to_I1"] = dict(Counter(f"{o['verdict']}->{a['verdict']}" for _, o, a, _ in t))
        res["transition_orig_to_I2"] = dict(Counter(f"{o['verdict']}->{b['verdict']}" for _, o, _, b in t))
        res["I1_flip_direction"] = dict(Counter(f"{o['verdict']}->{a['verdict']}" for _, o, a, _ in t if a["verdict"] != o["verdict"]))
        it_ = lambda p, m: inv_items[m][p]
        res["I1_flips_toward_oracle"] = sum(1 for p, o, a, _ in t if a["verdict"] != o["verdict"] and a["verdict"] in it_(p, "I1")["accept"])
        res["I1_flips_away_from_oracle"] = sum(1 for p, o, a, _ in t if a["verdict"] != o["verdict"] and o["verdict"] in orig[p]["accept"])
        res["I1_acc_vs_oracle"] = rate(sum(a["verdict"] in it_(p, "I1")["accept"] for p, _, a, _ in t), len(t))
        res["I2_acc_vs_oracle"] = rate(sum(b["verdict"] in it_(p, "I2")["accept"] for p, _, _, b in t), len(t))
        hv = [(p, o, a) for p, o, a, _ in t if val.get(it_(p, "I1")["item_id"], {}).get("status") in ("valid", "invalid")]
        res["human_validated_I1_descriptive"] = {st: {"n": sum(1 for p, _, _ in hv if val[it_(p, "I1")["item_id"]]["status"] == st),
                                                      "flips": sum(1 for p, o, a in hv if val[it_(p, "I1")["item_id"]]["status"] == st and a["verdict"] != o["verdict"])}
                                                 for st in ("valid", "invalid")}
        fam[s] = res
        t2, cov2 = triples(s, exclude_invalid=True)
        fam_sens[s] = paired([(int(a["verdict"] != o["verdict"]), int(b["verdict"] != o["verdict"])) for _, o, a, b in t2]); fam_sens[s]["posts"] = cov2["posts"]
    for d_, h in ((fam, holm({s: fam[s]["mcnemar_exact_p"] for s in names})), (fam_sens, holm({s: fam_sens[s]["mcnemar_exact_p"] for s in names}))):
        for s in names: d_[s]["holm_p_family_F_I"] = h[s]
    stats["I1_vs_I2"] = {"family_F_I": "8 tests: one McNemar (flip under I1 vs flip under I2, paired on post) per system; Holm",
                         "flip_definition": "verdict differs from the same system's ORIG verdict; only posts where ORIG, I1 and I2 are all answered",
                         "main": fam, "sensitivity_without_human_invalid_I1_items": fam_sens}

    # ---------- 5. I3 groups and circularity
    i3 = {}
    groups = {"all_with_text": lambda it: True, "judge_equivalent": lambda it: bool(it.get("auto_valid")),
              "judge_not_equivalent": lambda it: not it.get("auto_valid"),
              "human_valid": lambda it: val.get(it["item_id"], {}).get("status") == "valid",
              "human_invalid": lambda it: val.get(it["item_id"], {}).get("status") == "invalid",
              "human_pending": lambda it: val.get(it["item_id"], {}).get("status") == "pending"}
    for s in names:
        X = by[s]; g = {}
        for gname, f in groups.items():
            its = [it for it in per_mr["I3"] if f(it)]; cs = [consistency(it, X, orig) for it in its]; both = [fl for a, fl in cs if a]
            g[gname] = {"n_items": len(its), "n_pairs_answered": len(both), "flip_rate": rate(sum(both), len(both)), "flips": sum(both), "ci95": wilson(sum(both), len(both))}
        pairs = []
        for it in per_mr["I3"]:
            o, a, b = X[orig[it["post_id"]]["item_id"]], X[it["item_id"]], X[inv_items["I2"][it["post_id"]]["item_id"]]
            if all(x["category"] in ANSWERED for x in (o, a, b)): pairs.append((int(a["verdict"] != o["verdict"]), int(b["verdict"] != o["verdict"])))
        g["I3_vs_I2_paired_descriptive"] = paired(pairs)
        i3[s] = g
    lost = Counter(it["label"] for it in items.values() if it["mr"] == "I3" and not it.get("text"))
    from scipy.stats import chisquare, chi2_contingency
    kept = Counter(it["label"] for it in per_mr["I3"])
    tab = [[lost[l] for l in ("hatespeech", "offensive", "normal")], [kept[l] for l in ("hatespeech", "offensive", "normal")]]
    c2 = chi2_contingency(tab)
    stats["I3"] = {"construction": "paraphrased by gemma2:9b (also evaluated); equivalence judged by qwen2.5:7b (also evaluated), two directions",
                   "items_created": 600, "items_with_text": len(per_mr["I3"]), "items_without_text": sum(lost.values()),
                   "lost_by_label": dict(lost), "kept_by_label": dict(kept),
                   "loss_vs_label_chi2": {"chi2": round(c2[0], 3), "df": c2[2], "p": float(f"{c2[1]:.3g}")},
                   "by_system": i3,
                   "circularity_check": "compare gemma2 (author of the paraphrases) and qwen2.5 (the judge) with the other systems "
                                        "on judge_equivalent vs judge_not_equivalent and human_valid vs human_invalid; descriptive only"}

    # ---------- 6. direct vs evidence (family F_P) and LLM vs word-LR (family F_B), on ORIG
    def orig_pairs(sa, sb, both_answered=False):
        out = []
        for p in posts:
            it = orig[p]; xa, xb = by[sa][it["item_id"]], by[sb][it["item_id"]]
            if both_answered and not (xa["category"] in ANSWERED and xb["category"] in ANSWERED): continue
            out.append((int(ok(it, xa)), int(ok(it, xb))))
        return out
    fp = {}
    for m in ("qwen2.5:7b", "llama3.1:8b", "gemma2:9b"):
        fp[m] = {"all_posts_nonanswer_wrong": paired(orig_pairs(f"{m}|evidence", f"{m}|direct")),
                 "posts_answered_in_both": paired(orig_pairs(f"{m}|evidence", f"{m}|direct", True))}
    for k in ("all_posts_nonanswer_wrong", "posts_answered_in_both"):
        h = holm({m: fp[m][k]["mcnemar_exact_p"] for m in fp})
        for m in fp: fp[m][k]["holm_p_family_F_P"] = h[m]
    fb = {s: {"all_posts_nonanswer_wrong": paired(orig_pairs(s, "word-LR")), "posts_answered_by_llm": paired(orig_pairs(s, "word-LR", True))} for s in llms}
    for k in ("all_posts_nonanswer_wrong", "posts_answered_by_llm"):
        h = holm({s: fb[s][k]["mcnemar_exact_p"] for s in fb})
        for s in fb: fb[s][k]["holm_p_family_F_B"] = h[s]
    stats["direct_vs_evidence_ORIG"] = {"family_F_P": "3 tests per variant (one per model), x = evidence correct, y = direct correct; Holm", "results": fp}
    stats["llm_vs_wordLR_ORIG"] = {"family_F_B": "6 tests per variant (each LLM condition vs word-LR), x = LLM correct, y = word-LR correct; Holm", "results": fb}

    # ---------- 7. human validation: agreement and oracle validity
    vrows = list(val.values())
    def kappa_ci(rs):
        bp = defaultdict(list)
        for r in rs: bp[r["post_id"]].append((r["r1"], r["r2"]))
        keys = list(bp); rng = random.Random(SEED); est = []
        for _ in range(B_POOLED):
            sm = [pr for _ in keys for pr in bp[keys[rng.randrange(len(keys))]]]
            k_ = kappa(sm)
            if k_ is not None: est.append(k_)
        est.sort(); return [round(est[int(.025 * len(est))], 3), round(est[int(.975 * len(est)) - 1], 3)] if est else [None, None]
    agree = {}
    for m in ["ALL", *VALIDATED_MRS]:
        rs = [r for r in vrows if m == "ALL" or r["mr"] == m]; pr = [(r["r1"], r["r2"]) for r in rs]
        agree[m] = {"n": len(rs), "pct_agree": rate(sum(a == b for a, b in pr), len(pr)), "cohen_kappa": round(kappa(pr), 3) if kappa(pr) is not None else None,
                    "kappa_ci95_post_bootstrap": kappa_ci(rs), "disagreements": sum(a != b for a, b in pr),
                    "adjudicated": sum(1 for r in rs if r["r1"] != r["r2"] and r["adj"] is not None),
                    "pending": sum(r["status"] == "pending" for r in rs)}
    stats["human_validation"] = {"raters": 2, "rater_identity_background": "not documented",
                                 "procedure": "Ya/Tidak dropdown per item in human_validation.xlsx (hitl_sheet.py); a third 'Keputusan' column settles disagreements",
                                 "independence": "not enforced: both raters' sheets are in the same workbook; whether raters saw each other's answers is not documented",
                                 "adjudicator": "not documented", "agreement": agree,
                                 "pending_items": [k for k, r in val.items() if r["status"] == "pending"]}

    # oracle validity per stratum + model sensitivity
    ov = []
    pop = {"E1": len(per_mr["E1"]), "E2": len(per_mr["E2"]), "I1": len(per_mr["I1"]), "I3": len(per_mr["I3"])}
    def vstat(ids):
        st = Counter(val[i]["status"] for i in ids); return st["valid"], st["invalid"], st["pending"]
    for m in ("E1", "E2", "I1", "I3"):
        ids = [it["item_id"] for it in per_mr[m] if it["item_id"] in val]; k, bad, pend = vstat(ids)
        ov.append({"row_type": "oracle_validity", "mr": m, "stratum": "all", "population_N": pop[m], "sampled_n": len(ids), "design": "simple random 20% (seed 42)",
                   "n_valid": k, "n_invalid": bad, "n_pending": pend, "validity": rate(k, k + bad), "validity_ci95": wilson(k, k + bad)})
        if pend:
            for as_ in ("valid", "invalid"):
                kk, bb = (k + pend, bad) if as_ == "valid" else (k, bad + pend)
                ov.append({"row_type": "oracle_validity", "mr": m, "stratum": f"all (pending counted {as_})", "population_N": pop[m], "sampled_n": len(ids),
                           "design": "sensitivity for pending adjudication", "n_valid": kk, "n_invalid": bb, "n_pending": 0, "validity": rate(kk, kk + bb), "validity_ci95": wilson(kk, kk + bb)})
    Ns = Counter(strata.values()); r2v = {}
    for g in ("offensive_ambiguous", "offensive_control", "hatespeech", "normal"):
        ids = [i for i in val if val[i]["mr"] == "R2" and strata.get(i) == g]; k, bad, pend = vstat(ids)
        r2v[g] = (k, bad)
        ov.append({"row_type": "oracle_validity", "mr": "R2", "stratum": g, "population_N": Ns[g], "sampled_n": len(ids),
                   "design": {"offensive_ambiguous": "census (all items)", "offensive_control": "simple random 20% of stratum"}.get(g, "NOT VALIDATED"),
                   "n_valid": k, "n_invalid": bad, "n_pending": pend, "validity": rate(k, k + bad) if ids else None, "validity_ci95": wilson(k, k + bad) if ids else [None, None]})
    (ka, ba), (kc, bc) = r2v["offensive_ambiguous"], r2v["offensive_control"]
    Na, Nc = Ns["offensive_ambiguous"], Ns["offensive_control"]; pa, pc = ka / (ka + ba), kc / (kc + bc); nc = kc + bc
    w_est = (Na * pa + Nc * pc) / (Na + Nc)
    se = math.sqrt((Nc / (Na + Nc)) ** 2 * pc * (1 - pc) / nc * (1 - nc / Nc))
    ov.append({"row_type": "oracle_validity", "mr": "R2", "stratum": "offensive (stratum-weighted)", "population_N": Na + Nc, "sampled_n": ka + ba + nc,
               "design": "census + 20% sample, weights N_h/N, FPC on control", "n_valid": ka + kc, "n_invalid": ba + bc, "n_pending": 0,
               "validity": round(w_est, 4), "validity_ci95": [round(max(0, w_est - 1.96 * se), 4), round(min(1, w_est + 1.96 * se), 4)]})
    ov.append({"row_type": "oracle_validity", "mr": "R2", "stratum": "all R2 (600)", "population_N": sum(Ns.values()), "sampled_n": ka + ba + nc,
               "design": "hatespeech and normal strata (400 items) never validated", "validity": "not identifiable",
               "note": "the unweighted 44.8% in validation.json mixes a census of ambiguous cases with a small control sample and does not describe R2"})

    # model sensitivity: A original/all, B original/validated, C corrected/validated, D population estimate, E contamination bounds
    def sens_binary(s, m, its, q_ci):
        X = by[s]; ans = [it for it in its if X[it["item_id"]]["category"] in ANSWERED]
        vd = [it for it in ans if val.get(it["item_id"], {}).get("status") in ("valid", "invalid")]
        un = [it for it in ans if it["item_id"] not in val or val[it["item_id"]]["status"] == "pending"]
        A = sum(ok(it, X[it["item_id"]]) for it in ans); Bv = sum(ok(it, X[it["item_id"]]) for it in vd)
        C = sum(ok_corrected(it, X[it["item_id"]], val[it["item_id"]]["status"] == "valid") for it in vd)
        P = sum(ok(it, X[it["item_id"]]) for it in un); F = sum(1 for it in un if not ok(it, X[it["item_id"]]) and X[it["item_id"]]["verdict"] in (V, NV))
        k_hi = math.ceil(q_ci[1] * len(un)) if q_ci[1] is not None else len(un)
        lo, hi = (C + P - min(k_hi, P)) / max(1, len(vd) + len(un)), (C + P + min(k_hi, F)) / max(1, len(vd) + len(un))
        return {"A_all_items_original_oracle": rate(A, len(ans)), "A_n": len(ans), "A_ci95": wilson(A, len(ans)),
                "B_validated_original_oracle": rate(Bv, len(vd)), "B_n": len(vd),
                "C_validated_corrected_oracle": rate(C, len(vd)), "C_ci95": wilson(C, len(vd)),
                "E_bounds_all_items_corrected": [round(lo, 4), round(hi, 4)], "E_assumed_max_invalid_unvalidated": k_hi}
    inval_ci = {}
    for r in ov:
        if r["row_type"] == "oracle_validity" and r["stratum"] in ("all", "offensive_control"):
            v = r["validity_ci95"]; inval_ci[(r["mr"], r["stratum"])] = [1 - v[1], 1 - v[0]] if v[0] is not None else [None, None]
    for s in names:
        X = by[s]
        for m in ("E1", "E2"):
            ov.append({"row_type": "model_sensitivity", "system": s, "mr": m, "stratum": "all", "metric": "pass among answered (strict)",
                       **sens_binary(s, m, per_mr[m], inval_ci[(m, "all")])})
        for g in ("offensive_ambiguous", "offensive_control", "hatespeech", "normal"):
            its = [it for it in per_mr["R2"] if strata[it["item_id"]] == g]
            if g in ("hatespeech", "normal"):
                ans = [it for it in its if X[it["item_id"]]["category"] in ANSWERED]; A = sum(ok(it, X[it["item_id"]]) for it in ans)
                ov.append({"row_type": "model_sensitivity", "system": s, "mr": "R2", "stratum": g, "metric": "pass among answered (strict)",
                           "A_all_items_original_oracle": rate(A, len(ans)), "A_n": len(ans), "A_ci95": wilson(A, len(ans)),
                           "E_bounds_all_items_corrected": [0.0, 1.0], "note": "oracle never validated: corrected value not identified"})
            else:
                q = [0.0, 0.0] if g == "offensive_ambiguous" else inval_ci[("R2", "offensive_control")]
                ov.append({"row_type": "model_sensitivity", "system": s, "mr": "R2", "stratum": g, "metric": "pass among answered (strict)", **sens_binary(s, "R2", its, q)})
        # weighted corrected R2-offensive estimate (D)
        def corr_rate(g):
            its = [it for it in per_mr["R2"] if strata[it["item_id"]] == g and val.get(it["item_id"], {}).get("status") in ("valid", "invalid") and X[it["item_id"]]["category"] in ANSWERED]
            return rate(sum(ok_corrected(it, X[it["item_id"]], val[it["item_id"]]["status"] == "valid") for it in its), len(its)), len(its)
        (ra, na_), (rc_, nc_) = corr_rate("offensive_ambiguous"), corr_rate("offensive_control")
        if ra is not None and rc_ is not None:
            ov.append({"row_type": "model_sensitivity", "system": s, "mr": "R2", "stratum": "offensive (stratum-weighted)", "metric": "pass among answered (strict)",
                       "D_population_estimate_corrected": round((Na * ra + Nc * rc_) / (Na + Nc), 4), "D_n_ambiguous": na_, "D_n_control": nc_,
                       "note": "weights use stratum sizes; answered-only items"})
        for m in ("I1", "I3"):
            its = per_mr[m]; cs = {it["item_id"]: consistency(it, X, orig) for it in its}
            def fl(sel):
                b = [cs[it["item_id"]][1] for it in its if sel(it) and cs[it["item_id"]][0]]; return rate(len(b) - sum(b), len(b)), len(b)
            a_, an = fl(lambda it: True); vv, vn = fl(lambda it: val.get(it["item_id"], {}).get("status") == "valid")
            nb, nbn = fl(lambda it: val.get(it["item_id"], {}).get("status") != "invalid")
            ov.append({"row_type": "model_sensitivity", "system": s, "mr": m, "stratum": "all", "metric": "invariance (no flip vs own ORIG) among answered pairs",
                       "A_all_items_original_oracle": a_, "A_n": an, "C_validated_corrected_oracle": vv, "B_n": vn,
                       "D_population_estimate_corrected": vv, "excluding_known_invalid": nb, "excluding_known_invalid_n": nbn,
                       "note": "corrected = only human-valid items (invalid items are not invariance tests); pending item excluded"})
    cols = list(dict.fromkeys(k for r in ov for k in r))
    with open(f"{OUT}/oracle_validity_analysis.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in ov: w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()})
    stats["oracle_validity"] = [r for r in ov if r["row_type"] == "oracle_validity"]

    # pending-item sensitivity on I3 invariance for every system
    pend = stats["human_validation"]["pending_items"]
    stats["pending_item_sensitivity"] = {}
    for s in names:
        X = by[s]; res = {}
        for as_ in ("excluded", "valid", "invalid"):
            def st(it):
                v = val.get(it["item_id"], {}).get("status")
                return ("valid" if as_ == "valid" else "invalid") if (v == "pending" and as_ != "excluded") else v
            b = [consistency(it, X, orig) for it in per_mr["I3"] if st(it) == "valid"]; b = [f for a, f in b if a]
            res[as_] = {"n_pairs": len(b), "invariance_rate_on_human_valid_I3": rate(len(b) - sum(b), len(b))}
        stats["pending_item_sensitivity"][s] = res
    stats["pending_item_sensitivity"]["items"] = pend

    # ---------- 7b. E1 residual identity terms (refusal-aware) + check against human oracle validity
    import importlib.util
    from scipy.stats import fisher_exact
    spec = importlib.util.spec_from_file_location("bi", "build_items.py"); bi = importlib.util.module_from_spec(spec); spec.loader.exec_module(bi)
    IDENT = set().union(*bi.GROUP_TERMS.values())
    has_id = lambda it: any(t in IDENT for t in toks(it["text"]))
    e1v = [it for it in per_mr["E1"] if val.get(it["item_id"], {}).get("status") in ("valid", "invalid")]
    xt = [[sum(1 for it in e1v if has_id(it) and val[it["item_id"]]["status"] == st) for st in ("invalid", "valid")],
          [sum(1 for it in e1v if not has_id(it) and val[it["item_id"]]["status"] == st) for st in ("invalid", "valid")]]
    resid = {"definition": "E1 items: flagged = verdict 'violating'; identity term = any build_items.GROUP_TERMS token left in the E1 text; "
                           "answered items only (refusals and unparseable excluded)",
             "human_validity_by_identity_term": {"table_rows_identity_yes_no_cols_invalid_valid": xt,
                                                 "invalid_share_with_identity": rate(xt[0][0], sum(xt[0])), "invalid_share_without_identity": rate(xt[1][0], sum(xt[1])),
                                                 "fisher_p": float(f"{fisher_exact(xt)[1]:.3g}")}, "by_system": {}}
    for variant, keep in (("all_answered", lambda it: True), ("excluding_human_invalid", lambda it: val.get(it["item_id"], {}).get("status") != "invalid")):
        ps = {}
        for s in names:
            X = by[s]; its = [it for it in per_mr["E1"] if keep(it) and X[it["item_id"]]["category"] in ANSWERED]
            a = [it for it in its if has_id(it)]; b_ = [it for it in its if not has_id(it)]
            fa = sum(X[it["item_id"]]["verdict"] == V for it in a); fb_ = sum(X[it["item_id"]]["verdict"] == V for it in b_)
            orr, p = fisher_exact([[fa, len(a) - fa], [fb_, len(b_) - fb_]])
            resid["by_system"].setdefault(s, {})[variant] = {"flagged_with_identity": [rate(fa, len(a)), fa, len(a), wilson(fa, len(a))],
                                                             "flagged_without_identity": [rate(fb_, len(b_)), fb_, len(b_), wilson(fb_, len(b_))],
                                                             "odds_ratio": round(orr, 3) if orr != float("inf") else None, "fisher_p": float(f"{p:.4g}")}
            ps[s] = p
        h = holm(ps)
        for s in names: resid["by_system"][s][variant]["holm_p_family_F_R"] = h[s]
    resid["family_F_R"] = "8 Fisher tests (one per system) per variant; Holm"
    stats["E1_residual_identity_terms"] = resid

    # ---------- 8. model comparison table
    mc = []
    for meta in systems:
        s = meta["system"]; b_ = beh[s]; f_ = fam[s]; g3 = i3[s]
        mc.append({"system": s, "model": meta["model"], "prompt": meta["prompt"],
                   "ORIG_coverage_valid": M[(s, "ORIG")]["coverage_valid"], "ORIG_cond_acc_valid": M[(s, "ORIG")]["cond_acc_valid"],
                   "ORIG_cond_acc_valid_ci95": json.dumps(M[(s, "ORIG")]["cond_acc_valid_ci95"]),
                   "ORIG_overall_acc_nonanswer_wrong": M[(s, "ORIG")]["overall_acc_nonanswer_wrong"],
                   "ALL_refusal_rate": M[(s, "ALL")]["refusal_rate"], "ALL_refusal_ci95": json.dumps(M[(s, "ALL")]["refusal_ci95"]),
                   "ALL_abstention_rate": M[(s, "ALL")]["abstention_rate"], "ALL_unparseable_rate": M[(s, "ALL")]["unparseable_rate"],
                   "ALL_generation_error_rate": M[(s, "ALL")]["generation_error_rate"], "ALL_empty_rate": M[(s, "ALL")]["empty_rate"],
                   "E1_pass_answered": M[(s, "E1")]["cond_acc_answered"], "E1_retained_violating": b_["E1"]["retained_violating_after_removal"][0],
                   "E1_quotes_cite_removed_words": b_["E1"]["quotes_cite_removed_words"][0],
                   "E2_pass_answered": M[(s, "E2")]["cond_acc_answered"], "E2_turned_violating": b_["E2"]["turned_violating_after_insertion"][0],
                   "E2_quotes_cite_injected": b_["E2"]["quotes_cite_injected_words"][0],
                   "R1_abstained_among_answered": b_["R1"]["abstained_among_answered"][0], "R1_refusals": b_["R1"]["refused"],
                   "R2_pass_label_changes_ambiguous": b_["R2"]["offensive_ambiguous"]["pass_among_answered"][0],
                   "R2_pass_label_changes_control": b_["R2"]["offensive_control"]["pass_among_answered"][0],
                   "R2_pass_label_stays_hate": b_["R2"]["hatespeech"]["pass_among_answered"][0], "R2_pass_label_stays_normal": b_["R2"]["normal"]["pass_among_answered"][0],
                   "R3_verdict_changed": b_["R3"]["verdict_changed_vs_orig"][0],
                   "I1I2_complete_triples": f_["coverage_complete_triples"][1], "I1_flip": f_["rate_x"], "I2_flip": f_["rate_y"],
                   "I1_minus_I2": f_.get("risk_difference"), "I1_minus_I2_ci95": json.dumps(f_.get("rd_ci95_post_bootstrap")),
                   "I1_vs_I2_p": f_.get("mcnemar_exact_p"), "I1_vs_I2_p_holm": f_.get("holm_p_family_F_I"),
                   "I3_flip_all": g3["all_with_text"]["flip_rate"], "I3_flip_judge_eq": g3["judge_equivalent"]["flip_rate"],
                   "I3_flip_judge_not_eq": g3["judge_not_equivalent"]["flip_rate"], "I3_flip_human_valid": g3["human_valid"]["flip_rate"],
                   # appended after the original columns (JSC v3 reproduction): shares of the 600 ORIG posts, same denominator as ORIG_coverage_valid
                   "ORIG_refusal_rate": M[(s, "ORIG")]["refusal_rate"], "ORIG_abstention_rate": M[(s, "ORIG")]["abstention_rate"]})
    with open(f"{OUT}/model_comparison.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(mc[0])); w.writeheader(); w.writerows(mc)

    # ---------- 9. before / after
    before = json.load(open("results/_sebelum_refusal/revised_llm600.json"))["systems"]
    oldval = json.load(open("validation.json"))
    ba = []
    def add(fid, finding, system, metric, initial, audited, reason):
        delta = round(audited - initial, 4) if isinstance(initial, (int, float)) and isinstance(audited, (int, float)) else ""
        ba.append({"id": fid, "finding": finding, "system": system, "metric": metric, "initial": initial, "audited": audited, "change": delta, "reason": reason})
    for s in ("llama3.1:8b|direct", "llama3.1:8b|evidence"):
        add("F1", "llama3.1 accuracy", s, "ORIG accuracy (refusal counted wrong) -> conditional accuracy on valid verdicts",
            before[s]["verdict_accuracy_EV1"], M[(s, "ORIG")]["cond_acc_valid"], "refusals are not wrong answers; report coverage + conditional accuracy together")
        add("F1", "llama3.1 coverage", s, "ORIG valid-verdict coverage", "", M[(s, "ORIG")]["coverage_valid"], "new metric")
        add("F2", "llama3.1 R1 pass", s, "R1 pass (refusal stored as insufficient) -> R1 pass, refusal never passes",
            before[s]["verdict_only_MR_pass"]["R1"][0], M[(s, "R1")]["overall_acc_nonanswer_wrong"], "refusal had been counted as the correct abstention")
        for m in ("I1", "I2"):
            add("F3", f"llama3.1 {m} invariance", s, f"{m} pass (refusal==refusal counted invariant) -> flip rate on answered pairs",
                before[s]["verdict_only_MR_pass"][m][0], M[(s, m)]["flip_rate_vs_own_orig"], "invariance only defined when both verdicts exist")
    for s in names:
        bi = before[s]["identity_swap"]["mcnemar_discordant"]["exact_p"]
        add("F4", "I1 vs I2 significance", s, "McNemar p (uncorrected) -> Holm-adjusted over 8 systems", bi, fam[s]["holm_p_family_F_I"], "family of 8 simultaneous tests")
    for s in ("qwen2.5:7b|direct", "qwen2.5:7b|evidence", "gemma2:9b|direct", "gemma2:9b|evidence"):
        oldins = sum(1 for x in by[s].values() if x["stored_verdict"] == INS)
        add("F5", "abstention count", s, "items stored as insufficient -> ABSTENTION", oldins, sum(1 for x in by[s].values() if x["category"] == "ABSTENTION"),
            "unparseable answers and null verdicts had been folded into insufficient")
    add("F6", "llama3.1 refusals", "llama3.1:8b|direct", "refusals (first regex) -> audited classifier", 2383, rc["summary"]["llama3.1:8b|direct"].get("REFUSAL", 0),
        "3 'I cannot determine ...' answers are abstentions")
    add("F7", "R2 oracle validity", "-", "unweighted validity -> stratum-weighted (offensive only)", oldval["validity_by_mr"]["R2"], round(w_est, 4),
        "ambiguous cases were a census; hatespeech/normal strata not validated")
    k1, b1, _ = vstat([i for i in val if val[i]["mr"] == "I1"])
    add("F8", "I1 item validity", "-", f"validity (n={k1 + b1})", oldval["validity_by_mr"]["I1"], rate(k1, k1 + b1),
        "same value; now with Wilson CI " + json.dumps(wilson(k1, k1 + b1)))
    for s in names:
        e1 = [r for r in ov if r.get("row_type") == "model_sensitivity" and r.get("system") == s and r["mr"] == "E1"][0]
        add("F9", "E1 pass under corrected oracle", s, "E1 pass (original oracle, answered) -> validated subset, corrected oracle",
            e1["A_all_items_original_oracle"], e1["C_validated_corrected_oracle"], "16.5% of sampled E1 items still contain an attack")
    with open(f"{OUT}/before_after.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ba[0])); w.writeheader(); w.writerows(ba)

    stats["model_metadata"] = systems
    json.dump(stats, open(f"{OUT}/statistical_analysis.json", "w"), indent=1)
    print("written:", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
