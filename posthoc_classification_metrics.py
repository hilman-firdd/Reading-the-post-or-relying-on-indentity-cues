"""Post hoc: precision, recall, F1 and balanced accuracy of the verdict on the 600 ORIG posts.
Run from the repository root:  python3 posthoc_classification_metrics.py [out.json]
Positive class = violating (gold hate speech or offensive). A non-answer (abstention, refusal, unparseable) counts as
not violating, the same convention as the overall accuracy in audited_metrics.csv. Reads only items_llm600.jsonl and runs/."""
import json, sys
sys.path.insert(0, ".")
import audit_metrics as A

items, run_items, orig, systems, records, by = A.load()
out = {}
for s in systems:
    name = s["system"]; tp = fp = fn = tn = 0
    for post, it in orig.items():
        pos = it["accept"] == ["violating"]; pred = by[name][it["item_id"]]["verdict"] == "violating"
        tp += pos and pred; fn += pos and not pred; fp += (not pos) and pred; tn += (not pos) and not pred
    prec = tp / (tp + fp) if tp + fp else 0.0; rec = tp / (tp + fn); spec = tn / (tn + fp)
    f1p = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    prec_n = tn / (tn + fn) if tn + fn else 0.0; f1n = 2 * prec_n * spec / (prec_n + spec) if prec_n + spec else 0.0
    out[name] = dict(n=tp + fp + fn + tn, tp=tp, fp=fp, fn=fn, tn=tn, precision=round(prec, 3), recall=round(rec, 3),
                     specificity=round(spec, 3), f1_violating=round(f1p, 3), macro_f1=round((f1p + f1n) / 2, 3),
                     balanced_accuracy=round((rec + spec) / 2, 3))
    print(f"{name:24s} n={tp+fp+fn+tn} P={prec:.3f} R={rec:.3f} spec={spec:.3f} F1+={f1p:.3f} macroF1={(f1p+f1n)/2:.3f} bal.acc={(rec+spec)/2:.3f}")
if len(sys.argv) > 1: json.dump(out, open(sys.argv[1], "w"), indent=1)
