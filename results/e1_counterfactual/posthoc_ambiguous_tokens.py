#!/usr/bin/env python3
"""
POST HOC sensitivity of E1-CF to ambiguous identity tokens. NOT part of the pre-specified protocol
(PROTOCOL.md section 8, entry 4).

Some tokens in build_items.GROUP_TERMS are frequent ordinary words ("white", "black", "man"). A post whose ONLY identity tokens are such
words may not be an identity-term case at all. This script drops those posts and repeats the two protocol contrasts on the rest:
  H1: flag(PLC) - flag(NEU)        S1: flag(PLCDEL) - flag(DEL)
using exactly the functions of analyze_e1_counterfactual.py (pairs = both conditions answered, abstention = not flagged,
exact McNemar, post-bootstrap CI B=5000 seed 42), with Holm over the 4 qwen2.5/gemma2 conditions (post hoc family) per contrast.

Sets (a post is flagged ambiguous when ALL its identity tokens are in the set):
  core      {black, white, man}                                     expected 25 of 88 posts -> 63 remain
  extended  core + plurals {blacks, whites, men}                    expected 33 of 88 posts -> 55 remain (comparison)

Reads results/e1_counterfactual/{items_e1cf.jsonl, runs/*.jsonl}, analysis.json. Writes only --out.
  PYTHONDONTWRITEBYTECODE=1 python results/e1_counterfactual/posthoc_ambiguous_tokens.py [--out file.json]
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(HERE, "posthoc_ambiguous_tokens.json")); a = ap.parse_args()
os.chdir(ROOT); sys.dont_write_bytecode = True; sys.path.insert(0, ROOT)
from analyze_e1_counterfactual import load_system, contrast  # noqa: E402
from audit_metrics import holm  # noqa: E402

D = "results/e1_counterfactual"
CORE = ["black", "white", "man"]
EXT = ["black", "blacks", "white", "whites", "man", "men"]
EXPECTED = {"core": 25, "extended": 33}
SYS = {"qwen2.5:7b|direct": "qwen2.5_7b_direct", "qwen2.5:7b|evidence": "qwen2.5_7b_evidence",
       "gemma2:9b|direct": "gemma2_9b_direct", "gemma2:9b|evidence": "gemma2_9b_evidence"}

items = {}
for l in open(f"{D}/items_e1cf.jsonl"):
    it = json.loads(l); items[it["item_id"]] = it
tokens = {}                                                  # post (e1_item_id) -> identity tokens (identical in all 5 conditions)
for it in items.values():
    tokens.setdefault(it["e1_item_id"], tuple(it["cf_meta"]["identity_tokens"]))
    assert tokens[it["e1_item_id"]] == tuple(it["cf_meta"]["identity_tokens"])
posts = sorted(tokens)
assert len(posts) == 88, len(posts)

sets = {}
for name, toks in (("core", CORE), ("extended", EXT)):
    flagged = sorted(p for p in posts if tokens[p] and set(tokens[p]) <= set(toks))
    sets[name] = {"tokens": toks, "n_posts_all_tokens_ambiguous": len(flagged), "n_posts_remaining": len(posts) - len(flagged),
                  "excluded_e1_item_ids": flagged}
    print(f"{name}: {len(flagged)} of {len(posts)} posts have only ambiguous tokens -> {len(posts) - len(flagged)} remain (expected {EXPECTED[name]})")
bad = {k: v["n_posts_all_tokens_ambiguous"] for k, v in sets.items() if v["n_posts_all_tokens_ambiguous"] != EXPECTED[k]}
if bad:
    sys.exit(f"STOP: counts differ from the expected {EXPECTED}: {bad}")

flags = {s: load_system(f"{D}/runs/{fn}.jsonl", items) for s, fn in SYS.items()}
analysis = json.load(open(f"{D}/analysis.json"))

def run(keep):
    out = {}
    for key, (a_, b_) in (("H1_PLC_minus_NEU", ("PLC", "NEU")), ("S1_PLCDEL_minus_DEL", ("PLCDEL", "DEL"))):
        per = {s: contrast(S, a_, b_, keep=keep) for s, S in flags.items()}
        h = holm({s: per[s]["mcnemar_exact_p"] for s in per})
        for s in per: per[s]["holm_p_posthoc_4"] = h.get(s)
        out[key] = per
    return out

res = {"label": "POST HOC (not in the E1-CF protocol); added 2026-11-10 after the audit; protocol section 6 decision rule NOT changed",
       "method": "same functions as analyze_e1_counterfactual.py (load_system, contrast): pairs = both conditions answered; abstention = not flagged; "
                 "exact McNemar; post-bootstrap CI (B=5000, seed 42); Holm over the 4 qwen2.5/gemma2 conditions per contrast",
       "sets": sets, "results": {}}
# sanity: the full 88-post set must reproduce the primary analysis exactly
full = run(lambda p: True); sanity = {}
for s in SYS:
    for key in ("H1_PLC_minus_NEU", "S1_PLCDEL_minus_DEL"):
        r, ref = full[key][s], analysis["systems"][s][key]
        sanity[f"{s}|{key}"] = all(r[k] == ref[k] for k in ("n_pairs", "rate_x", "rate_y", "risk_difference", "b_only_x", "c_only_y", "mcnemar_exact_p", "rd_ci95_post_bootstrap"))
res["sanity_full_88_equals_analysis_json"] = sanity
print("sanity (88 posts reproduce analysis.json for all 8 contrasts):", all(sanity.values()))
if not all(sanity.values()):
    sys.exit("STOP: the full-set contrasts do not reproduce analysis.json")

for name, spec in sets.items():
    excluded = set(spec["excluded_e1_item_ids"]); r = run(lambda p, ex=excluded: p not in ex)
    pos = {k: [s for s in SYS if (r[k][s]["risk_difference"] or 0) > 0 and (r[k][s]["holm_p_posthoc_4"] or 1) < 0.05] for k in r}
    r["descriptive_rule_reading"] = {
        "note": "descriptive reading of the section 6 rule on the remaining posts; the protocol rule itself is unchanged and its outcome (SUPPORT) is the one in analysis.json",
        "holm_significant_positive_H1": pos["H1_PLC_minus_NEU"], "holm_significant_positive_S1": pos["S1_PLCDEL_minus_DEL"],
        "n_with_both": len(set(pos["H1_PLC_minus_NEU"]) & set(pos["S1_PLCDEL_minus_DEL"]))}
    res["results"][f"{name}_excluded"] = r
    print(f"\n--- remaining posts after excluding the {name} set ({spec['n_posts_remaining']} posts)")
    for key in ("H1_PLC_minus_NEU", "S1_PLCDEL_minus_DEL"):
        for s in SYS:
            t = r[key][s]
            print(f"{key[:2]} {s:20} n={t['n_pairs']:2} RD={100 * t['risk_difference']:+5.1f} [{100 * t['rd_ci95_post_bootstrap'][0]:+.1f},{100 * t['rd_ci95_post_bootstrap'][1]:+.1f}] b/c={t['b_only_x']}/{t['c_only_y']} p={t['mcnemar_exact_p']} holm4={t['holm_p_posthoc_4']}")
    print("   ", r["descriptive_rule_reading"]["holm_significant_positive_H1"], "| both contrasts:", r["descriptive_rule_reading"]["n_with_both"])
json.dump(res, open(a.out, "w"), indent=1)
