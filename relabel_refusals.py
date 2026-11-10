#!/usr/bin/env python3
"""
Re-label refusals in finished runs (raw model text is kept; only the verdict field of refusals changes).
A refusal ("I cannot create content that ...") used to be folded into 'insufficient'. Here it becomes its own
verdict 'refused', which never passes any MR, and refusal rates are reported per system / MR / gold class.

  python relabel_refusals.py --items items_llm600.jsonl --runs runs/*_direct.jsonl runs/*_evidence.jsonl --out-dir runs_rl --rates results/refusal_rates.json
Runs without a raw field (the LR baselines) are copied unchanged.
"""
import argparse, json, os, collections
import run_llm

ap = argparse.ArgumentParser(); ap.add_argument("--items", required=True); ap.add_argument("--runs", nargs="+", required=True)
ap.add_argument("--out-dir", required=True); ap.add_argument("--rates", required=True); a = ap.parse_args()
items = {json.loads(l)["item_id"]: json.loads(l) for l in open(a.items)}
os.makedirs(a.out_dir, exist_ok=True); rates = {}
for p in a.runs:
    recs = [json.loads(l) for l in open(p)]; n = collections.Counter(); k = collections.Counter(); changed = 0
    for r in recs:
        if "raw" in r:
            q = run_llm.parse(r["raw"])
            if q.get("refused") and r["verdict"] != "refused": r.update(q); changed += 1
        it = items[r["item_id"]]
        for key in ("ALL", it["mr"], "class:" + it["label"]):
            n[key] += 1; k[key] += r["verdict"] == "refused"
    with open(os.path.join(a.out_dir, os.path.basename(p)), "w") as f:
        for r in recs: f.write(json.dumps(r) + "\n")
    rates[recs[0]["system"]] = {"n": len(recs), "relabelled": changed, "refusal_rate": {key: [round(k[key] / n[key], 4), k[key], n[key]] for key in sorted(n)}}
json.dump(rates, open(a.rates, "w"), indent=1)
for s, v in rates.items(): print(s.ljust(24), "n", v["n"], "ditandai refused:", v["relabelled"], "| rate", v["refusal_rate"]["ALL"][0])
