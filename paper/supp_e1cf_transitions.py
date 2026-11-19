"""Supplementary Table S1 (v29, audit #12): PLC -> NEU response transitions in E1-CF, per LLM condition.

For each of the 88 posts, the response to the placebo text (PLC) and to the identity-replaced text (NEU) is put in one of
four categories: flag (valid verdict 'violating'), not violating (valid verdict 'not_violating'), insufficient (abstention),
refusal / other (refusal, unparseable, error, empty). The H1 contrast of Table 6 uses only posts where both texts are answered
(flag, not violating, or insufficient); b = flag -> not flagged, c = not flagged -> flag. The script asserts that b, c and
n reproduce results/e1_counterfactual/analysis.json, so the matrix and Table 6 come from the same responses.

Usage: python3 paper/supp_e1cf_transitions.py <repo> <out_dir>
  writes <repo>/results/e1cf_transitions.json and <out_dir>/tab_s1_body.tex
"""
import json, os, sys
from collections import Counter, defaultdict

repo, out = sys.argv[1], sys.argv[2]
os.chdir(repo)
sys.dont_write_bytecode = True
sys.path.insert(0, repo)
from response_classifier import classify_record  # noqa: E402

CATS = ["flag", "not violating", "insufficient", "refusal/other"]
SYS = [("qwen2.5:7b|direct", "qwen2.5_7b_direct", "Qwen2.5 / direct"), ("qwen2.5:7b|evidence", "qwen2.5_7b_evidence", "Qwen2.5 / evidence"),
       ("gemma2:9b|direct", "gemma2_9b_direct", "Gemma 2 / direct"), ("gemma2:9b|evidence", "gemma2_9b_evidence", "Gemma 2 / evidence"),
       ("llama3.1:8b|direct", "llama3.1_8b_direct", "Llama 3.1 / direct"), ("llama3.1:8b|evidence", "llama3.1_8b_evidence", "Llama 3.1 / evidence")]


def cat(c):
    if c["category"] == "VALID_VERDICT":
        return "flag" if c["verdict"] == "violating" else "not violating"
    if c["category"] == "ABSTENTION":
        return "insufficient"
    return "refusal/other"


items = {json.loads(l)["item_id"]: json.loads(l) for l in open("results/e1_counterfactual/items_e1cf.jsonl")}
an = json.load(open("results/e1_counterfactual/analysis.json"))["systems"]
res, rows = {}, []
for key, fn, lab in SYS:
    R = defaultdict(dict)
    for line in open(f"results/e1_counterfactual/runs/{fn}.jsonl"):
        r = json.loads(line); it = items[r["item_id"]]
        R[it["e1_item_id"]][it["cf_condition"]] = cat(classify_record(r))
    assert len(R) == 88, (key, len(R))
    M = Counter((R[p]["PLC"], R[p]["NEU"]) for p in R)
    answered = [p for p in R if R[p]["PLC"] != "refusal/other" and R[p]["NEU"] != "refusal/other"]
    b = sum(R[p]["PLC"] == "flag" and R[p]["NEU"] != "flag" for p in answered)
    c = sum(R[p]["PLC"] != "flag" and R[p]["NEU"] == "flag" for p in answered)
    h = an[key]["H1_PLC_minus_NEU"]
    assert (len(answered), b, c) == (h["n_pairs"], h["b_only_x"], h["c_only_y"]), (key, len(answered), b, c)
    res[key] = {"matrix_PLC_to_NEU": {f"{a}->{z}": M.get((a, z), 0) for a in CATS for z in CATS},
                "n_pairs_answered": len(answered), "b_flag_lost": b, "c_flag_gained": c,
                "flag_lost_to_not_violating": sum(R[p]["PLC"] == "flag" and R[p]["NEU"] == "not violating" for p in answered),
                "flag_lost_to_insufficient": sum(R[p]["PLC"] == "flag" and R[p]["NEU"] == "insufficient" for p in answered)}
    # v30b (audit #15): net decomposition of b - c and the size of the valid-verdicts-only subset of Section 4.4
    m = res[key]["matrix_PLC_to_NEU"]
    res[key]["net_via_insufficient"] = m["flag->insufficient"] - m["insufficient->flag"]
    res[key]["net_via_not_violating"] = m["flag->not violating"] - m["not violating->flag"]
    res[key]["valid_only_pairs"] = sum(m[f"{x}->{y}"] for x in ("flag", "not violating") for y in ("flag", "not violating"))
    assert res[key]["net_via_insufficient"] + res[key]["net_via_not_violating"] == b - c, key
    # LaTeX rows: one block per condition, PLC category in rows, NEU category in columns
    for i, a in enumerate(CATS):
        cells = " & ".join(str(M.get((a, z), 0)) for z in CATS)
        tot = sum(M.get((a, z), 0) for z in CATS)
        rows.append(f"{lab if i == 0 else ''} & {a} & {cells} & {tot} \\\\")
    rows.append(f" & \\multicolumn{{6}}{{p{{12.8cm}}}}{{\\emph{{pairs in H1: {len(answered)}; flag lost $b$ = {b} (to not violating {res[key]['flag_lost_to_not_violating']}, to insufficient {res[key]['flag_lost_to_insufficient']}); flag gained $c$ = {c}; net $b-c$ = {b - c} (via insufficient {res[key]['net_via_insufficient']}, via not violating {res[key]['net_via_not_violating']}); both valid: {res[key]['valid_only_pairs']}}}}} \\\\")
    rows.append("\\midrule")
rows = rows[:-1]
vo = json.load(open("results/e1_counterfactual/posthoc_valid_only.json"))   # cross-check with the valid-verdicts-only analysis
for k in vo:
    assert res[k]["valid_only_pairs"] == vo[k]["valid_only"]["n_pairs"], k
json.dump({"label": "PLC -> NEU response transitions (rows PLC, columns NEU); b/c and n match analysis.json", "by_system": res},
          open("results/e1cf_transitions.json", "w"), indent=1)
os.makedirs(out, exist_ok=True)
open(os.path.join(out, "tab_s1_body.tex"), "w").write("\n".join(rows) + "\n")
for key, v in res.items():
    print(key, "n", v["n_pairs_answered"], "b", v["b_flag_lost"], "c", v["c_flag_gained"], "lost->ins", v["flag_lost_to_insufficient"])
