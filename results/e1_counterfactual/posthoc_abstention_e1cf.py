#!/usr/bin/env python3
"""
POST HOC sensitivity of E1-CF H1 (PLC - NEU) to the abstention convention. NOT part of the pre-specified protocol
(see PROTOCOL.md section 8, entry 3).

Primary analysis (protocol): abstention counts as 'not flagged'; pairs = both conditions answered (valid verdict or abstention).
This script: (a) transition table PLC -> NEU by response category; (b) H1 recomputed on VALID_VERDICT only
(abstentions removed), with exact McNemar, risk difference and Holm over the 4 qwen2.5/gemma2 conditions (post hoc family).

Adapted from scripts/posthoc_abstention_e1cf.py of JSC_v3_kit.zip: ONLY the path handling differs (repository root is found from
this file's location; default output next to this file). The computation is unchanged.

Reads: results/e1_counterfactual/{items_e1cf.jsonl, runs/*.jsonl, analysis.json} and the response classifier. Writes only --out.
Usage (from anywhere):
  PYTHONDONTWRITEBYTECODE=1 python results/e1_counterfactual/posthoc_abstention_e1cf.py [--repo <repo>] [--out <file.json>]
"""
import argparse, json, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--repo", default=os.path.abspath(os.path.join(HERE, "..", "..")))
ap.add_argument("--out", default=os.path.join(HERE, "posthoc_valid_only.json"))
a = ap.parse_args()
os.chdir(a.repo)
sys.dont_write_bytecode = True
sys.path.insert(0, a.repo)
from response_classifier import classify_record  # noqa: E402
from audit_metrics import paired, holm  # noqa: E402

D = "results/e1_counterfactual"
items = {}
for l in open(f"{D}/items_e1cf.jsonl"):
    it = json.loads(l)
    items[it["item_id"]] = it
SYS = {"qwen2.5:7b|direct": "qwen2.5_7b_direct", "qwen2.5:7b|evidence": "qwen2.5_7b_evidence",
       "gemma2:9b|direct": "gemma2_9b_direct", "gemma2:9b|evidence": "gemma2_9b_evidence"}
analysis = json.load(open(f"{D}/analysis.json"))          # read-only: used for a consistency check of the primary analysis
res, ps = {}, {}
for s, fn in SYS.items():
    S = {}
    for l in open(f"{D}/runs/{fn}.jsonl"):
        r = json.loads(l)
        it = items[r["item_id"]]
        c = classify_record(r)
        S.setdefault(it["e1_item_id"], {})[it["cf_condition"]] = (c["category"], c.get("verdict"))
    def lab(x):
        cat, v = x
        return "violating" if (cat == "VALID_VERDICT" and v == "violating") else ("not_violating" if cat == "VALID_VERDICT" else cat)
    trans = Counter((lab(S[p]["PLC"]), lab(S[p]["NEU"])) for p in S)
    pr = [(int(lab(S[p]["PLC"]) == "violating"), int(lab(S[p]["NEU"]) == "violating"))
          for p in S if S[p]["PLC"][0] == "VALID_VERDICT" and S[p]["NEU"][0] == "VALID_VERDICT"]
    t = paired(pr)
    res[s] = {"transitions_PLC_to_NEU": {f"{k[0]}->{k[1]}": v for k, v in sorted(trans.items())},
              "valid_only": t}
    ps[s] = t["mcnemar_exact_p"]
    # consistency check against the primary analysis (answered = valid verdict or abstention; abstention = not flagged)
    prim = [(int(lab(S[p]["PLC"]) == "violating"), int(lab(S[p]["NEU"]) == "violating"))
            for p in S if S[p]["PLC"][0] in ("VALID_VERDICT", "ABSTENTION") and S[p]["NEU"][0] in ("VALID_VERDICT", "ABSTENTION")]
    h = analysis["systems"][s]["H1_PLC_minus_NEU"]
    ok = len(prim) == h["n_pairs"] and abs(sum(x for x, _ in prim) / len(prim) - h["rate_x"]) < 1e-3 and abs(sum(y for _, y in prim) / len(prim) - h["rate_y"]) < 1e-3
    print(f"[check vs analysis.json] {s}: primary n_pairs {len(prim)} == {h['n_pairs']} and flag rates match: {ok}")
    if not ok:
        sys.exit("primary analysis could not be reproduced from the runs; stopping")
h = holm(ps) if callable(holm) else None
for s in res:
    res[s]["valid_only"]["holm_p_posthoc_4"] = (h or {}).get(s)
json.dump(res, open(a.out, "w"), indent=1)
for s, v in res.items():
    t = v["valid_only"]
    print(s, "pairs", t["n_pairs"], "RD", t["risk_difference"], "b/c", t["b_only_x"], t["c_only_y"], "p", t["mcnemar_exact_p"], "holm", t["holm_p_posthoc_4"])
    print("   ", v["transitions_PLC_to_NEU"])
