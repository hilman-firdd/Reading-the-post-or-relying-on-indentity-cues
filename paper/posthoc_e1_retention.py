"""POST HOC (added for manuscript v25 after audit #9; not in any protocol).

Separates the two E1 populations that Table 5 mixes:
  (a) retention: among posts the system flagged at ORIG (valid verdict 'violating') and answered after erasure (valid verdict or abstention),
      is the flag kept more often when an identity term remains?  -> same population as Table 5 columns n / Kept / To not / To ins.
  (b) the audited association (all answered E1 posts) is NOT recomputed here; it stays in results/audited/statistical_analysis.json.
Identity detection, answered-set definition and the 'flag' definition are those of the audit (verify_numbers.py).
Sample OR, exact conditional 95% CI, Fisher exact p, Holm over the same 8 systems as family F_R.

Usage: python3 paper/posthoc_e1_retention.py <repo> <out_dir>      (read-only on the repo; writes <out_dir>/posthoc_e1_retention.json)
"""
import json, os, sys
from collections import defaultdict

repo, out = sys.argv[1], sys.argv[2]
os.chdir(repo)
sys.dont_write_bytecode = True
sys.path.insert(0, repo)
from build_items import GROUP_TERMS  # noqa: E402
from scipy.stats import fisher_exact  # noqa: E402
from scipy.stats.contingency import odds_ratio  # noqa: E402

allterms = set().union(*GROUP_TERMS.values())
items = {}
for line in open("items_llm600.jsonl"):
    d = json.loads(line); items[d["item_id"]] = d
S = defaultdict(dict)
for r in json.load(open("results/audited/response_classification.json"))["records"]:
    S[r["system"]][r["item_id"]] = r
e1 = [i for i in items.values() if i["mr"] == "E1"]


def has_id(it):
    return any(t in allterms for t in it["text"].lower().split())


res = {}
for s in S:
    tab = {True: [0, 0], False: [0, 0]}
    for it in e1:
        o, r = S[s][it["source_id"]], S[s][it["item_id"]]
        if o["category"] == "VALID_VERDICT" and o["verdict"] == "violating" and r["category"] in ("VALID_VERDICT", "ABSTENTION"):
            k = has_id(it)
            tab[k][1] += 1
            tab[k][0] += r["category"] == "VALID_VERDICT" and r["verdict"] == "violating"
    (a, n1), (b, n0) = tab[True], tab[False]
    t = [[a, n1 - a], [b, n0 - b]]
    ci = odds_ratio(t, kind="conditional").confidence_interval(0.95)
    res[s] = {"kept_with_identity": [a, n1], "kept_without_identity": [b, n0], "n": n1 + n0,
              "odds_ratio_sample": round(odds_ratio(t, kind="sample").statistic, 3),
              "or_ci95_exact_conditional": [round(ci.low, 3), round(ci.high, 3)],
              "fisher_p": fisher_exact(t)[1]}
# Holm over the 8 systems
order = sorted(res, key=lambda s: res[s]["fisher_p"])
m, running = len(order), 0.0
for i, s in enumerate(order):
    running = max(running, min(1.0, (m - i) * res[s]["fisher_p"]))
    res[s]["holm_p_posthoc_8"] = running

os.makedirs(out, exist_ok=True)
json.dump({"label": "POST HOC retention analysis (v25); population = ORIG violating and E1 answered; Holm over 8 systems", "by_system": res},
          open(os.path.join(out, "posthoc_e1_retention.json"), "w"), indent=1)
for s, v in res.items():
    a, n1 = v["kept_with_identity"]; b, n0 = v["kept_without_identity"]
    print(f"{s:22s} kept with id {a}/{n1}  without {b}/{n0}  n={v['n']}  OR {v['odds_ratio_sample']:.2f} "
          f"[{v['or_ci95_exact_conditional'][0]:.1f}, {v['or_ci95_exact_conditional'][1]:.1f}]  Holm p {v['holm_p_posthoc_8']:.3g}")
