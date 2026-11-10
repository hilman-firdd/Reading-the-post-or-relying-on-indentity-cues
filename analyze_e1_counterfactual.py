#!/usr/bin/env python3
"""
Analysis of the E1 identity-term counterfactual, exactly as fixed in results/e1_counterfactual/PROTOCOL.md.

  python analyze_e1_counterfactual.py   -> results/e1_counterfactual/analysis.json, summary.csv
Reads results/e1_counterfactual/{items_e1cf.jsonl, runs/*.jsonl}, runs/ (main E1 run, for the stability check S3),
and the human validation sheet (S4). Writes nothing else.
"""
import csv, json, os, sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from response_classifier import classify_record, ANSWERED  # noqa: E402
from audit_metrics import paired, holm, wilson, rate, load_validation  # noqa: E402

D = "results/e1_counterfactual"
LLM = [("qwen2.5:7b", "direct"), ("qwen2.5:7b", "evidence"), ("llama3.1:8b", "direct"), ("llama3.1:8b", "evidence"),
       ("gemma2:9b", "direct"), ("gemma2:9b", "evidence")]
CONDS = ("REPLAY", "NEU", "PLC", "DEL", "PLCDEL")
DECISION_SYSTEMS = ("qwen2.5:7b|direct", "qwen2.5:7b|evidence", "gemma2:9b|direct", "gemma2:9b|evidence")

def load_system(path, items):
    """-> {e1_item_id: {cond: (answered, flagged, category)}}"""
    out = defaultdict(dict)
    for l in open(path):
        r = json.loads(l); it = items[r["item_id"]]; c = classify_record(r)
        out[it["e1_item_id"]][it["cf_condition"]] = (c["category"] in ANSWERED, c["category"] == "VALID_VERDICT" and c["verdict"] == "violating", c["category"])
    return out

def contrast(S, a, b, keep=lambda p: True):
    """x = flag under condition a, y = flag under condition b, on posts where both are answered."""
    pr = [(int(S[p][a][1]), int(S[p][b][1])) for p in S if keep(p) and a in S[p] and b in S[p] and S[p][a][0] and S[p][b][0]]
    return paired(pr)

def main():
    items = {}
    for l in open(f"{D}/items_e1cf.jsonl"):
        it = json.loads(l); items[it["item_id"]] = it
    all_items = {json.loads(l)["item_id"]: json.loads(l) for l in open("items_llm600.jsonl")}
    val = load_validation(all_items)
    n_posts = len({it["e1_item_id"] for it in items.values()})
    systems = {f"{m}|{p}": f"{D}/runs/{m.replace(':', '_')}_{p}.jsonl" for m, p in LLM}
    systems.update({"word-LR": f"{D}/runs/cf_word-LR.jsonl", "char-LR": f"{D}/runs/cf_char-LR.jsonl"})
    main_runs = {f"{m}|{p}": f"runs/{m.replace(':', '_')}_{p}.jsonl" for m, p in LLM}
    main_runs.update({"word-LR": "runs/llm600_word-LR.jsonl", "char-LR": "runs/llm600_char-LR.jsonl"})

    res = {"protocol": f"{D}/PROTOCOL.md", "n_posts": n_posts, "systems": {}}
    for s, path in systems.items():
        n_lines = sum(1 for _ in open(path)) if os.path.exists(path) else 0
        if n_lines < len(items): res["systems"][s] = {"status": f"incomplete ({n_lines}/{len(items)} responses)"}; continue
        S = load_system(path, items)
        cov = {c: {"answered": sum(S[p][c][0] for p in S), "flag_rate_among_answered": rate(sum(S[p][c][1] for p in S if S[p][c][0]), sum(S[p][c][0] for p in S)),
                   "categories": dict(Counter(S[p][c][2] for p in S))} for c in CONDS}
        main = {}
        for l in open(main_runs[s]):
            r = json.loads(l); main[r["item_id"]] = classify_record(r)
        rep = [(S[p]["REPLAY"], main[p]) for p in S if S[p]["REPLAY"][0] and main[p]["category"] in ANSWERED]
        stab = {"pairs_answered": len(rep),
                "flag_agreement": rate(sum(a[1] == (b["category"] == "VALID_VERDICT" and b["verdict"] == "violating") for a, b in rep), len(rep))}
        invalid = lambda p: val.get(p, {}).get("status") == "invalid"
        res["systems"][s] = {"status": "complete", "coverage_by_condition": cov,
                             "H1_PLC_minus_NEU": contrast(S, "PLC", "NEU"),
                             "S1_PLCDEL_minus_DEL": contrast(S, "PLCDEL", "DEL"),
                             "S2_REPLAY_minus_NEU": contrast(S, "REPLAY", "NEU"), "S2_REPLAY_minus_PLC": contrast(S, "REPLAY", "PLC"),
                             "S2_REPLAY_minus_DEL": contrast(S, "REPLAY", "DEL"),
                             "S3_stability_REPLAY_vs_main_run": stab,
                             "S4_H1_excluding_human_invalid": contrast(S, "PLC", "NEU", keep=lambda p: not invalid(p)),
                             "n_posts_human_validated": sum(1 for p in S if val.get(p, {}).get("status") in ("valid", "invalid")),
                             "n_posts_human_invalid": sum(1 for p in S if invalid(p))}
    done = [s for s, _ in [(f"{m}|{p}", 0) for m, p in LLM] if res["systems"].get(s, {}).get("status") == "complete"]
    for key, fam in (("H1_PLC_minus_NEU", "F_CF"), ("S1_PLCDEL_minus_DEL", "F_CF2"), ("S4_H1_excluding_human_invalid", "F_CF_S4")):
        h = holm({s: res["systems"][s][key]["mcnemar_exact_p"] for s in done})
        for s in done: res["systems"][s][key][f"holm_p_{fam}"] = h[s]

    # ---- decision rule (PROTOCOL.md §6), evaluated only when all four deciding systems are complete
    if all(s in done for s in DECISION_SYSTEMS):
        sig = [s for s in DECISION_SYSTEMS if (res["systems"][s]["H1_PLC_minus_NEU"]["risk_difference"] or 0) > 0
               and res["systems"][s]["H1_PLC_minus_NEU"]["holm_p_F_CF"] is not None and res["systems"][s]["H1_PLC_minus_NEU"]["holm_p_F_CF"] < 0.05]
        same_sign = [s for s in sig if (res["systems"][s]["S1_PLCDEL_minus_DEL"]["risk_difference"] or 0) > 0]
        pos = [s for s in DECISION_SYSTEMS if (res["systems"][s]["H1_PLC_minus_NEU"]["risk_difference"] or 0) > 0]
        if len(same_sign) >= 2: verdict = "SUPPORT: causal role of residual identity terms (protocol §6)"
        elif len(pos) >= 3: verdict = "PARTIAL: directional counterfactual evidence; claim stays associational"
        else: verdict = "NOT SUPPORTED: claim stays associational; counterfactual does not support it"
        res["decision"] = {"rule": "H1 Holm-significant with RD>0 in >=2 of 4 qwen/gemma conditions and S1 same sign",
                           "holm_significant_positive": sig, "with_S1_same_sign": same_sign, "rd_positive": pos, "verdict": verdict}
    else:
        res["decision"] = {"verdict": "not evaluated: deciding systems incomplete"}
    json.dump(res, open(f"{D}/analysis.json", "w"), indent=1)

    rows = []
    for s, v in res["systems"].items():
        if v.get("status") != "complete": rows.append({"system": s, "status": v["status"]}); continue
        for key in ("H1_PLC_minus_NEU", "S1_PLCDEL_minus_DEL", "S2_REPLAY_minus_NEU", "S2_REPLAY_minus_PLC", "S4_H1_excluding_human_invalid"):
            c = v[key]
            rows.append({"system": s, "status": "complete", "contrast": key, "n_pairs": c["n_pairs"], "flag_rate_x": c["rate_x"], "flag_rate_y": c["rate_y"],
                         "risk_difference": c["risk_difference"], "rd_ci95": json.dumps(c["rd_ci95_post_bootstrap"]), "b": c["b_only_x"], "c": c["c_only_y"],
                         "mcnemar_p": c["mcnemar_exact_p"], "holm_p": next((c[k] for k in c if k.startswith("holm_p")), "")})
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(f"{D}/summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(res["decision"]["verdict"])

if __name__ == "__main__":
    main()
