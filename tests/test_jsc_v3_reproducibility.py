"""Small pytest checks for the JSC v3 reproduction additions (post hoc E1-CF analyses and the ORIG_* audit columns).

  PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider tests/test_jsc_v3_reproducibility.py

Read-only: reads result files and recomputes small quantities from the raw runs; writes only to pytest's tmp_path.
"""
import csv, json, os, subprocess, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CF = ROOT / "results" / "e1_counterfactual"
AUD = ROOT / "results" / "audited"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))

LLM4 = {"qwen2.5:7b|direct": "qwen2.5_7b_direct", "qwen2.5:7b|evidence": "qwen2.5_7b_evidence",
        "gemma2:9b|direct": "gemma2_9b_direct", "gemma2:9b|evidence": "gemma2_9b_evidence"}
CORE, EXT = {"black", "white", "man"}, {"black", "blacks", "white", "whites", "man", "men"}


def _post_tokens():
    out = {}
    for line in open(CF / "items_e1cf.jsonl"):
        it = json.loads(line)
        out[it["e1_item_id"]] = tuple(it["cf_meta"]["identity_tokens"])
    return out


# ------------------------------------------------------------------ 25 / 33 ambiguous posts
def test_88_posts_and_25_core_ambiguous_posts():
    tok = _post_tokens()
    assert len(tok) == 88
    core = [p for p, t in tok.items() if t and set(t) <= CORE]
    assert len(core) == 25
    assert len(tok) - len(core) == 63


def test_33_extended_ambiguous_posts_include_the_core_set():
    tok = _post_tokens()
    core = {p for p, t in tok.items() if t and set(t) <= CORE}
    ext = {p for p, t in tok.items() if t and set(t) <= EXT}
    assert len(ext) == 33 and core <= ext


def test_every_post_has_identity_tokens_and_the_same_in_all_conditions():
    seen = {}
    for line in open(CF / "items_e1cf.jsonl"):
        it = json.loads(line)
        seen.setdefault(it["e1_item_id"], set()).add(tuple(it["cf_meta"]["identity_tokens"]))
    assert all(len(v) == 1 and list(v)[0] for v in seen.values())


# ------------------------------------------------------------------ post hoc: valid-verdict-only
def test_posthoc_valid_only_n_pairs_and_effects():
    r = json.load(open(CF / "posthoc_valid_only.json"))
    n = {s: r[s]["valid_only"]["n_pairs"] for s in LLM4}
    assert n == {"qwen2.5:7b|direct": 84, "qwen2.5:7b|evidence": 73, "gemma2:9b|direct": 64, "gemma2:9b|evidence": 51}
    rd = {s: round(100 * r[s]["valid_only"]["risk_difference"], 1) for s in LLM4}
    assert rd == {"qwen2.5:7b|direct": 22.6, "qwen2.5:7b|evidence": 16.4, "gemma2:9b|direct": 18.8, "gemma2:9b|evidence": 2.0}
    holm = {s: r[s]["valid_only"]["holm_p_posthoc_4"] for s in LLM4}
    assert round(holm["qwen2.5:7b|evidence"], 3) == 0.034 and round(holm["gemma2:9b|direct"], 3) == 0.001 and holm["gemma2:9b|evidence"] == 1.0


def test_posthoc_valid_only_n_pairs_recomputed_independently_from_the_raw_runs():
    from response_classifier import classify_record
    cf = {}
    for line in open(CF / "items_e1cf.jsonl"):
        it = json.loads(line)
        cf[it["item_id"]] = (it["e1_item_id"], it["cf_condition"])
    expected = json.load(open(CF / "posthoc_valid_only.json"))
    for s, fn in LLM4.items():
        valid = {}
        for line in open(CF / "runs" / f"{fn}.jsonl"):
            rec = json.loads(line)
            post, cond = cf[rec["item_id"]]
            valid.setdefault(post, {})[cond] = classify_record(rec)["category"] == "VALID_VERDICT"
        assert sum(1 for v in valid.values() if v["PLC"] and v["NEU"]) == expected[s]["valid_only"]["n_pairs"], s


def test_gemma2_evidence_lost_flags_are_mostly_abstentions():
    t = json.load(open(CF / "posthoc_valid_only.json"))["gemma2:9b|evidence"]["transitions_PLC_to_NEU"]
    lost_to_abstention, lost_to_not_violating = t["violating->ABSTENTION"], t["violating->not_violating"]
    assert (lost_to_abstention, lost_to_not_violating) == (17, 1)       # 17 of the 18 posts that lose the flag


# ------------------------------------------------------------------ post hoc: ambiguous tokens
def test_posthoc_ambiguous_tokens_json_structure():
    r = json.load(open(CF / "posthoc_ambiguous_tokens.json"))
    assert r["sets"]["core"]["n_posts_all_tokens_ambiguous"] == 25 and r["sets"]["core"]["n_posts_remaining"] == 63
    assert r["sets"]["extended"]["n_posts_all_tokens_ambiguous"] == 33 and r["sets"]["extended"]["n_posts_remaining"] == 55
    assert all(r["sanity_full_88_equals_analysis_json"].values()) and len(r["sanity_full_88_equals_analysis_json"]) == 8
    for name, remaining in (("core_excluded", 63), ("extended_excluded", 55)):
        for key in ("H1_PLC_minus_NEU", "S1_PLCDEL_minus_DEL"):
            assert set(r["results"][name][key]) == set(LLM4)
            assert all(v["n_pairs"] <= remaining for v in r["results"][name][key].values())


def test_posthoc_ambiguous_tokens_excluded_posts_match_the_rule():
    r = json.load(open(CF / "posthoc_ambiguous_tokens.json")); tok = _post_tokens()
    assert set(r["sets"]["core"]["excluded_e1_item_ids"]) == {p for p, t in tok.items() if t and set(t) <= CORE}
    assert set(r["sets"]["extended"]["excluded_e1_item_ids"]) == {p for p, t in tok.items() if t and set(t) <= EXT}


# ------------------------------------------------------------------ ORIG_* columns
def _mc():
    return {r["system"]: r for r in csv.DictReader(open(AUD / "model_comparison.csv"))}


def _orig_rows():
    return {r["system"]: r for r in csv.DictReader(open(AUD / "audited_metrics.csv")) if r["mr"] == "ORIG"}


def test_new_columns_are_appended_after_the_old_ones():
    cols = list(csv.reader(open(AUD / "model_comparison.csv")))[0]
    assert cols[-2:] == ["ORIG_refusal_rate", "ORIG_abstention_rate"] and len(cols) == 39


def test_orig_columns_use_the_600_posts_denominator_and_expected_values():
    mc, om = _mc(), _orig_rows()
    for s, row in mc.items():
        assert int(om[s]["n_total"]) == 600
        assert abs(float(row["ORIG_refusal_rate"]) * 600 - int(om[s]["n_refusal"])) < 0.5
        assert abs(float(row["ORIG_abstention_rate"]) * 600 - int(om[s]["n_abstention"])) < 0.5
    pct = lambda s, c: round(100 * float(mc[s][c]), 1)
    assert pct("llama3.1:8b|direct", "ORIG_refusal_rate") == 59.0
    assert pct("llama3.1:8b|evidence", "ORIG_refusal_rate") == 87.3
    assert pct("gemma2:9b|evidence", "ORIG_abstention_rate") == 6.2


def test_orig_shares_sum_to_100_percent_with_coverage_and_the_remaining_categories():
    mc, om = _mc(), _orig_rows()
    for s, row in mc.items():
        total = (float(row["ORIG_coverage_valid"]) + float(row["ORIG_refusal_rate"]) + float(row["ORIG_abstention_rate"])
                 + float(om[s]["unparseable_rate"]) + float(om[s]["generation_error_rate"]) + float(om[s]["empty_rate"]))
        assert abs(total - 1.0) < 1e-3, (s, total)


def test_coverage_refusal_abstention_alone_fall_short_only_by_the_unparseable_share():
    mc, om = _mc(), _orig_rows()
    for s, row in mc.items():
        three = float(row["ORIG_coverage_valid"]) + float(row["ORIG_refusal_rate"]) + float(row["ORIG_abstention_rate"])
        assert abs((1.0 - three) - float(om[s]["unparseable_rate"])) < 1e-3, s


def test_orig_columns_match_the_manuscript_table_generated_by_paper_gen_tables(tmp_path):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    subprocess.run([sys.executable, str(ROOT / "paper" / "gen_tables.py"), str(ROOT), str(tmp_path)], check=True, env=env, capture_output=True)
    rows = [l for l in open(tmp_path / "tab_cov_body.tex").read().splitlines() if l.strip() and not l.startswith("\\midrule")]
    mc = _mc()
    order = ["qwen2.5:7b|direct", "qwen2.5:7b|evidence", "gemma2:9b|direct", "gemma2:9b|evidence", "llama3.1:8b|direct", "llama3.1:8b|evidence", "word-LR", "char-LR"]
    assert len(rows) == 8
    for s, line in zip(order, rows):
        cells = [c.strip().rstrip("\\").strip() for c in line.split("&")]
        ref, ab = cells[4], cells[5]
        if s.endswith("LR"):
            assert (ref, ab) == ("--", "--")
        else:
            assert ref == f"{100 * float(mc[s]['ORIG_refusal_rate']):.1f}" and ab == f"{100 * float(mc[s]['ORIG_abstention_rate']):.1f}", s


# ------------------------------------------------------------------ v5 tables: odds-ratio CI (E1) and kappa CI (oracle)
import re


@pytest.fixture(scope="module")
def v5_tables(tmp_path_factory):
    out = tmp_path_factory.mktemp("tabs")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    subprocess.run([sys.executable, str(ROOT / "paper" / "gen_tables.py"), str(ROOT), str(out)], check=True, env=env, capture_output=True)
    return out


E1_ROWS = ["qwen2.5:7b|direct", "qwen2.5:7b|evidence", "gemma2:9b|direct", "gemma2:9b|evidence",
           "llama3.1:8b|direct", "llama3.1:8b|evidence", "word-LR", "char-LR"]
OR_CELL = re.compile(r"^([\d.]+) \[([\d.]+), ([\d.]+)\]$")


def _e1_or_cells(tabs):
    rows = [l for l in open(tabs / "tab_e1_body.tex").read().splitlines() if l.strip() and not l.startswith("\\midrule")]
    assert len(rows) == 8
    out = {}
    for s, line in zip(E1_ROWS, rows):
        cells = [c.strip().rstrip("\\").strip() for c in line.split("&")]
        cell = cells[11]         # v27: cols 5-8 retention 2x2 + post hoc OR + Holm (F_RET), cols 9-10 association 2x2, col 11 association OR
        m = OR_CELL.match(cell)
        assert m, (s, cell)
        out[s] = tuple(float(x) for x in m.groups())
    return out


def _scipy_or_from_audit(system):
    """Odds ratio and exact conditional 95% CI computed directly from the 2x2 counts stored in statistical_analysis.json."""
    from scipy.stats.contingency import odds_ratio
    a = json.load(open(AUD / "statistical_analysis.json"))["E1_residual_identity_terms"]["by_system"][system]["all_answered"]
    k1, n1 = a["flagged_with_identity"][1:3]
    k2, n2 = a["flagged_without_identity"][1:3]
    ci = odds_ratio([[k1, n1 - k1], [k2, n2 - k2]], kind="conditional").confidence_interval(0.95)
    sample_or = (k1 * (n2 - k2)) / ((n1 - k1) * k2)
    return sample_or, ci.low, ci.high, (k1, n1, k2, n2)


@pytest.mark.parametrize("system", ["gemma2:9b|direct", "word-LR"])
def test_e1_table_odds_ratio_ci_matches_scipy_from_the_2x2_counts(v5_tables, system):
    sample_or, lo, hi, counts = _scipy_or_from_audit(system)
    got_or, got_lo, got_hi = _e1_or_cells(v5_tables)[system]
    assert (round(sample_or, 1), round(lo, 1), round(hi, 1)) == (got_or, got_lo, got_hi), (system, counts)
    assert lo < sample_or < hi                                   # the point estimate lies inside the exact interval


def test_e1_table_contains_the_expected_cells(v5_tables):
    text = open(v5_tables / "tab_e1_body.tex").read()
    for expected in ("3.1 [1.8, 5.2]", "8.8 [4.6, 17.6]", "3.5 [1.1, 11.6]", "1.2 [0.7, 1.9]"):
        assert expected in text, expected


def test_e1_table_prints_the_2x2_counts_behind_each_odds_ratio(v5_tables):
    """v25 (audit #9): the OR population (all answered E1 posts) must show its 2x2 counts, separate from the retention block."""
    rows = [l for l in open(v5_tables / "tab_e1_body.tex").read().splitlines() if l.strip() and not l.startswith("\\midrule")]
    audit = json.load(open(AUD / "statistical_analysis.json"))["E1_residual_identity_terms"]["by_system"]
    for s, line in zip(E1_ROWS, rows):
        cells = [c.strip().rstrip("\\").strip() for c in line.split("&")]
        a = audit[s]["all_answered"]
        assert cells[9] == f"{a['flagged_with_identity'][1]}/{a['flagged_with_identity'][2]}", s
        assert cells[10] == f"{a['flagged_without_identity'][1]}/{a['flagged_without_identity'][2]}", s


def test_e1_table_prints_the_retention_2x2_and_its_post_hoc_or(v5_tables):
    """v26 (audit #10): the retention block shows kept/n with and without an identity term; n adds up to the transition n."""
    ret = json.load(open(ROOT / "results" / "posthoc_e1_retention.json"))["by_system"]
    rows = [l for l in open(v5_tables / "tab_e1_body.tex").read().splitlines() if l.strip() and not l.startswith("\\midrule")]
    for s, line in zip(E1_ROWS, rows):
        cells = [c.strip().rstrip("\\").strip() for c in line.split("&")]
        a1, m1 = ret[s]["kept_with_identity"]; a0, m0 = ret[s]["kept_without_identity"]
        assert cells[5] == f"{a1}/{m1}" and cells[6] == f"{a0}/{m0}", s
        assert int(cells[1]) == m1 + m0, s
        assert cells[7].startswith(f"{ret[s]['odds_ratio_sample']:.1f} ["), s
        hp = ret[s]["holm_p_posthoc_8"]                       # v27: Holm over the 8 retention tests (family F_RET)
        assert cells[8] == ("$<$0.001" if hp < 0.001 else f"{hp:.3f}"), s


def test_retention_holm_is_a_separate_family_of_eight_fisher_tests():
    """v27 (audit #11): recompute Holm over the 8 retention Fisher p values and compare with the stored values."""
    ret = json.load(open(ROOT / "results" / "posthoc_e1_retention.json"))["by_system"]
    assert len(ret) == 8
    order = sorted(ret, key=lambda k: ret[k]["fisher_p"]); run = 0.0
    for i, k in enumerate(order):
        run = max(run, min(1.0, (8 - i) * ret[k]["fisher_p"]))
        assert abs(run - ret[k]["holm_p_posthoc_8"]) < 1e-12, k


def test_cf_table_reports_separate_h1_and_s1_denominators(v5_tables):
    """v25 (audit #9): Llama 3.1 direct has 52 H1 pairs but 47 S1 pairs; RD is (b - c) / n from raw counts."""
    rows = [l for l in open(v5_tables / "tab_cf_body.tex").read().splitlines() if l.strip() and not l.startswith("\\midrule")]
    cells = {r.split("&")[0].strip(): [c.strip() for c in r.split("&")] for r in rows}
    assert cells["Llama 3.1 / direct"][1:3] == ["52", "47"]
    assert cells["Llama 3.1 / direct"][5].startswith("+21.2")
    assert cells["Qwen2.5 / evidence"][5].startswith("+17.0")


def test_e1_table_or_matches_the_audit_for_all_eight_systems(v5_tables):
    cells = _e1_or_cells(v5_tables)
    audit = json.load(open(AUD / "statistical_analysis.json"))["E1_residual_identity_terms"]["by_system"]
    for s in E1_ROWS:
        assert cells[s][0] == round(audit[s]["all_answered"]["odds_ratio"], 1), s
        _, lo, hi, _ = _scipy_or_from_audit(s)
        assert (cells[s][1], cells[s][2]) == (round(lo, 1), round(hi, 1)), s


def test_oracle_table_kappa_ci_comes_from_the_audit_bootstrap(v5_tables):
    ag = json.load(open(AUD / "statistical_analysis.json"))["human_validation"]["agreement"]
    text = open(v5_tables / "tab_oracle_body.tex").read()
    assert "0.73 [0.52, 0.89]" in text                           # E1
    for mr, label in (("E1", "E1 erase rationale"), ("E2", "E2 insert rationale"), ("I1", "I1 identity swap"), ("I3", "I3 paraphrase")):
        lo, hi = ag[mr]["kappa_ci95_post_bootstrap"]
        cell = f"{ag[mr]['cohen_kappa']:.2f} [{lo:.2f}, {hi:.2f}]"
        line = next(l for l in text.splitlines() if l.startswith(label))
        assert line.split("&")[-1].strip().rstrip("\\").strip() == cell, (mr, cell)


# ------------------------------------------------------------------ v29 (audit #12): R3 denominators and E1-CF transitions
def test_policy_table_r3_cell_shows_changed_over_answered_pairs(v5_tables):
    sa = json.load(open(AUD / "statistical_analysis.json"))["behaviour_E_R"]
    text = open(v5_tables / "tab_pol_body.tex").read()
    for s, lab in (("qwen2.5:7b|direct", "Qwen2.5 / direct"), ("llama3.1:8b|evidence", "Llama 3.1 / evidence")):
        r3 = sa[s]["R3"]
        line = next(l for l in text.splitlines() if l.startswith(lab))
        assert f"{r3['verdict_changed_vs_orig'][1]}/{r3['n_pairs_answered']} (" in line, s


def test_e1cf_transition_matrix_reproduces_table6_counts(tmp_path):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    out = subprocess.run([sys.executable, str(ROOT / "paper" / "supp_e1cf_transitions.py"), str(ROOT), str(tmp_path)],
                         check=True, env=env, capture_output=True, text=True)   # the script asserts n, b, c against analysis.json
    tr = json.load(open(ROOT / "results" / "e1cf_transitions.json"))["by_system"]
    g = tr["gemma2:9b|evidence"]
    assert (g["b_flag_lost"], g["c_flag_gained"], g["flag_lost_to_insufficient"]) == (18, 2, 17)
    for s, v in tr.items():
        assert sum(v["matrix_PLC_to_NEU"].values()) == 88, s
    # v30b (audit #15): net decomposition and the valid-verdicts-only subset sizes
    assert (g["net_via_insufficient"], g["net_via_not_violating"]) == (15, 1)
    assert [tr[k]["valid_only_pairs"] for k in ("qwen2.5:7b|direct", "qwen2.5:7b|evidence", "gemma2:9b|direct", "gemma2:9b|evidence")] == [84, 73, 64, 51]
