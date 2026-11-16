#!/usr/bin/env python3
"""
analysis_repeats.py — run-to-run stability (reviewer R3). Read-only on all run files.

Repetition 1 = the original runs (runs/, results/e1_counterfactual/runs/). For Qwen2.5 direct, the first 822 items of
repetition 1 were run with a different setting; by default they are replaced by the uniform re-run in runs_uniform/,
so that every repetition uses the same setting ("rep1 uniform"). Use --rep1-as-reported to keep the original file.
Repetitions 2.. come from runs_repeat/rep<k>/{main,e1cf}/ (run_repeats.sh).

Reported per LLM condition (systems present in at least two repetitions):
  * label agreement over items: label = verdict if answered, else the response category;
    share identical in all repetitions, pairwise agreement with repetition 1, Fleiss' kappa across repetitions;
  * per repetition: coverage, abstention, refusal, generation errors, ORIG accuracy, flag rate per MR,
    E1 residual-identity odds ratio; then mean, SD, min and max across repetitions;
  * E1-CF per repetition: H1 (PLC - NEU) risk difference with Holm p as in the protocol, the decision label,
    and the post hoc valid-verdict-only H1 (both texts VALID_VERDICT; Holm over the four Qwen2.5/Gemma 2 conditions).

  python analysis_repeats.py          -> results/repeats/stability.{json,md}
"""
import argparse
import glob
import json
import os
import statistics as st
import subprocess
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analysis_systems import load_items, load_run, summary, MRS  # noqa: E402
from audit_metrics import paired, holm  # noqa: E402
from response_classifier import classify_record  # noqa: E402

LLM = ["qwen2.5_7b_direct", "qwen2.5_7b_evidence", "llama3.1_8b_direct", "llama3.1_8b_evidence", "gemma2_9b_direct", "gemma2_9b_evidence"]
DECIDING = ["qwen2.5:7b|direct", "qwen2.5:7b|evidence", "gemma2:9b|direct", "gemma2:9b|evidence"]
OUT = "results/repeats"


def label(x):
    return x["verdict"] if x["verdict"] is not None else x["category"]


def fleiss(rows):
    """rows: list of label lists (one per item, one label per repetition)."""
    n = len(rows[0]) if rows else 0
    if n < 2 or not rows:
        return None
    cats = sorted({c for r in rows for c in r})
    N = len(rows)
    p_j = {c: sum(r.count(c) for r in rows) / (N * n) for c in cats}
    P_i = [(sum(r.count(c) ** 2 for c in cats) - n) / (n * (n - 1)) for r in rows]
    Pbar, Pe = sum(P_i) / N, sum(v * v for v in p_j.values())
    return None if Pe == 1 else round((Pbar - Pe) / (1 - Pe), 4)


def spread(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return None
    return {"mean": round(st.mean(v), 4), "sd": round(st.stdev(v), 4) if len(v) > 1 else 0.0, "min": min(v), "max": max(v), "n_reps": len(v)}


def main_runs(rep1_as_reported):
    reps = {1: {}}
    for tag in LLM:
        reps[1][tag] = f"runs/{tag}.jsonl"
    for d in sorted(glob.glob("runs_repeat/rep*/main")):
        k = int(d.split("/")[1][3:])
        reps[k] = {os.path.basename(f)[:-6]: f for f in glob.glob(f"{d}/*.jsonl")}
    items, ident = load_items()
    data = {k: {} for k in reps}
    for k, files in reps.items():
        for tag, f in files.items():
            X = load_run(f, items)
            if k == 1 and tag == "qwen2.5_7b_direct" and not rep1_as_reported and os.path.exists("runs_uniform/qwen2.5_7b_direct_first822.jsonl"):
                X.update(load_run("runs_uniform/qwen2.5_7b_direct_first822.jsonl", items))
            if len(X) >= len(items):           # only complete runs enter the comparison
                data[k][tag] = X
    out = {}
    for tag in LLM:
        ks = [k for k in sorted(data) if tag in data[k]]
        if len(ks) < 2:
            continue
        ids = sorted(items)
        lab = [[label(data[k][tag][i]) for k in ks] for i in ids]
        sums = {k: summary(data[k][tag], items, ident) for k in ks}
        cat = {k: Counter(x["category"] for x in data[k][tag].values()) for k in ks}
        res = {"repetitions": ks,
               "identical_in_all": round(sum(len(set(r)) == 1 for r in lab) / len(lab), 4),
               "agreement_with_rep1": {k: round(sum(r[0] == r[j] for r in lab) / len(lab), 4) for j, k in enumerate(ks) if j},
               "fleiss_kappa": fleiss(lab),
               "per_rep": {k: {"coverage_valid": s["coverage_valid"], "abstention": s["abstention"], "refusal": s["refusal"],
                               "generation_errors": cat[k]["GENERATION_ERROR"], "ORIG_overall_accuracy": s.get("ORIG_overall_accuracy"),
                               "flag_rate_by_mr": {m: s["by_mr"][m]["flag_rate_all"] for m in MRS if m in s["by_mr"]},
                               "E1_OR": s.get("E1_residual_identity", {}).get("odds_ratio")} for k, s in sums.items()}}
        res["spread"] = {key: spread([res["per_rep"][k][key] for k in ks]) for key in ("coverage_valid", "abstention", "refusal", "ORIG_overall_accuracy", "E1_OR")}
        res["spread"]["flag_rate_by_mr"] = {m: spread([res["per_rep"][k]["flag_rate_by_mr"].get(m) for k in ks]) for m in MRS}
        out[tag] = res
    return out


def cf_runs(P):
    res = {}
    dirs = {1: "results/e1_counterfactual/runs"}
    for d in sorted(glob.glob("runs_repeat/rep*/e1cf")):
        dirs[int(d.split("/")[1][3:])] = d
    items = {json.loads(l)["item_id"]: json.loads(l) for l in open("results/e1_counterfactual/items_e1cf.jsonl")}
    for k, d in sorted(dirs.items()):
        files = [f"{d}/{t}.jsonl" for t in LLM]
        if not all(os.path.exists(f) and sum(1 for _ in open(f)) >= len(items) for f in files):
            res[k] = {"status": "incomplete"}
            continue
        od = f"{OUT}/e1cf_rep{k}"
        mr = f"runs_repeat/rep{k}/main" if k > 1 and glob.glob(f"runs_repeat/rep{k}/main/*.jsonl") else "runs"
        subprocess.run([P, "analyze_e1_counterfactual.py", "--runs-dir", d, "--out-dir", od, "--main-runs-dir", mr], check=True,
                       capture_output=True)
        a = json.load(open(f"{od}/analysis.json"))
        # post hoc: valid verdicts only (both PLC and NEU VALID_VERDICT)
        vo = {}
        for s in DECIDING:
            f = f"{d}/{s.split('|')[0].replace(':', '_')}_{s.split('|')[1]}.jsonl"
            S = {}
            for l in open(f):
                r = json.loads(l); it = items[r["item_id"]]; c = classify_record(r)
                S.setdefault(it["e1_item_id"], {})[it["cf_condition"]] = c
            pr = [(int(S[p]["PLC"]["verdict"] == "violating"), int(S[p]["NEU"]["verdict"] == "violating")) for p in S
                  if S[p]["PLC"]["category"] == "VALID_VERDICT" and S[p]["NEU"]["category"] == "VALID_VERDICT"]
            vo[s] = paired(pr)
        h = holm({s: v["mcnemar_exact_p"] for s, v in vo.items()})
        res[k] = {"status": "complete", "decision": a["decision"]["verdict"],
                  "H1": {s: {"rd": a["systems"][s]["H1_PLC_minus_NEU"]["risk_difference"], "holm_p": a["systems"][s]["H1_PLC_minus_NEU"].get("holm_p_F_CF")}
                         for s in a["systems"] if "|" in s and a["systems"][s].get("status") == "complete"},
                  "H1_valid_only": {s: {"n_pairs": v["n_pairs"], "rd": v["risk_difference"], "holm_p_over_4": h[s]} for s, v in vo.items()}}
    return res


def md(main, cf):
    L = ["# Run-to-run stability (analysis_repeats.py)\n",
         "Repetition 1 = original runs (Qwen2.5 direct: first 822 items from the uniform re-run unless --rep1-as-reported).\n",
         "## Main runs: agreement of the label (verdict, or response category when not answered)\n",
         "| Condition | Reps | Identical in all | Agreement with rep 1 | Fleiss κ | Coverage mean [min–max] | ORIG acc. mean [min–max] | E1 OR [min–max] |",
         "|---|---|---|---|---|---|---|---|"]
    f = lambda s: "–" if not s else f"{100 * s['mean']:.1f} [{100 * s['min']:.1f}–{100 * s['max']:.1f}]"
    fe = lambda e: "–" if not e else "%.2f [%.2f–%.2f]" % (e["mean"], e["min"], e["max"])
    for tag, r in main.items():
        e = r["spread"]["E1_OR"]
        L.append(f"| {tag} | {','.join(map(str, r['repetitions']))} | {100 * r['identical_in_all']:.1f}% | "
                 f"{', '.join(f'rep{k}: {100 * v:.1f}%' for k, v in r['agreement_with_rep1'].items())} | {r['fleiss_kappa']} | "
                 f"{f(r['spread']['coverage_valid'])} | {f(r['spread']['ORIG_overall_accuracy'])} | "
                 f"{fe(e)} |")
    L += ["\n## E1-CF per repetition\n", "| Rep | Decision | H1 RD (Holm p) per deciding condition | Valid-only H1 RD (Holm p over 4) |", "|---|---|---|---|"]
    for k, r in cf.items():
        if r["status"] != "complete":
            L.append(f"| {k} | incomplete | | |"); continue
        h1 = "; ".join(f"{s}: {100 * r['H1'][s]['rd']:+.1f} ({r['H1'][s]['holm_p']:.3g})" for s in DECIDING if s in r["H1"])
        vo = "; ".join(f"{s}: {100 * v['rd']:+.1f} ({v['holm_p_over_4']:.3g}, n={v['n_pairs']})" for s, v in r["H1_valid_only"].items())
        L.append(f"| {k} | {r['decision']} | {h1} | {vo} |")
    return "\n".join(L) + "\n"


def run():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rep1-as-reported", action="store_true")
    a = ap.parse_args()
    m = main_runs(a.rep1_as_reported)
    c = cf_runs(sys.executable)
    os.makedirs(OUT, exist_ok=True)
    json.dump({"main": m, "e1cf": c}, open(f"{OUT}/stability.json", "w"), indent=1)
    text = md(m, c)
    open(f"{OUT}/stability.md", "w").write(text)
    print(text)
    print("written:", OUT)


if __name__ == "__main__":
    run()
