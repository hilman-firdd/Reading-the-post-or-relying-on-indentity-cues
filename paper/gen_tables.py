"""Generate LaTeX table bodies from the audited result files (no hand-typed numbers).
Usage: python3 gen_tables.py <repo_dir> <out_dir>
"""
import csv, json, sys, os
from scipy.stats.contingency import odds_ratio as _scipy_or

repo, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
A = f"{repo}/results/audited"
sa = json.load(open(f"{A}/statistical_analysis.json"))
cf = json.load(open(f"{repo}/results/e1_counterfactual/analysis.json"))
mc = {r["system"]: r for r in csv.DictReader(open(f"{A}/model_comparison.csv"))}
ov = list(csv.DictReader(open(f"{A}/oracle_validity_analysis.csv")))

SYS = ["qwen2.5:7b|direct", "qwen2.5:7b|evidence", "gemma2:9b|direct", "gemma2:9b|evidence",
       "llama3.1:8b|direct", "llama3.1:8b|evidence", "word-LR", "char-LR"]
LAB = {"qwen2.5:7b|direct": "Qwen2.5 / direct", "qwen2.5:7b|evidence": "Qwen2.5 / evidence",
       "gemma2:9b|direct": "Gemma 2 / direct", "gemma2:9b|evidence": "Gemma 2 / evidence",
       "llama3.1:8b|direct": "Llama 3.1 / direct", "llama3.1:8b|evidence": "Llama 3.1 / evidence",
       "word-LR": "word-LR", "char-LR": "char-LR"}
MINUS = "$-$"


def f(x, nd=1):
    return "--" if x in ("", None) else f"{float(x):.{nd}f}"


def pct(x, nd=1):
    return "--" if x in ("", None) else f"{100*float(x):.{nd}f}"


def sgn(x, nd=1):
    v = 100 * float(x)
    s = f"{abs(v):.{nd}f}"
    return ("+" if v > 0 else (MINUS if v < 0 else "")) + s


def pv(p):
    if p is None or p == "":
        return "--"
    p = float(p)
    return "$<$0.001" if p < 0.001 else f"{p:.3f}"


def ci(lo, hi, nd=1, signed=False):
    g = sgn if signed else pct
    return f"[{g(lo, nd)}, {g(hi, nd)}]"


def parse_ci(s):
    s = s.strip("[]").split(",")
    return float(s[0]), float(s[1])


def write(name, rows):
    open(f"{out}/{name}.tex", "w").write("\n".join(rows) + "\n")


# ---- Table: coverage and accuracy on original posts ----
rows = []
rc = json.load(open(f"{A}/response_classification.json"))["summary_by_mr"]
for s in SYS:
    r = mc[s]
    lo, hi = parse_ci(r["ORIG_cond_acc_valid_ci95"])
    # refusal/abstention are shares of the 600 ORIG posts, the same denominator as coverage and accuracy
    o = rc[s]["ORIG"]; n_o = sum(o.values())
    ref = "--" if s.endswith("LR") else f"{100*o.get('REFUSAL',0)/n_o:.1f}"
    ab = "--" if s.endswith("LR") else f"{100*o.get('ABSTENTION',0)/n_o:.1f}"
    assert n_o == 600
    rows.append(f"{LAB[s]} & {pct(r['ORIG_coverage_valid'])} & {pct(r['ORIG_cond_acc_valid'])} {ci(lo, hi)} & "
                f"{pct(r['ORIG_overall_acc_nonanswer_wrong'])} & {ref} & {ab} \\\\")
    if s == "llama3.1:8b|evidence":
        rows.append("\\midrule")
write("tab_cov_body", rows)

# ---- Table: E1 transitions and residual identity ----
rows = []
for s in SYS:
    e1 = sa["behaviour_E_R"][s]["E1"]
    t = e1["transition_orig_to_E1"]
    n = e1["n_orig_violating_and_E1_answered"]
    keep = t.get("violating->violating", 0) / n
    nv = t.get("violating->not_violating", 0) / n
    ins = t.get("violating->insufficient", 0) / n
    r = sa["E1_residual_identity_terms"]["by_system"][s]["all_answered"]
    ins_s = "--" if s.endswith("LR") else pct(ins)
    # exact conditional (Fisher) 95% CI of the odds ratio, recomputed from the 2x2 counts of the audit (flagged / answered, with vs without identity term)
    k1, n1 = r["flagged_with_identity"][1:3]; k2, n2 = r["flagged_without_identity"][1:3]
    ci_or = _scipy_or([[k1, n1 - k1], [k2, n2 - k2]], kind="conditional").confidence_interval(0.95)
    assert abs((k1 * (n2 - k2)) / ((n1 - k1) * k2) - r["odds_ratio"]) < 0.005   # the audit OR is the sample odds ratio
    rows.append(f"{LAB[s]} & {n} & {pct(keep)} & {pct(nv)} & {ins_s} & {r['odds_ratio']:.1f} [{ci_or.low:.1f}, {ci_or.high:.1f}] & {pv(r['holm_p_family_F_R'])} \\\\")
    if s == "llama3.1:8b|evidence":
        rows.append("\\midrule")
write("tab_e1_body", rows)

# ---- Table: counterfactual ----
rows = []
for s in SYS:
    d = cf["systems"][s]
    h, s1 = d["H1_PLC_minus_NEU"], d["S1_PLCDEL_minus_DEL"]
    hp = h.get("holm_p_F_CF")
    sp = s1.get("holm_p_F_CF2")
    hps = pv(hp) if not s.endswith("LR") else "--"
    sps = pv(sp) if not s.endswith("LR") else "--"
    lo, hi = h["rd_ci95_post_bootstrap"]
    lo2, hi2 = s1["rd_ci95_post_bootstrap"]
    rows.append(f"{LAB[s]} & {h['n_pairs']} & {pct(h['rate_x'])} & {pct(h['rate_y'])} & {sgn(h['risk_difference'])} {ci(lo, hi, signed=True)} & "
                f"{h['b_only_x']}/{h['c_only_y']} & {hps} & {sgn(s1['risk_difference'])} {ci(lo2, hi2, signed=True)} & {sps} \\\\")
    if s in ("gemma2:9b|evidence", "llama3.1:8b|evidence"):
        rows.append("\\midrule")
write("tab_cf_body", rows)

# ---- Table: oracle validity ----
ag = sa["human_validation"]["agreement"]
def kap(k):
    lo_, hi_ = ag[k]["kappa_ci95_post_bootstrap"]
    return f"{ag[k]['cohen_kappa']:.2f} [{lo_:.2f}, {hi_:.2f}]"
rows = []
lab = {("E1", "all"): ("E1 erase rationale", "E1"), ("E2", "all"): ("E2 insert rationale", "E2"),
       ("R2", "offensive_ambiguous"): ("R2 offensive, ambiguous", "R2"),
       ("R2", "offensive_control"): ("R2 offensive, control", "R2"),
       ("R2", "offensive (stratum-weighted)"): ("R2 offensive, weighted", "R2"),
       ("I1", "all"): ("I1 identity swap", "I1"), ("I3", "all"): ("I3 paraphrase", "I3")}
design = {("R2", "offensive_ambiguous"): "census", ("R2", "offensive_control"): "20\\%", ("R2", "offensive (stratum-weighted)"): "weighted"}
for r in ov:
    if r["row_type"] != "oracle_validity":
        continue
    key = (r["mr"], r["stratum"])
    if key not in lab:
        continue
    lo, hi = parse_ci(r["validity_ci95"])
    name, k = lab[key]
    kk = kap(k) if key in (("E1", "all"), ("E2", "all"), ("I1", "all"), ("I3", "all")) else "--"
    rows.append(f"{name} & {r['population_N']} & {r['sampled_n']} & {pct(r['validity'])} {ci(lo, hi)} & {kk} \\\\")
rows.append(f"R2 offensive, pooled agreement & 200 & {ag['R2']['n']} & -- & {ag['R2']['cohen_kappa']:.2f} [{ag['R2']['kappa_ci95_post_bootstrap'][0]:.2f}, {ag['R2']['kappa_ci95_post_bootstrap'][1]:.2f}] \\\\")
rows.append("R2 hate speech, normal & 400 & 0 & not validated & -- \\\\")
write("tab_oracle_body", rows)

# ---- Table: policy axis and invariance ----
ovs = {}
for r in ov:
    if r["row_type"] == "model_sensitivity" and r["mr"] == "R2":
        ovs[(r["system"], r["stratum"])] = r
rows = []
for s in SYS:
    r = mc[s]
    lr = s.endswith("LR")
    r1 = "--" if lr else pct(r["R1_abstained_among_answered"], 0)
    r2o = pct(r["R2_pass_label_changes_ambiguous"], 0)
    r2c = pct(ovs[(s, "offensive_ambiguous")]["C_validated_corrected_oracle"], 0)
    r2w = pct(ovs[(s, "offensive (stratum-weighted)")]["D_population_estimate_corrected"], 0)
    r3 = pct(r["R3_verdict_changed"], 0)
    lo, hi = parse_ci(r["I1_minus_I2_ci95"])
    dd = f"{sgn(r['I1_minus_I2'])} {ci(lo, hi, signed=True)}"
    hp = pv(r["I1_vs_I2_p_holm"])
    if s == "llama3.1:8b|evidence":
        dd, hp = "n/a", "n/a"
        i1, i2 = "--", "--"
    else:
        i1, i2 = pct(r["I1_flip"]), pct(r["I2_flip"])
    rows.append(f"{LAB[s]} & {r1} & {r2o} & {r2c} & {r2w} & {r3} & {r['I1_I2_complete_triples'] if 'I1_I2_complete_triples' in r else r['I1I2_complete_triples']} & {i1} & {i2} & {dd} & {hp} \\\\")
    if s == "llama3.1:8b|evidence":
        rows.append("\\midrule")
write("tab_pol_body", rows)
print("tables written to", out)
