"""Independent recomputation of key manuscript numbers from raw classified records, compared with
(a) the audited result files and (b) the numbers printed in body.tex.  Read-only.
Usage: python3 verify_numbers.py <repo> <body.tex>
"""
import json, sys, os, re, math
from collections import Counter, defaultdict
repo, body_path = sys.argv[1], sys.argv[2]
os.chdir(repo)
sys.dont_write_bytecode = True
sys.path.insert(0, repo)
from build_items import GROUP_TERMS  # noqa
from scipy.stats import fisher_exact

body = open(body_path).read()
items = {}
for l in open("items_llm600.jsonl"):
    d = json.loads(l); items[d["item_id"]] = d
rec = json.load(open("results/audited/response_classification.json"))["records"]
S = defaultdict(dict)
for r in rec:
    S[r["system"]][r["item_id"]] = r
fails = []
def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("  " + detail if detail else ""))
    if not ok: fails.append(name)
def inbody(s): return s in body

def wilson(k, n, z=1.959964):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h

orig = [i for i in items.values() if i["mr"] == "ORIG"]
# 1 coverage / accuracy / refusal
for s in S:
    ids = [i["item_id"] for i in orig]
    cat = Counter(S[s][i]["category"] for i in ids)
    valid = [i for i in ids if S[s][i]["category"] == "VALID_VERDICT"]
    corr = sum(S[s][i]["verdict"] in items[i]["accept"] for i in valid)
    cov = len(valid) / 600; ca = corr / len(valid); oa = corr / 600
    print(f"{s}: cov {cov:.4f} condacc {ca:.4f} overall {oa:.4f}")
ref_all = {s: sum(r["category"] == "REFUSAL" for r in S[s].values()) / len(S[s]) for s in S}
check("llama direct refusal 56.2", abs(ref_all["llama3.1:8b|direct"] - 0.5622) < 5e-4 and inbody("56.2\\%"))
check("llama evidence refusal 81.2", abs(ref_all["llama3.1:8b|evidence"] - 0.8117) < 5e-4 and inbody("81.2\\%"))
# the manuscript interval is the post-cluster bootstrap CI stored in model_comparison.csv (column ALL_refusal_ci95); a Wilson interval over
# 4,233 items would treat items of the same post as independent
import csv
mc_row = {r["system"]: r for r in csv.DictReader(open("results/audited/model_comparison.csv"))}["llama3.1:8b|direct"]
lo, hi = json.loads(mc_row["ALL_refusal_ci95"])
check("llama direct refusal CI [53.4, 59.0]", f"[{100*lo:.1f}, {100*hi:.1f}]" == "[53.4, 59.0]" and inbody("[53.4, 59.0]"), f"{100*lo:.1f},{100*hi:.1f} (ALL_refusal_ci95)")
# refusal by gold class (all items) and by MR
for sysname in ("llama3.1:8b|direct", "llama3.1:8b|evidence"):
    bc = defaultdict(lambda: [0, 0])
    for i, r in S[sysname].items():
        it = items[i]; bc[it["label"]][1] += 1; bc[it["label"]][0] += r["category"] == "REFUSAL"
    print(sysname, {k: round(v[0] / v[1] * 100) for k, v in bc.items()})
    e2 = [i for i in S[sysname] if items[i]["mr"] == "E2"]
    print(sysname, "E2 refusal", round(sum(S[sysname][i]["category"] == "REFUSAL" for i in e2) / len(e2) * 100))
# per-class accuracy on ORIG
def acc_by_class(s):
    out = {}
    for lab in ("hatespeech", "offensive", "normal"):
        ids = [i["item_id"] for i in orig if i["label"] == lab]
        out[lab] = sum(S[s][i]["category"] == "VALID_VERDICT" and S[s][i]["verdict"] in items[i]["accept"] for i in ids) / len(ids)
    return out
for s, nm in (("gemma2:9b|direct", "28.0"), ("gemma2:9b|evidence", "13.0")):
    a = acc_by_class(s)["normal"]; check(f"{s} normal acc {nm}", f"{100*a:.1f}" == nm and inbody(nm + "\\%"), f"{100*a:.1f}")
a = acc_by_class("word-LR")["normal"]; check("word-LR normal acc 76", round(100 * a) == 76 and inbody("76\\% for word-LR"), f"{100*a:.1f}")
# 2 E1 residual identity
allterms = set().union(*GROUP_TERMS.values())
e1 = [i for i in items.values() if i["mr"] == "E1"]
def has_id(it): return any(t in allterms for t in it["text"].lower().split())
n_id = sum(has_id(i) for i in e1); check("88 E1 posts retain an identity token", n_id == 88, str(n_id))
for s, (k1, n1, k0, n0) in {"gemma2:9b|direct": (74, 88, 116, 309), "qwen2.5:7b|direct": (43, 88, 73, 309)}.items():
    a1 = [(S[s][i["item_id"]]["category"] == "VALID_VERDICT" and S[s][i["item_id"]]["verdict"] == "violating") for i in e1 if has_id(i) and S[s][i["item_id"]]["category"] in ("VALID_VERDICT", "ABSTENTION")]
    a0 = [(S[s][i["item_id"]]["category"] == "VALID_VERDICT" and S[s][i["item_id"]]["verdict"] == "violating") for i in e1 if not has_id(i) and S[s][i["item_id"]]["category"] in ("VALID_VERDICT", "ABSTENTION")]
    orr = fisher_exact([[sum(a1), len(a1) - sum(a1)], [sum(a0), len(a0) - sum(a0)]])[0]
    check(f"{s} identity flagged {sum(a1)}/{len(a1)} vs {sum(a0)}/{len(a0)} OR {orr:.1f}", (sum(a1), len(a1), sum(a0), len(a0)) == (k1, n1, k0, n0))
# 3 E1 transitions
for s in ("qwen2.5:7b|direct", "gemma2:9b|direct", "gemma2:9b|evidence"):
    n = 0; t = Counter()
    for i in e1:
        o = S[s][i["source_id"]]; r = S[s][i["item_id"]]
        if o["verdict"] == "violating" and o["category"] == "VALID_VERDICT" and r["category"] in ("VALID_VERDICT", "ABSTENTION"):
            n += 1; t["ins" if r["category"] == "ABSTENTION" else r["verdict"]] += 1
    print(s, "E1 n", n, {k: round(v / n * 100, 1) for k, v in t.items()})
# 4 E1-CF: recompute flag rates PLC/NEU from raw runs (abstention = not flagged)
from response_classifier import classify_record
cfi = {json.loads(l)["item_id"]: json.loads(l) for l in open("results/e1_counterfactual/items_e1cf.jsonl")}
an = json.load(open("results/e1_counterfactual/analysis.json"))
for s, fn in {"qwen2.5:7b|direct": "qwen2.5_7b_direct", "gemma2:9b|direct": "gemma2_9b_direct"}.items():
    F = defaultdict(dict)
    for l in open(f"results/e1_counterfactual/runs/{fn}.jsonl"):
        r = json.loads(l); c = classify_record(r); it = cfi[r["item_id"]]
        F[it["e1_item_id"]][it["cf_condition"]] = (c["category"] in ("VALID_VERDICT", "ABSTENTION"), c["category"] == "VALID_VERDICT" and c["verdict"] == "violating")
    pr = [(F[p]["PLC"][1], F[p]["NEU"][1]) for p in F if F[p]["PLC"][0] and F[p]["NEU"][0]]
    plc = sum(a for a, b in pr) / len(pr); neu = sum(b for a, b in pr) / len(pr)
    h = an["systems"][s]["H1_PLC_minus_NEU"]
    check(f"{s} H1 recomputed PLC {plc:.4f} NEU {neu:.4f}", abs(plc - h["rate_x"]) < 1e-3 and abs(neu - h["rate_y"]) < 1e-3 and len(pr) == h["n_pairs"])
# 5 abstract and text claims vs body
abstract = re.search(r"ABS=\((.*?)\)\n", open(os.path.join(os.path.dirname(body_path), "assemble.py")).read(), re.S).group(1)
words = len(re.sub(r'"\s*\n?\s*"', "", abstract).replace('"', "").split())
check(f"abstract words {words} in 100-150", 100 <= words <= 150)
print("FAILS:", fails)
sys.exit(1 if fails else 0)
