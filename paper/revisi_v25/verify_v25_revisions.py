"""Checks for the v25 revisions (audit #9). Read-only on the repository.

Part A recomputes, from the result files, every number that the v25 revision adds or changes.
Part B (only if a body.tex is given) checks that the manuscript carries the new strings and none of the retired phrasings.

Usage:  python3 paper/revisi_v25/verify_v25_revisions.py <repo> [body.tex]
Exit code 1 if any check fails.
"""
import csv, json, os, re, sys

repo = sys.argv[1]
body = open(sys.argv[2]).read() if len(sys.argv) > 2 else None
os.chdir(repo)
fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not ok:
        fails.append(name)


A = "results/audited"
sa = json.load(open(f"{A}/statistical_analysis.json"))
cf = json.load(open("results/e1_counterfactual/analysis.json"))
pv = json.load(open("results/e1_counterfactual/posthoc_valid_only.json"))
ov = [r for r in csv.DictReader(open(f"{A}/oracle_validity_analysis.csv")) if r["row_type"] == "model_sensitivity" and r["mr"] == "R2"]
R2 = {(r["system"], r["stratum"]): r for r in ov}
LLM4 = ["qwen2.5:7b|direct", "qwen2.5:7b|evidence", "gemma2:9b|direct", "gemma2:9b|evidence"]

# ---------- A1  Table 7 / Section 4.5: which R2 column is which ----------
amb = {s: round(100 * float(R2[(s, "offensive_ambiguous")]["C_validated_corrected_oracle"]), 1) for s in LLM4}
ctl = {s: round(100 * float(R2[(s, "offensive_control")]["C_validated_corrected_oracle"]), 1) for s in LLM4}
wtd = {s: round(100 * float(R2[(s, "offensive (stratum-weighted)")]["D_population_estimate_corrected"]), 1) for s in LLM4}
check("R2 corr. (59 ambiguous) = 76.3/67.8 Gemma, 72.9/70.2 Qwen",
      [amb[s] for s in ("gemma2:9b|direct", "gemma2:9b|evidence", "qwen2.5:7b|direct", "qwen2.5:7b|evidence")] == [76.3, 67.8, 72.9, 70.2], str(amb))
check("R2 wtd. (200 offensive) = 52.7/40.1 Gemma, 74.4/73.6 Qwen",
      [wtd[s] for s in ("gemma2:9b|direct", "gemma2:9b|evidence", "qwen2.5:7b|direct", "qwen2.5:7b|evidence")] == [52.7, 40.1, 74.4, 73.6], str(wtd))
check("R2 other offensive (28 rated) = 42.9/28.6 Gemma, 75.0/75.0 Qwen",
      [ctl[s] for s in ("gemma2:9b|direct", "gemma2:9b|evidence", "qwen2.5:7b|direct", "qwen2.5:7b|evidence")] == [42.9, 28.6, 75.0, 75.0], str(ctl))
for s in LLM4:   # the weighted estimate is 59/200 * ambiguous + 141/200 * other
    a = float(R2[(s, "offensive_ambiguous")]["C_validated_corrected_oracle"]); c = float(R2[(s, "offensive_control")]["C_validated_corrected_oracle"])
    check(f"R2 weighting 59/200, 141/200 reproduces D for {s}", abs(0.295 * a + 0.705 * c - float(R2[(s, 'offensive (stratum-weighted)')]["D_population_estimate_corrected"])) < 6e-4)

# ---------- A2  Table 6: separate H1 / S1 denominators, RD from raw counts ----------
n = {s: (cf["systems"][s]["H1_PLC_minus_NEU"]["n_pairs"], cf["systems"][s]["S1_PLCDEL_minus_DEL"]["n_pairs"]) for s in cf["systems"]}
check("Llama 3.1 direct n H1 = 52, n S1 = 47", n["llama3.1:8b|direct"] == (52, 47), str(n["llama3.1:8b|direct"]))
check("Llama 3.1 evidence n H1 = n S1 = 12", n["llama3.1:8b|evidence"] == (12, 12))
check("all other systems n H1 = n S1 = 88", all(v == (88, 88) for s, v in n.items() if not s.startswith("llama")))
rd = {s: round(100 * (h["b_only_x"] - h["c_only_y"]) / h["n_pairs"], 1) for s in LLM4 for h in [cf["systems"][s]["H1_PLC_minus_NEU"]]}
check("H1 RD range from raw counts = 17.0 to 25.0", (min(rd.values()), max(rd.values())) == (17.0, 25.0), str(rd))
s1 = {s: round(100 * (h["b_only_x"] - h["c_only_y"]) / h["n_pairs"], 1) for s in LLM4 for h in [cf["systems"][s]["S1_PLCDEL_minus_DEL"]]}
check("S1 RD range = 18.2 to 26.1", (min(s1.values()), max(s1.values())) == (18.2, 26.1), str(s1))
check("S1 has its own Holm family F_CF2", all("holm_p_F_CF2" in cf["systems"][s]["S1_PLCDEL_minus_DEL"] for s in LLM4 + ["llama3.1:8b|direct", "llama3.1:8b|evidence"]))
# no unparseable / error / empty in E1-CF: every unpaired post is a refusal (Llama only)
sys.path.insert(0, repo); sys.dont_write_bytecode = True
from response_classifier import classify_record  # noqa: E402
from collections import Counter  # noqa: E402
cats = Counter()
for fn in os.listdir("results/e1_counterfactual/runs"):
    if fn.startswith("cf_"):
        continue
    for line in open(f"results/e1_counterfactual/runs/{fn}"):
        c = classify_record(json.loads(line))["category"]
        cats[(fn.split("_")[0], c)] += 1
bad = {k: v for k, v in cats.items() if k[1] not in ("VALID_VERDICT", "ABSTENTION", "REFUSAL")}
ref = {k: v for k, v in cats.items() if k[1] == "REFUSAL"}
check("E1-CF: no unparseable/error/empty response", not bad, str(bad))
check("E1-CF: only Llama 3.1 refused", all(k[0].startswith("llama") for k in ref), str(ref))

# ---------- A3  Section 4.1: Llama 3.1 is in the overall-accuracy family F_B ----------
fb = sa["llm_vs_wordLR_ORIG"]["results"]
ld = fb["llama3.1:8b|direct"]["all_posts_nonanswer_wrong"]; le = fb["llama3.1:8b|evidence"]["all_posts_nonanswer_wrong"]
check("F_B overall accuracy includes Llama: RD -50.2 / -68.3, Holm p < 0.001",
      (round(100 * ld["risk_difference"], 1), round(100 * le["risk_difference"], 1)) == (-50.2, -68.3) and ld["holm_p_family_F_B"] < 1e-3 and le["holm_p_family_F_B"] < 1e-3)
check("F_B has 6 tests", len(fb) == 6)
check("no LLM condition better than word-LR in overall accuracy", all(v["all_posts_nonanswer_wrong"]["risk_difference"] <= 0 for v in fb.values()))
cov = {r["system"]: r for r in csv.DictReader(open(f"{A}/model_comparison.csv"))}
nv = {s: round(600 * float(cov[s]["ORIG_coverage_valid"])) for s in ("llama3.1:8b|direct", "llama3.1:8b|evidence")}
check("Llama valid verdicts on ORIG = 246 and 76", list(nv.values()) == [246, 76], str(nv))

# ---------- A4  Table 5: 2x2 of the OR population vs retention population ----------
res = sa["E1_residual_identity_terms"]["by_system"]
g = res["gemma2:9b|direct"]["all_answered"]
check("Gemma 2 direct OR population 74/88 vs 116/309", (g["flagged_with_identity"][1:3], g["flagged_without_identity"][1:3]) == ([74, 88], [116, 309]))
check("Llama 3.1 evidence OR population = 175 answered E1 posts",
      res["llama3.1:8b|evidence"]["all_answered"]["flagged_with_identity"][2] + res["llama3.1:8b|evidence"]["all_answered"]["flagged_without_identity"][2] == 175)
rt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "posthoc_e1_retention.json")
if os.path.exists(rt_path):
    rt = json.load(open(rt_path))["by_system"]
    for s in rt:
        check(f"retention n equals Table 5 n for {s}", rt[s]["n"] == sa["behaviour_E_R"][s]["E1"]["n_orig_violating_and_E1_answered"])
    ors = [rt[s]["odds_ratio_sample"] for s in LLM4]
    check("retention OR 6.1-10.6 in Qwen2.5/Gemma 2, Holm < 0.001", (round(min(ors), 1), round(max(ors), 1)) == (6.1, 10.6) and all(rt[s]["holm_p_posthoc_8"] < 1e-3 for s in LLM4), str(ors))
    kept = [100 * rt[s]["kept_with_identity"][0] / rt[s]["kept_with_identity"][1] for s in LLM4]
    other = [100 * rt[s]["kept_without_identity"][0] / rt[s]["kept_without_identity"][1] for s in LLM4]
    check("retention kept 70.5-87.1% vs 25.5-38.8%", (round(min(kept), 1), round(max(kept), 1), round(min(other), 1), round(max(other), 1)) == (70.5, 87.1, 25.5, 38.8))
    check("classifier retention OR 2.1/1.8, Holm 0.076/0.100",
          (round(rt["word-LR"]["odds_ratio_sample"], 1), round(rt["char-LR"]["odds_ratio_sample"], 1), round(rt["word-LR"]["holm_p_posthoc_8"], 3), round(rt["char-LR"]["holm_p_posthoc_8"], 3)) == (2.1, 1.8, 0.076, 0.1))
    check("Llama 3.1 direct retention OR 7.2, Holm 0.004", (round(rt["llama3.1:8b|direct"]["odds_ratio_sample"], 1), round(rt["llama3.1:8b|direct"]["holm_p_posthoc_8"], 3)) == (7.2, 0.004))
else:
    check("posthoc_e1_retention.json present (run paper/posthoc_e1_retention.py first)", False)

# ---------- A5  I1-I2 family: Llama evidence is inside F_I ----------
fi = sa["I1_vs_I2"]["main"]
check("F_I has 8 systems incl. Llama evidence (6 triples, b=c=0, Holm 1)",
      len(fi) == 8 and fi["llama3.1:8b|evidence"]["n_pairs"] == 6 and fi["llama3.1:8b|evidence"]["b_only_x"] == 0
      and fi["llama3.1:8b|evidence"]["c_only_y"] == 0 and fi["llama3.1:8b|evidence"]["holm_p_family_F_I"] == 1.0)

# ---------- A6  valid-only analysis: H1 only, S1 not recomputed ----------
check("valid-only file holds H1 only (no S1)", all(set(pv[s].keys()) == {"transitions_PLC_to_NEU", "valid_only"} for s in LLM4))
check("valid-only pairs 84/73/64/51", [pv[s]["valid_only"]["n_pairs"] for s in LLM4] == [84, 73, 64, 51])
check("valid-only Holm: 3 of 4 significant", sum(pv[s]["valid_only"]["holm_p_posthoc_4"] < 0.05 for s in LLM4) == 3)
check("S4 (84 posts) Holm max 0.020", round(max(cf["systems"][s]["S4_H1_excluding_human_invalid"]["holm_p_F_CF_S4"] for s in LLM4), 3) == 0.02)

# ---------- A7  protocol chronology ----------
import subprocess  # noqa: E402
first = subprocess.run(["git", "log", "--diff-filter=A", "--format=%h %ad", "--date=short", "--", "results/e1_counterfactual/PROTOCOL.md"],
                       capture_output=True, text=True).stdout.split()
check("PROTOCOL.md first committed in c60d6c4 on 2026-11-16", first[:2] == ["c60d6c4", "2026-11-16"], " ".join(first))
check("PROTOCOL.md self-dates 2026-11-10", "fixed before any model call** (2026-11-10)" in open("results/e1_counterfactual/PROTOCOL.md").read())
check("run.log first LLM call 2026-11-10 05:18:30", "[2026-11-10 05:18:30] run qwen2.5:7b direct" in open("results/e1_counterfactual/run.log").read())

# ---------- Part B: manuscript strings ----------
if body is not None:
    flat = re.sub(r"\s+", " ", body)
    must = ["52.7", "40.1", "74.4", "73.6", "42.9", "28.6", "17.0 to 25.0", "CF2", "246 and 76", "50.2", "68.3",
            "6.1--10.6", "PROTOCOL.md", "c60d6c4", "posts entering each contrast", "Acknowledgment"]
    for m in must:
        check(f"body contains '{m}'", m in flat)
    retired = ["stay violating far more often", "stratum-weighted estimates: Table", "so the decision rule still holds",
               "Llama 3.1 is not compared on accuracy", "17.1 to 25.0", "keeps the flag for 84.1", "fixed before data collection",
               "All columns use the 600 original posts as denominator", "including I1 and I3, are exploratory",
               "retention of violating verdicts after erasure to", "the retention of a violating verdict is the main",
               "a cue it should not need", "by a rule fixed in advance", "(Fig. 3, Table 5)"]
    for r in retired:
        check(f"body no longer contains '{r}'", r not in flat)
    check("author placeholders resolved (ethics, acknowledgment, commit hash)", "to be stated by the authors" not in flat and "PENULIS" not in flat and "HASH RILIS" not in flat)

print("FAILS:", fails)
sys.exit(1 if fails else 0)
