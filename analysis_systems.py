#!/usr/bin/env python3
"""
analysis_systems.py — summaries for runs that are not part of the main audit (read-only on all run files).

  python analysis_systems.py ablation   -> results/ablation/summary.{json,md}
  python analysis_systems.py extra      -> results/extra_models/summary.{json,md}

Shared per-system summary (same response classifier and accept sets as audit_metrics.py):
  coverage (valid verdicts / all), abstention, refusal, other non-answers, flag rate (violating / all items),
  strict pass among answered per MR, ORIG overall accuracy (non-answers wrong), and the E1 residual-identity
  odds ratio on answered items.

ablation: per model, the chain direct -> abl_quote_first (+A) -> abl_quote_only (+A+B) -> evidence (+A+B+C).
  direct and evidence are taken from the newest repetition in runs_repeat/ if one is complete (same session setting
  as the ablation), otherwise from runs/. Adjacent steps are compared with exact McNemar tests, paired by post, on
  (1) ORIG correct, (2) E1 still flagged, (3) R1 abstained; Holm within each metric over all adjacent steps.
  Run-to-run variation (analysis_repeats.py) is the noise floor: a step difference smaller than the variation between
  repetitions of the same prompt should not be attributed to the prompt part.
extra: every runs_extra/main/<model>_<prompt>.jsonl, plus ORIG accuracy vs word-LR (exact McNemar, Holm).
"""
import glob
import importlib.util
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from response_classifier import classify_record, ANSWERED  # noqa: E402
from audit_metrics import paired, holm, rate, wilson, toks  # noqa: E402
from scipy.stats import fisher_exact  # noqa: E402

V, INS = "violating", "insufficient"
MRS = ["ORIG", "E1", "E2", "R1", "R2", "R3", "I1", "I2", "I3"]


def load_items():
    items = {}
    for l in open("items_llm600.jsonl"):
        it = json.loads(l)
        if it.get("text"):
            items[it["item_id"]] = it
    spec = importlib.util.spec_from_file_location("bi", "build_items.py")
    bi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bi)
    ident = set().union(*bi.GROUP_TERMS.values())
    return items, ident


def load_run(path, items):
    out = {}
    for l in open(path):
        r = json.loads(l)
        if r["item_id"] not in items:
            continue
        c = classify_record(r)
        out[r["item_id"]] = {"category": c["category"], "verdict": c["verdict"] if c["category"] in ANSWERED else None}
    return out


def summary(X, items, ident):
    res = {"n_items": len(X)}
    cat = Counter(x["category"] for x in X.values())
    n = len(X)
    res["coverage_valid"] = rate(cat["VALID_VERDICT"], n)
    res["abstention"] = rate(cat["ABSTENTION"], n)
    res["refusal"] = rate(cat["REFUSAL"], n)
    res["other_nonanswer"] = rate(n - cat["VALID_VERDICT"] - cat["ABSTENTION"] - cat["REFUSAL"], n)
    res["flag_rate_all"] = rate(sum(x["verdict"] == V for x in X.values()), n)
    per = {}
    for m in MRS:
        ids = [i for i in X if items[i]["mr"] == m]
        if not ids:
            continue
        ans = [i for i in ids if X[i]["category"] in ANSWERED]
        k = sum(X[i]["verdict"] in items[i]["accept"] for i in ans)
        per[m] = {"n": len(ids), "answered": len(ans), "pass_among_answered": rate(k, len(ans)),
                  "flag_rate_all": rate(sum(X[i]["verdict"] == V for i in ids), len(ids)),
                  "abstention_among_answered": rate(sum(X[i]["verdict"] == INS for i in ans), len(ans))}
    res["by_mr"] = per
    orig = [i for i in X if items[i]["mr"] == "ORIG"]
    if orig:
        k = sum(X[i]["category"] in ANSWERED and X[i]["verdict"] in items[i]["accept"] for i in orig)
        res["ORIG_overall_accuracy"] = rate(k, len(orig))
        res["ORIG_overall_accuracy_ci95"] = wilson(k, len(orig))
    e1 = [i for i in X if items[i]["mr"] == "E1" and X[i]["category"] in ANSWERED]
    if e1:
        a = [i for i in e1 if any(t in ident for t in toks(items[i]["text"]))]
        b = [i for i in e1 if i not in set(a)]
        fa, fb = sum(X[i]["verdict"] == V for i in a), sum(X[i]["verdict"] == V for i in b)
        orr, p = fisher_exact([[fa, len(a) - fa], [fb, len(b) - fb]])
        res["E1_residual_identity"] = {"flagged_with_identity": [fa, len(a)], "flagged_without": [fb, len(b)],
                                       "odds_ratio": None if orr == float("inf") else round(float(orr), 2), "fisher_p": float(f"{p:.3g}")}
    return res


def pairs_on(Xa, Xb, items, mr, fn):
    """(x, y) per post on items of one MR present in both runs; fn(item, record) -> 0/1 or None (excluded)."""
    out = []
    for i in Xa:
        if items[i]["mr"] != mr or i not in Xb:
            continue
        x, y = fn(items[i], Xa[i]), fn(items[i], Xb[i])
        if x is not None and y is not None:
            out.append((x, y))
    return out


METRICS = {
    "ORIG_correct": ("ORIG", lambda it, r: int(r["category"] in ANSWERED and r["verdict"] in it["accept"])),
    "E1_flagged": ("E1", lambda it, r: int(r["verdict"] == V) if r["category"] in ANSWERED else None),
    "R1_abstained": ("R1", lambda it, r: int(r["verdict"] == INS) if r["category"] in ANSWERED else None),
}


def newest_complete_rep(fname):
    reps = sorted(glob.glob("runs_repeat/rep*/main/" + fname), key=lambda p: int(p.split("/")[1][3:]), reverse=True)
    for p in reps:
        if sum(1 for _ in open(p)) >= 4233:
            return p
    return None


def fmt(v):
    """percent for rates (0-1)."""
    return "–" if v is None else (f"{100 * v:.1f}" if isinstance(v, float) else str(v))


def fmt_or(v):
    return "–" if v is None else f"{v:.2f}"


def ablation():
    items, ident = load_items()
    out = {"chain": ["direct", "abl_quote_first", "abl_quote_only", "evidence"], "models": {}}
    tests = {k: {} for k in METRICS}
    for f in sorted(glob.glob("runs_ablation/*_abl_quote_first.jsonl")):
        tag = os.path.basename(f)[: -len("_abl_quote_first.jsonl")]
        src = {}
        for p in ("direct", "evidence"):
            rep = newest_complete_rep(f"{tag}_{p}.jsonl")
            src[p] = rep or f"runs/{tag}_{p}.jsonl"
        src["abl_quote_first"] = f
        src["abl_quote_only"] = f"runs_ablation/{tag}_abl_quote_only.jsonl"
        if not os.path.exists(src["abl_quote_only"]):
            continue
        X = {p: load_run(src[p], items) for p in out["chain"]}
        common = set.intersection(*(set(x) for x in X.values()))   # same items for every step (MRS subset allowed)
        X = {p: {i: x[i] for i in common} for p, x in X.items()}
        out["models"][tag] = {"sources": src, "n_common_items": len(common), "summary": {p: summary(X[p], items, ident) for p in out["chain"]}}
        for a, b in zip(out["chain"], out["chain"][1:]):
            for k, (mr, fn) in METRICS.items():
                pr = pairs_on(X[b], X[a], items, mr, fn)   # x = later step, y = earlier step
                if len(pr) >= 1:
                    tests[k][f"{tag}: {a} -> {b}"] = paired(pr)
    for k, t in tests.items():
        h = holm({s: v["mcnemar_exact_p"] for s, v in t.items()})
        for s in t:
            t[s]["holm_p"] = h[s]
    out["adjacent_step_tests"] = tests
    write("results/ablation", out, md_ablation(out))


def md_ablation(out):
    L = ["# Prompt ablation (analysis_systems.py ablation)\n",
         "Chain: direct → +A quote first → +B decide only from quotes → +C insufficient when quotes do not settle the case (= evidence).\n"]
    for tag, d in out["models"].items():
        L += [f"## {tag} ({d['n_common_items']} items in every step)\n",
              "| Prompt | Coverage | Abstention | Refusal | ORIG acc. | E1 flag (all) | R1 abst. (answered) | E1 OR |", "|---|---|---|---|---|---|---|---|"]
        for p, s in d["summary"].items():
            L.append(f"| {p} | {fmt(s['coverage_valid'])} | {fmt(s['abstention'])} | {fmt(s['refusal'])} | {fmt(s.get('ORIG_overall_accuracy'))} | "
                     f"{fmt(s['by_mr'].get('E1', {}).get('flag_rate_all'))} | {fmt(s['by_mr'].get('R1', {}).get('abstention_among_answered'))} | "
                     f"{fmt_or(s.get('E1_residual_identity', {}).get('odds_ratio'))} |")
        L.append("")
    L += ["## Adjacent steps (exact McNemar, paired by post; RD = later − earlier step, in points; Holm per metric)\n",
          "| Metric | Step | n | RD [95% CI] | Holm p |", "|---|---|---|---|---|"]
    for k, t in out["adjacent_step_tests"].items():
        for s, v in t.items():
            ci = v["rd_ci95_post_bootstrap"]
            L.append(f"| {k} | {s} | {v['n_pairs']} | {100 * v['risk_difference']:+.1f} [{100 * ci[0]:+.1f}, {100 * ci[1]:+.1f}] | {v['holm_p']:.3g} |")
    L.append("\nCompare every step difference with the run-to-run variation in results/repeats/stability.md before attributing it to the prompt part.")
    return "\n".join(L) + "\n"


def extra():
    items, ident = load_items()
    word = load_run("runs/llm600_word-LR.jsonl", items)
    out = {"systems": {}, "vs_wordLR_ORIG": {}}
    for f in sorted(glob.glob("runs_extra/main/*.jsonl")):
        tag = os.path.basename(f)[:-6]
        X = load_run(f, items)
        out["systems"][tag] = {"file": f, "complete": len(X) >= len(items), "summary": summary(X, items, ident)}
        pr = pairs_on(X, word, items, "ORIG", METRICS["ORIG_correct"][1])
        if pr:
            out["vs_wordLR_ORIG"][tag] = paired(pr)
    h = holm({s: v["mcnemar_exact_p"] for s, v in out["vs_wordLR_ORIG"].items()})
    for s in out["vs_wordLR_ORIG"]:
        out["vs_wordLR_ORIG"][s]["holm_p"] = h[s]
    L = ["# Added models (analysis_systems.py extra)\n", "| System | Items | Coverage | Abstention | Refusal | ORIG acc. | vs word-LR RD [CI], Holm p | E1 OR |",
         "|---|---|---|---|---|---|---|---|"]
    for tag, d in out["systems"].items():
        s = d["summary"]; v = out["vs_wordLR_ORIG"].get(tag)
        vs = f"{100 * v['risk_difference']:+.1f} [{100 * v['rd_ci95_post_bootstrap'][0]:+.1f}, {100 * v['rd_ci95_post_bootstrap'][1]:+.1f}], {v['holm_p']:.3g}" if v else "–"
        L.append(f"| {tag} | {s['n_items']}{'' if d['complete'] else ' (incomplete)'} | {fmt(s['coverage_valid'])} | {fmt(s['abstention'])} | "
                 f"{fmt(s['refusal'])} | {fmt(s.get('ORIG_overall_accuracy'))} | {vs} | {fmt_or(s.get('E1_residual_identity', {}).get('odds_ratio'))} |")
    write("results/extra_models", out, "\n".join(L) + "\n")


def write(d, obj, md):
    os.makedirs(d, exist_ok=True)
    json.dump(obj, open(f"{d}/summary.json", "w"), indent=1)
    open(f"{d}/summary.md", "w").write(md)
    print(md)
    print("written:", d)


if __name__ == "__main__":
    {"ablation": ablation, "extra": extra}[sys.argv[1] if len(sys.argv) > 1 else "ablation"]()
