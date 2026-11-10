# paper/ — scripts that regenerate the numbers, tables and figures of the JSC manuscript (v3)

These three scripts are copies of `scripts/` in the manuscript kits: `make_figs.py` from `JSC_v3_kit.zip` (unchanged in v5), `gen_tables.py` from `JSC_v5_kit.zip` (10 Nov 2026), and `verify_numbers.py` from the v3 kit with one changed check (see the last section; the v5 kit contains the same version). They only **read** `results/` (and, for `verify_numbers.py`, a few source files of the repository). They never write inside the repository: every output goes to the directory you pass.

Run from the repository root with the project environment (numpy, scipy, matplotlib; see `results/audited/reproducibility_notes.md` §1):

```bash
export PYTHONDONTWRITEBYTECODE=1
PY=~/.venvs/modkit/bin/python

# 1. LaTeX table bodies (Tables 3, 4, 5, 6, 7 of the manuscript, in this order of appearance)
$PY paper/gen_tables.py . /path/to/out/tabs        # writes tab_cov_body, tab_oracle_body, tab_e1_body, tab_cf_body, tab_pol_body .tex

# 2. Data figures + the redrawn framework figure (png 600 dpi, jpg, eps)
$PY paper/make_figs.py . /path/to/out/figs

# 3. Independent recomputation of the key numbers and comparison with the manuscript text
$PY paper/verify_numbers.py . /path/to/body.tex      # assemble.py must sit in the same folder as body.tex (abstract word count)
```

`body.tex` and `assemble.py` belong to the manuscript sources (kit `scripts/`); they are not stored in this repository.

| Script | Reads | Notes |
|---|---|---|
| `gen_tables.py` | `results/audited/{statistical_analysis.json, response_classification.json, model_comparison.csv, oracle_validity_analysis.csv}`, `results/e1_counterfactual/analysis.json` | no hand-typed numbers. v5 changes two tables: the E1 table (`tab_e1_body`) gives the sample odds ratio with its exact conditional 95% CI (`scipy.stats.contingency.odds_ratio(kind="conditional")` on the 2x2 counts stored in `statistical_analysis.json`; the script asserts that the stored OR is the sample OR), and the oracle table (`tab_oracle_body`) gives Cohen's kappa with its post-cluster bootstrap 95% CI (`kappa_ci95_post_bootstrap`) in place of the number of judged items. With the audit as it stands, the five table bodies are identical to those in the kit. |
| `make_figs.py` | `results/audited/{statistical_analysis.json, response_classification.json}`, `results/e1_counterfactual/analysis.json` | uses the font *Liberation Serif* if installed; otherwise matplotlib falls back to another font (a warning is printed), so figure files differ slightly in size and glyphs from the kit's, with the same data. |
| `verify_numbers.py` | `items_llm600.jsonl`, `results/audited/response_classification.json`, `results/e1_counterfactual/{items_e1cf.jsonl, runs/, analysis.json}`, `build_items.py`, `response_classifier.py`, `body.tex`, `assemble.py` | prints PASS/FAIL per check; exit code 1 if any check fails. |

## `verify_numbers.py`: change to one check

The check "llama direct refusal CI [53.4, 59.0]" used to compute a Wilson interval over the 4,233 items as if they were independent ([54.7, 57.7]), which failed against the manuscript. It now compares the manuscript interval with the audited **post-cluster bootstrap** CI (`ALL_refusal_ci95`, row `llama3.1:8b|direct` of `results/audited/model_comparison.csv`) and also requires the string to be present in `body.tex`. With this change all 12 checks pass against the kit's `body.tex` (10 Nov 2026). This is the only difference from the kit's copy of the script.

## Related, not in this folder

- `results/e1_counterfactual/posthoc_abstention_e1cf.py` and `posthoc_ambiguous_tokens.py`: the two post hoc analyses (valid-verdict-only; ambiguous identity tokens), see `results/e1_counterfactual/PROTOCOL.md` §8.
- `tests/test_jsc_v3_reproducibility.py`: tests for the post hoc results and the added `ORIG_*` columns.
