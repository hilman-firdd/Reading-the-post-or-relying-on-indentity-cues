#!/usr/bin/env python3
"""
Stereotype analysis for MR-E1 (evidence erasure).

After the annotators' rationale tokens are removed, a grounded moderator should no longer
flag the post. If it still flags it, what is left in the text? We compare the still-flagged
rate for erased posts that still mention a protected-group identity term versus those that
do not (chi-square / Fisher), and list the tokens the word-LR model cites after erasure.
"""
import argparse, json
from collections import Counter
from scipy.stats import fisher_exact
import importlib.util, os

spec = importlib.util.spec_from_file_location("bi", os.path.join(os.path.dirname(__file__), "build_items.py"))
bi = importlib.util.module_from_spec(spec); spec.loader.exec_module(bi)
IDENTITY = set().union(*bi.GROUP_TERMS.values())

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--items", required=True); ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", required=True); a = ap.parse_args()
    items = {json.loads(l)["item_id"]: json.loads(l) for l in open(a.items)}
    out = {}
    for p in a.runs:
        recs = [json.loads(l) for l in open(p)]; name = recs[0]["system"]
        e1 = [(items[r["item_id"]], r) for r in recs if items.get(r["item_id"], {}).get("mr") == "E1"]
        has = [(it, r) for it, r in e1 if IDENTITY & set(it["tokens"])]
        no = [(it, r) for it, r in e1 if not (IDENTITY & set(it["tokens"]))]
        fl = lambda xs: sum(r["verdict"] == "violating" for _, r in xs)
        t = [[fl(has), len(has) - fl(has)], [fl(no), len(no) - fl(no)]]
        odds, p_ = fisher_exact(t)
        cited = Counter(q for _, r in e1 if r["verdict"] == "violating" for q in r.get("quotes", []))
        out[name] = {"E1_items": len(e1),
                     "still_flagged_with_identity_term": [round(fl(has) / max(1, len(has)), 4), len(has)],
                     "still_flagged_without_identity_term": [round(fl(no) / max(1, len(no)), 4), len(no)],
                     "fisher_odds_ratio": round(float(odds), 3), "fisher_p": float(f"{p_:.3g}"),
                     "share_of_cited_tokens_that_are_identity_terms": round(sum(c for t_, c in cited.items() if t_ in IDENTITY) / max(1, sum(cited.values())), 4) if cited else None,
                     "top_identity_tokens_cited": [(t_, c) for t_, c in cited.most_common(200) if t_ in IDENTITY][:10]}
        # paired control: identity swap (I1) vs neutral distractor (I2) on the same posts
        by = {}
        for r in recs:
            it = items.get(r["item_id"])
            if it: by.setdefault(it["post_id"], {})[it["mr"]] = r["verdict"]
        pairs = [(v["ORIG"] != v["I1"], v["ORIG"] != v["I2"]) for v in by.values() if {"ORIG", "I1", "I2"} <= set(v)]
        b = sum(x and not y for x, y in pairs); c = sum(y and not x for x, y in pairs); n = b + c
        import math
        pv = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)
        out[name]["I1_vs_I2_paired"] = {"n_posts": len(pairs), "flip_I1": round(sum(x for x, _ in pairs) / max(1, len(pairs)), 4),
                                        "flip_I2": round(sum(y for _, y in pairs) / max(1, len(pairs)), 4),
                                        "only_I1_flips": b, "only_I2_flips": c, "mcnemar_p": float(f"{pv:.3g}")}
    print(json.dumps(out, indent=1)); json.dump(out, open(a.out, "w"), indent=1)

if __name__ == "__main__":
    main()
