#!/usr/bin/env python3
"""
analysis_e1_missing.py — sensitivity of the E1 residual-identity association to non-answers.

Table 5 of the manuscript computes the odds ratio (OR) between "an identity term remains after
erasure" and "still flagged" on ANSWERED E1 items only (valid verdict or abstention). Refusals,
unparseable, empty and error responses are excluded. If the chance of answering depends on the
identity term, that conditional OR can be biased (selection on the outcome model's own behaviour).

This script is READ-ONLY on runs/ and items. For every system it reports
  1. the response breakdown of the 397 E1 items, split by identity term (yes/no);
  2. the OR on answered items (reproduces Table 5);
  3. the OR when every non-answer is coded as flagged, and as not flagged;
  4. worst-case bounds: non-answers coded against the association (identity -> not flagged,
     no identity -> flagged) and in favour of it (the reverse).
Bounds 3-4 are deterministic codings, not imputations; they show how far the conclusion could move.

  python analysis_e1_missing.py      -> results/audited/e1_missing_sensitivity.json (+ printed table)
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_metrics as am  # noqa: E402
from response_classifier import ANSWERED  # noqa: E402
from scipy.stats import fisher_exact  # noqa: E402
import importlib.util  # noqa: E402

V = "violating"


def odds(fa, na, fb, nb):
    t = [[fa, na - fa], [fb, nb - fb]]
    orr, p = fisher_exact(t)
    return (None if orr in (float("inf"),) else round(float(orr), 2)), float(f"{p:.3g}")


def main():
    items, run_items, orig, systems, records, by = am.load()
    spec = importlib.util.spec_from_file_location("bi", "build_items.py")
    bi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bi)
    ident = set().union(*bi.GROUP_TERMS.values())
    has_id = lambda it: any(t in ident for t in am.toks(it["text"]))  # noqa: E731
    e1 = [it for it in run_items.values() if it["mr"] == "E1"]
    out = {"n_E1": len(e1), "definition": "answered = VALID_VERDICT or ABSTENTION; flagged = verdict 'violating'",
           "by_system": {}}
    print(f"E1 items: {len(e1)}  (with identity term: {sum(map(has_id, e1))})\n")
    hdr = (f"{'system':22} {'grp':4} {'n':>4} {'valid':>5} {'abst':>5} {'refus':>5} {'other':>5} "
           f"| OR answ | OR na=flag | OR na=not | OR worst | OR best")
    print(hdr)
    for meta in systems:
        s = meta["system"]
        X = by[s]
        res = {}
        cells = {}
        for g, sel in (("id", [it for it in e1 if has_id(it)]), ("no", [it for it in e1 if not has_id(it)])):
            cat = Counter(X[it["item_id"]]["category"] for it in sel)
            ans = [it for it in sel if X[it["item_id"]]["category"] in ANSWERED]
            flag = sum(X[it["item_id"]]["verdict"] == V for it in ans)
            na = len(sel) - len(ans)
            cells[g] = (len(sel), len(ans), flag, na)
            res[g] = {"n": len(sel), "valid_verdict": cat.get("VALID_VERDICT", 0), "abstention": cat.get("ABSTENTION", 0),
                      "refusal": cat.get("REFUSAL", 0),
                      "other_nonanswer": sum(v for k, v in cat.items() if k not in ("VALID_VERDICT", "ABSTENTION", "REFUSAL")),
                      "answered": len(ans), "flagged_among_answered": flag}
        (ni, ai, fi, mi), (nn, an, fn, mn) = cells["id"], cells["no"]
        res["OR_answered"] = odds(fi, ai, fn, an)
        res["OR_nonanswer_as_flagged"] = odds(fi + mi, ni, fn + mn, nn)
        res["OR_nonanswer_as_not_flagged"] = odds(fi, ni, fn, nn)
        res["OR_worst_case"] = odds(fi, ni, fn + mn, nn)          # against the association
        res["OR_best_case"] = odds(fi + mi, ni, fn, nn)           # in favour of the association
        out["by_system"][s] = res
        for g in ("id", "no"):
            r = res[g]
            tail = ""
            if g == "id":
                tail = (f"| {res['OR_answered'][0]!s:>7} | {res['OR_nonanswer_as_flagged'][0]!s:>10} | "
                        f"{res['OR_nonanswer_as_not_flagged'][0]!s:>9} | {res['OR_worst_case'][0]!s:>8} | {res['OR_best_case'][0]!s:>7}")
            print(f"{s if g == 'id' else '':22} {g:4} {r['n']:>4} {r['valid_verdict']:>5} {r['abstention']:>5} "
                  f"{r['refusal']:>5} {r['other_nonanswer']:>5} {tail}")
    os.makedirs("results/audited", exist_ok=True)
    with open("results/audited/e1_missing_sensitivity.json", "w") as fh:
        json.dump(out, fh, indent=1)
    print("\nwritten: results/audited/e1_missing_sensitivity.json")


if __name__ == "__main__":
    main()
