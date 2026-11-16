#!/usr/bin/env python3
"""
Revised evaluator addressing the ReviewForge findings R002-R007.

Key changes vs evaluate.py:
  R003  Verdict and citation are scored SEPARATELY.
        - verdict_pass: does the verdict fall in the accept set? (no citation needed)
        - citation: only computed for VIOLATING verdicts of models that cite; reported
          as a separate quality metric, never folded into the MR pass/fail.
        A model that returns no citations is simply "no citation channel", not a failure.
  R004  Policy axis is split by whether the reference label CHANGES under the new policy:
        R2 (narrow)  -> changed group (offensive posts) vs unchanged (hate, normal)
        R3 (negate)  -> all labels flip; pass rate of a fixed-verdict model equals
                        P(fixed verdict == flipped label), so it is reported with an
                        explicit confound flag, not as "policy sensitivity".
        R1 (delete)  -> abstain-protocol test; needs an insufficient channel.
  R005  Identity swap (I1) vs neutral sentence (I2): McNemar discordant counts (b,c),
        two-way flip direction, and a cluster bootstrap CI for the paired difference
        flip(I1) - flip(I2).
  R006  Reconciliation: items created / with usable text / analyzed, per MR; I3 status.
  R007  Per-class verdict accuracy; same evaluation can be run on any item file so the
        LR baseline can be scored on the SAME 600 posts as the LLMs.

Usage:
  python revise_eval.py --items items_test_full.jsonl --runs runs/full_word-LR.jsonl runs/full_char-LR.jsonl --out results/revised_full.json
  python revise_eval.py --items items_llm600.jsonl   --runs runs/s600_word-LR.jsonl runs/s600_char-LR.jsonl --out results/revised_600.json
"""
import argparse, json, math, random, re
from collections import Counter, defaultdict

V, NV, INS = "violating", "not_violating", "insufficient"

def toks(s): return re.findall(r"\S+", (s or "").lower())

def citation_support(it, r, tau=0.5):
    """For a VIOLATING verdict only: do the cited words overlap the gold rationale?
    Returns None when the model gives no citation channel (so it is not counted)."""
    q = []
    for x in r.get("quotes") or []: q += toks(x)
    if not q: return None
    text = set(toks(it["text"]))
    if any(t not in text for t in q): return False      # non-verbatim quote
    gold = set(t.lower() for t in it["gold_evidence"])
    if not gold: return None
    return sum(t in gold for t in q) / len(q) >= tau

def token_f1(it, r):
    gold = Counter(t.lower() for t in it["gold_evidence"]); q = Counter()
    for x in r.get("quotes") or []: q.update(toks(x))
    if not gold: return None
    if not q: return None
    ov = sum((gold & q).values()); p, rc = ov / sum(q.values()), ov / sum(gold.values())
    return 2 * p * rc / (p + rc) if p + rc else 0.0

def wilson(k, n, z=1.96):
    if n == 0: return [None, None]
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]

def cluster_boot_diff(pairs, B=5000, seed=42):
    """pairs: list of (flipI1 0/1, flipI2 0/1) per post. CI for mean(I1)-mean(I2)."""
    if not pairs: return [None, None]
    rng = random.Random(seed); n = len(pairs); est = []
    for _ in range(B):
        s = [pairs[rng.randrange(n)] for _ in range(n)]
        est.append(sum(a for a, _ in s) / n - sum(b for _, b in s) / n)
    est.sort(); return [round(est[int(.025 * B)], 4), round(est[int(.975 * B) - 1], 4)]

def mcnemar_exact(b, c):
    n = b + c
    if n == 0: return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)

def evaluate(items, recs):
    by = {r["item_id"]: r for r in recs}
    groups = defaultdict(dict)
    for it in items.values():
        if it["item_id"] in by: groups[it["post_id"]][it["mr"]] = (it, by[it["item_id"]])
    # ---- R006 reconciliation ----
    created = Counter(it["mr"] for it in items.values())
    usable = Counter(it["mr"] for it in items.values() if it.get("text"))            # has text
    scored = Counter(it["mr"] for it in items.values() if it["item_id"] in by)        # model answered
    # ---- verdict accuracy (EV1), overall and per class ----
    orig = [(it, by[it["item_id"]]) for it in items.values() if it["mr"] == "ORIG" and it["item_id"] in by]
    acc = sum(r["verdict"] in it["accept"] for it, r in orig) / len(orig)
    per_class = {}
    for lab in ("hatespeech", "offensive", "normal"):
        g = [(it, r) for it, r in orig if it["label"] == lab]
        per_class[lab] = [round(sum(r["verdict"] in it["accept"] for it, r in g) / len(g), 4), len(g)] if g else None
    # ---- verdict-only MR pass (NO citation requirement) ----
    def vpass(mr, accept_field="accept"):
        xs = [(it, by.get(it["item_id"])) for it in items.values() if it["mr"] == mr and it.get("text") and it["item_id"] in by]
        if not xs: return None
        if mr.startswith("I"):   # invariance: equal to the model's own ORIG verdict
            k = 0
            for it, r in xs:
                o = groups[it["post_id"]].get("ORIG")
                if o and r["verdict"] == o[1]["verdict"] and r["verdict"] != "refused": k += 1
            return [round(k / len(xs), 4), len(xs), wilson(k, len(xs))]
        k = sum(r["verdict"] in it[accept_field] for it, r in xs)
        return [round(k / len(xs), 4), len(xs), wilson(k, len(xs))]
    verdict_only = {mr: vpass(mr) for mr in ("E1", "E2", "R1", "R2", "R3", "I1", "I2")}
    verdict_only["E1_lenient"] = vpass("E1", "accept_lenient")   # accepts 'insufficient'
    verdict_only["I3"] = {"status": "not evaluated in pilot (paraphrase requires an LLM; no text generated for the LR baseline)",
                          "created": created.get("I3", 0)}
    # ---- R004 policy axis split by reference-label change ----
    def split_policy(mr):
        xs = [(it, by[it["item_id"]]) for it in items.values() if it["mr"] == mr and it["item_id"] in by]
        orig_gold = {it["post_id"]: groups[it["post_id"]]["ORIG"][0]["gold"] for it, _ in xs if "ORIG" in groups[it["post_id"]]}
        changed = [(it, r) for it, r in xs if orig_gold.get(it["post_id"]) != it["gold"]]
        stayed = [(it, r) for it, r in xs if orig_gold.get(it["post_id"]) == it["gold"]]
        f = lambda g: [round(sum(r["verdict"] in it["accept"] for it, r in g) / len(g), 4), len(g)] if g else None
        return {"label_changed": f(changed), "label_unchanged": f(stayed)}
    policy_split = {"R2_narrow": split_policy("R2"), "R3_negate": split_policy("R3")}
    policy_split["R3_confound_note"] = ("R3 flips every reference label, so for a fixed-verdict (policy-blind) model "
                                        "R3 pass rate equals P(fixed verdict == flipped label), i.e. the complement "
                                        "of a label-balanced accuracy, not policy sensitivity.")
    # ---- citation quality, separate, violating verdicts only ----
    cit = [citation_support(it, r) for it, r in orig if r["verdict"] == V]
    cit = [c for c in cit if c is not None]
    f1s = [token_f1(it, r) for it, r in orig if r["verdict"] == V]
    f1s = [f for f in f1s if f is not None]
    citation = {"has_citation_channel": bool(cit or f1s),
                "support_rate_on_violating": [round(sum(cit) / len(cit), 4), len(cit)] if cit else None,
                "token_f1_on_violating": round(sum(f1s) / len(f1s), 4) if f1s else None}
    # ---- R005 identity swap vs neutral sentence (paired on same posts) ----
    pairs, bdir, cdir = [], Counter(), Counter()
    for pid, d in groups.items():
        if {"ORIG", "I1", "I2"} <= set(d):
            o = d["ORIG"][1]["verdict"]; i1 = d["I1"][1]["verdict"]; i2 = d["I2"][1]["verdict"]
            f1, f2 = int(i1 != o or i1 == "refused"), int(i2 != o or i2 == "refused"); pairs.append((f1, f2))   # a refusal is not holding the verdict
            if i1 != o: bdir[f"{o}->{i1}"] += 1
    b = sum(a and not c for a, c in pairs); c_ = sum(c and not a for a, c in pairs)
    swap = {"n_posts": len(pairs),
            "flip_I1": [round(sum(a for a, _ in pairs) / len(pairs), 4), sum(a for a, _ in pairs)] if pairs else None,
            "flip_I2": [round(sum(x for _, x in pairs) / len(pairs), 4), sum(x for _, x in pairs)] if pairs else None,
            "mcnemar_discordant": {"only_I1_flips_b": b, "only_I2_flips_c": c_, "exact_p": float(f"{mcnemar_exact(b, c_):.3g}")},
            "paired_diff_I1_minus_I2": round((sum(a for a, _ in pairs) - sum(x for _, x in pairs)) / len(pairs), 4) if pairs else None,
            "paired_diff_CI95": cluster_boot_diff(pairs),
            "flip_direction_I1": dict(bdir)}
    # ---- dual-axis diagnostic structure (reviewer's cross-tab); degenerate for policy-blind LR ----
    both = []
    for pid, d in groups.items():
        epass = all(d[m][1]["verdict"] in d[m][0]["accept"] for m in ("E1", "E2") if m in d)
        rpass = all(d[m][1]["verdict"] in d[m][0]["accept"] for m in ("R1", "R2", "R3") if m in d)
        has_e = any(m in d for m in ("E1", "E2")); has_r = any(m in d for m in ("R1", "R2", "R3"))
        if has_e and has_r: both.append((epass, rpass))
    crosstab = {"evidence_and_policy": sum(e and r for e, r in both), "evidence_only": sum(e and not r for e, r in both),
                "policy_only": sum((not e) and r for e, r in both), "neither": sum((not e) and (not r) for e, r in both),
                "n": len(both)}
    return {"verdict_accuracy_EV1": round(acc, 4), "n_orig": len(orig), "accuracy_per_class": per_class,
            "verdict_only_MR_pass": verdict_only, "policy_axis_split": policy_split, "citation_quality": citation,
            "identity_swap": swap, "dual_axis_crosstab": crosstab,
            "reconciliation": {"created": dict(created), "with_text": dict(usable), "scored": dict(scored)}}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--items", required=True); ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", required=True); a = ap.parse_args()
    items = {json.loads(l)["item_id"]: json.loads(l) for l in open(a.items)}
    out = {"item_file": a.items, "systems": {}}
    for p in a.runs:
        recs = [json.loads(l) for l in open(p)]
        out["systems"][recs[0]["system"]] = evaluate(items, recs)
    json.dump(out, open(a.out, "w"), indent=1)
    for s, v in out["systems"].items():
        vo = v["verdict_only_MR_pass"]
        print(f"\n== {s} ==  EV1 acc={v['verdict_accuracy_EV1']}  per-class={v['accuracy_per_class']}")
        print("  verdict-only pass:", {k: (vv[0] if isinstance(vv, list) else vv) for k, vv in vo.items() if k != "I3"})
        print("  R2 split:", v['policy_axis_split']['R2_narrow'])
        print("  citation:", v['citation_quality'])
        sw = v['identity_swap']
        print(f"  swap flipI1={sw['flip_I1']} flipI2={sw['flip_I2']} diff={sw['paired_diff_I1_minus_I2']} CI={sw['paired_diff_CI95']} McNemar b={sw['mcnemar_discordant']['only_I1_flips_b']} c={sw['mcnemar_discordant']['only_I2_flips_c']} p={sw['mcnemar_discordant']['exact_p']}")

if __name__ == "__main__":
    main()
