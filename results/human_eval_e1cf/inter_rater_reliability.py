#!/usr/bin/env python3
"""
Validation and inter-rater reliability for the E1-counterfactual human evaluation.

  python inter_rater_reliability.py --phase 1 --rater1 R1.csv --rater2 R2.csv [--out-dir DIR]

* Validates both annotation files strictly (schema, ids, unchanged text, allowed values, verbatim spans, required fields).
  Any error => the report lists the errors and NO statistics are computed (exit code 2). Nothing is repaired or imputed.
* Computes, on the 3 categories POLICY_VIOLATING / NOT_POLICY_VIOLATING / AMBIGUOUS:
    raw agreement, Cohen's kappa (+ post-bootstrap CI), Krippendorff's alpha (nominal), Gwet's AC1 (+ CI),
    prevalence per rater, confusion matrix, per-category agreement, and the binary collapse (violating vs not violating).
  Kappa and alpha can be low or unstable when one category dominates (the "kappa paradox"); AC1 and the per-category
  agreement are reported next to them for that reason. No verbal label (e.g. "strong") is attached to any number.
* Writes the list of disagreements as an adjudication template. NOTHING is resolved here: no rater is preferred.

Importable: read_annotations(), reliability(), final_labels() are used by human_evaluation_analysis.py.
"""
import argparse, csv, hashlib, json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DECISIONS = ("POLICY_VIOLATING", "NOT_POLICY_VIOLATING", "AMBIGUOUS")
CLAUSES = ("(a)", "(b)", "(a)+(b)", "none", "unclear")
REQUIRED_COLS = ["blind_id", "text", "rater_id", "decision", "supporting_span", "policy_clause", "justification", "uncertainty_note"]
SPAN_SEP = " ||| "
ADJ_COLS = ["blind_id", "text", "rater1_decision", "rater1_clause", "rater1_span", "rater1_justification", "rater1_uncertainty",
            "rater2_decision", "rater2_clause", "rater2_span", "rater2_justification", "rater2_uncertainty",
            "adjudicator_id", "adjudication_process", "final_decision", "final_clause", "final_span", "final_justification"]
ADJ_PROCESSES = ("third_reviewer", "consensus_discussion")

# ------------------------------------------------------------------ key and validation
def load_key(path=None, phase=None):
    path = path or os.path.join(HERE, "private", "annotation_key.csv")
    rows = list(csv.DictReader(open(path, newline="")))
    return {r["blind_id"]: r for r in rows if phase is None or int(r["phase"]) == int(phase)}

def read_annotations(path, key, expect_one_rater_label=True):
    """-> (rows dict blind_id -> row, errors list). `key` = load_key(phase=...)"""
    errors = []; rows = {}
    try: raw = list(csv.DictReader(open(path, newline="", encoding="utf-8-sig")))
    except Exception as e: return {}, [f"cannot read file: {e}"]
    if not raw: return {}, ["file has no rows"]
    missing = [c for c in REQUIRED_COLS if c not in raw[0]]
    if missing: return {}, [f"missing columns: {missing}"]
    seen = set(); labels = set()
    for n, r in enumerate(raw, start=2):
        bid = (r["blind_id"] or "").strip(); where = f"line {n} ({bid or 'no id'})"
        if bid in seen: errors.append(f"{where}: duplicate blind_id"); continue
        seen.add(bid)
        if bid not in key: errors.append(f"{where}: unknown blind_id"); continue
        if hashlib.sha1(r["text"].encode()).hexdigest() != key[bid]["text_sha1"]: errors.append(f"{where}: text was modified")
        rid = (r["rater_id"] or "").strip(); labels.add(rid)
        if not rid: errors.append(f"{where}: rater_id empty")
        dec = (r["decision"] or "").strip(); clause = (r["policy_clause"] or "").strip(); just = (r["justification"] or "").strip()
        span = r["supporting_span"] or ""; unc = (r["uncertainty_note"] or "").strip()
        if dec not in DECISIONS: errors.append(f"{where}: decision '{dec}' is not one of {DECISIONS}"); continue
        if clause not in CLAUSES: errors.append(f"{where}: policy_clause '{clause}' is not one of {CLAUSES}")
        if not just: errors.append(f"{where}: justification empty")
        spans = [s for s in span.split(SPAN_SEP) if s.strip()] if span.strip() else []
        for s in spans:
            if s not in r["text"]: errors.append(f"{where}: span not found verbatim in text: '{s[:40]}'")
        if dec == "POLICY_VIOLATING":
            if not spans: errors.append(f"{where}: POLICY_VIOLATING needs a supporting_span")
            if clause not in ("(a)", "(b)", "(a)+(b)"): errors.append(f"{where}: POLICY_VIOLATING needs clause (a), (b) or (a)+(b)")
        elif dec == "NOT_POLICY_VIOLATING":
            if clause != "none": errors.append(f"{where}: NOT_POLICY_VIOLATING needs clause 'none'")
        elif not unc: errors.append(f"{where}: AMBIGUOUS needs an uncertainty_note")
        rows[bid] = {"decision": dec, "clause": clause, "span": span, "justification": just, "uncertainty": unc, "text": r["text"], "rater_id": rid}
    absent = sorted(set(key) - seen)
    if absent: errors.append(f"{len(absent)} items missing from the file, e.g. {absent[:3]}")
    if expect_one_rater_label and len(labels - {""}) > 1: errors.append(f"more than one rater_id in one file: {sorted(labels)}")
    return rows, errors

# ------------------------------------------------------------------ statistics
def cohen_kappa(a, b, cats=DECISIONS):
    n = len(a)
    if not n: return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return None if pe == 1 else (po - pe) / (1 - pe)

def gwet_ac1(a, b, cats=DECISIONS):
    n = len(a); q = len(cats)
    if not n: return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pi = [((a.count(c) + b.count(c)) / (2 * n)) for c in cats]
    pe = sum(p * (1 - p) for p in pi) / (q - 1)
    return None if pe == 1 else (po - pe) / (1 - pe)

def krippendorff_alpha_nominal(a, b):
    """Two coders, no missing values. alpha = 1 - (N-1) * sum_{c!=k} o_ck / sum_{c!=k} n_c n_k."""
    cats = sorted(set(a) | set(b)); o = {(c, k): 0 for c in cats for k in cats}
    for x, y in zip(a, b): o[(x, y)] += 1; o[(y, x)] += 1
    nc = {c: sum(o[(c, k)] for k in cats) for c in cats}; N = sum(nc.values())
    num = sum(o[(c, k)] for c in cats for k in cats if c != k); den = sum(nc[c] * nc[k] for c in cats for k in cats if c != k)
    return None if den == 0 else 1 - (N - 1) * num / den

def boot_ci(fn, a, b, B=5000, seed=42):
    n = len(a); rng = random.Random(seed); est = []
    for _ in range(B):
        idx = [rng.randrange(n) for _ in range(n)]
        v = fn([a[i] for i in idx], [b[i] for i in idx])
        if v is not None: est.append(v)
    est.sort()
    return [round(est[int(.025 * len(est))], 3), round(est[int(.975 * len(est)) - 1], 3)] if len(est) > 20 else [None, None]

def reliability(d1, d2, ids):
    a = [d1[i]["decision"] for i in ids]; b = [d2[i]["decision"] for i in ids]; n = len(ids)
    conf = {x: {y: sum(1 for p, q in zip(a, b) if p == x and q == y) for y in DECISIONS} for x in DECISIONS}
    r4 = lambda v: None if v is None else round(v, 4)
    bin_ = lambda xs: ["V" if x == "POLICY_VIOLATING" else "O" for x in xs]
    ab, bb = bin_(a), bin_(b)
    out = {"n_items": n, "raw_agreement": r4(sum(x == y for x, y in zip(a, b)) / n), "n_agree": sum(x == y for x, y in zip(a, b)),
           "n_disagree": sum(x != y for x, y in zip(a, b)),
           "cohen_kappa": r4(cohen_kappa(a, b)), "cohen_kappa_ci95_bootstrap": boot_ci(cohen_kappa, a, b),
           "krippendorff_alpha_nominal": r4(krippendorff_alpha_nominal(a, b)),
           "gwet_ac1": r4(gwet_ac1(a, b)), "gwet_ac1_ci95_bootstrap": boot_ci(gwet_ac1, a, b),
           "prevalence": {"rater1": {c: a.count(c) for c in DECISIONS}, "rater2": {c: b.count(c) for c in DECISIONS},
                          "rater1_share": {c: r4(a.count(c) / n) for c in DECISIONS}, "rater2_share": {c: r4(b.count(c) / n) for c in DECISIONS}},
           "confusion_matrix_rows_rater1_cols_rater2": conf,
           "per_category_positive_agreement": {c: r4(2 * conf[c][c] / (a.count(c) + b.count(c))) if (a.count(c) + b.count(c)) else None for c in DECISIONS},
           "binary_violating_vs_other": {"raw_agreement": r4(sum(x == y for x, y in zip(ab, bb)) / n),
                                         "cohen_kappa": r4(cohen_kappa(ab, bb, ("V", "O"))), "cohen_kappa_ci95_bootstrap": boot_ci(lambda x, y: cohen_kappa(x, y, ("V", "O")), ab, bb),
                                         "gwet_ac1": r4(gwet_ac1(ab, bb, ("V", "O"))), "krippendorff_alpha_nominal": r4(krippendorff_alpha_nominal(ab, bb))},
           "limitations": ["Only 2 raters and a small sample; every coefficient has a wide interval (see bootstrap CIs).",
                           "When one category dominates, kappa and alpha can be low even with high raw agreement (kappa paradox); read them with AC1, "
                           "per-category agreement and the prevalence table.",
                           "Items are posts; texts of one phase are independent posts, but the phase 2 file repeats phase 1 posts.",
                           "No verbal strength label is assigned to any coefficient."]}
    if any(out["prevalence"][r][c] == 0 for r in ("rater1", "rater2") for c in DECISIONS):
        out["limitations"].append("At least one category is never used by at least one rater; coefficients that depend on that category are unstable.")
    return out

def final_labels(d1, d2, adjudication, ids):
    """-> {blind_id: (label or None, source)}. Disagreements are resolved ONLY by a valid adjudication row."""
    out = {}
    for i in ids:
        if d1[i]["decision"] == d2[i]["decision"]: out[i] = (d1[i]["decision"], "agreement"); continue
        adj = (adjudication or {}).get(i)
        out[i] = (adj["final_decision"], "adjudicated") if adj else (None, "unresolved")
    return out

def read_adjudication(path, disagreement_ids):
    """-> (dict blind_id -> row for completed rows, errors). A row counts only if it is complete and valid."""
    rows = {}; errors = []
    for n, r in enumerate(csv.DictReader(open(path, newline="", encoding="utf-8-sig")), start=2):
        bid = (r.get("blind_id") or "").strip(); fd = (r.get("final_decision") or "").strip()
        if bid not in disagreement_ids: errors.append(f"line {n} ({bid}): not a disagreement item"); continue
        if not fd: continue                                    # not decided yet -> stays unresolved
        problems = []
        if fd not in DECISIONS: problems.append(f"final_decision '{fd}' invalid")
        if not (r.get("adjudicator_id") or "").strip(): problems.append("adjudicator_id empty")
        if (r.get("adjudication_process") or "").strip() not in ADJ_PROCESSES: problems.append(f"adjudication_process must be one of {ADJ_PROCESSES}")
        if not (r.get("final_justification") or "").strip(): problems.append("final_justification empty")
        if problems: errors.append(f"line {n} ({bid}): " + "; ".join(problems)); continue
        rows[bid] = {**r, "final_decision": fd}
    return rows, errors

def write_adjudication_template(path, d1, d2, ids):
    rows = []
    for i in ids:
        if d1[i]["decision"] != d2[i]["decision"]:
            rows.append({"blind_id": i, "text": d1[i]["text"],
                         **{f"rater1_{k}": d1[i][v] for k, v in (("decision", "decision"), ("clause", "clause"), ("span", "span"), ("justification", "justification"), ("uncertainty", "uncertainty"))},
                         **{f"rater2_{k}": d2[i][v] for k, v in (("decision", "decision"), ("clause", "clause"), ("span", "span"), ("justification", "justification"), ("uncertainty", "uncertainty"))},
                         "adjudicator_id": "", "adjudication_process": "", "final_decision": "", "final_clause": "", "final_span": "", "final_justification": ""})
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ADJ_COLS); w.writeheader(); w.writerows(rows)
    return len(rows)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--phase", type=int, required=True, choices=(1, 2))
    ap.add_argument("--rater1", required=True); ap.add_argument("--rater2", required=True)
    ap.add_argument("--key", default=None); ap.add_argument("--out-dir", default=os.path.join(HERE, "analysis")); a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True); key = load_key(a.key, a.phase)
    d1, e1 = read_annotations(a.rater1, key); d2, e2 = read_annotations(a.rater2, key)
    if d1 and d2 and not e1 and not e2 and d1[next(iter(d1))]["rater_id"] == d2[next(iter(d2))]["rater_id"]:
        e2.append("both files use the same rater_id; each rater must use a different label")
    report = {"phase": a.phase, "rater1_file": a.rater1, "rater2_file": a.rater2, "validation_errors": {"rater1": e1, "rater2": e2}}
    if e1 or e2:
        report["status"] = "INVALID: no statistics computed"
        json.dump(report, open(f"{a.out_dir}/reliability_phase{a.phase}.json", "w"), indent=1)
        print("INVALID annotation file(s):", len(e1), "errors in rater1,", len(e2), "in rater2 (see report). No statistics computed."); return 2
    ids = sorted(key); report["status"] = "OK"; report.update(reliability(d1, d2, ids))
    report["n_adjudication_items"] = write_adjudication_template(f"{a.out_dir}/adjudication_phase{a.phase}.csv", d1, d2, ids)
    json.dump(report, open(f"{a.out_dir}/reliability_phase{a.phase}.json", "w"), indent=1)
    with open(f"{a.out_dir}/confusion_phase{a.phase}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["rater1 \\ rater2", *DECISIONS])
        for x in DECISIONS: w.writerow([x, *(report["confusion_matrix_rows_rater1_cols_rater2"][x][y] for y in DECISIONS)])
    print(json.dumps({k: report[k] for k in ("n_items", "raw_agreement", "cohen_kappa", "cohen_kappa_ci95_bootstrap", "krippendorff_alpha_nominal", "gwet_ac1", "n_adjudication_items")}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
