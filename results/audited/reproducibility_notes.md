# Reproducibility Notes — Moderation Study Kit (llm600 audit)

Written in English for use as supplementary material. Companion to `audit_report.md`.

## 1. Re-running the audit (no model calls)

```bash
python3 -m venv ~/.venvs/modkit        # keep the venv OUTSIDE iCloud-synced folders (see §6)
~/.venvs/modkit/bin/pip install numpy==2.5.4 pandas==3.1.1 scipy==1.18.1 scikit-learn==1.9.1 \
    statsmodels==0.15.0 openpyxl==3.1.5 requests==2.34.2 matplotlib==3.11.2
cd Moderation_Study_Kit
~/.venvs/modkit/bin/python -m unittest discover -s tests -v   # 25 tests: classifier units + invariants on runs/
~/.venvs/modkit/bin/python audit_metrics.py                   # ~20 s, writes results/audited/*
```

Inputs, all read-only:
- `items_llm600.jsonl`
- `runs/*.jsonl`
- `human_validation_filled.xlsx` (read via `hitl_sheet.read`)
- `human_validation_r2_groups.json`
- `data/dataset.json`
- `results/_sebelum_refusal/revised_llm600.json` (used only for the before/after table)
- `validation.json` (used only for the before/after table)

Randomness: bootstrap seed 42. B = 2000 for pooled and kappa intervals, B = 5000 for paired tests.

## 2. Outputs (`results/audited/`)

| File | Content |
|---|---|
| `response_classification.json` | Per-system category counts (total and per MR), SHA-1 of every run file, one record per (system, item): category, verdict used, recovered verdict, stored run-time verdict, `raw_sha1` (first 12 hex digits of SHA-1 of the raw text). |
| `manual_review_queue.csv` | 23 responses flagged as ambiguous, with raw excerpts. |
| `audited_metrics.csv` | System × MR (and ALL): n per category, coverage, rates, conditional accuracies, CIs, flip rates. |
| `model_comparison.csv` | One row per system with headline metrics. |
| `oracle_validity_analysis.csv` | Oracle validity per MR/stratum, and per system: A (original oracle, all items), B (validated subset, original oracle), C (validated subset, corrected oracle), D (population estimate), E (contamination bounds). |
| `statistical_analysis.json` | Units of analysis, test families, transition matrices, McNemar/Holm results, I3 analysis, agreement, residual-identity analysis, model metadata. |
| `before_after.csv` | Initial vs audited value per finding and system. |

### Metric definitions (denominator = all items of the MR for that system unless stated)

| Metric | Definition |
|---|---|
| coverage_valid | VALID_VERDICT / total |
| answered_rate | (VALID_VERDICT + ABSTENTION) / total |
| refusal_rate, abstention_rate, unparseable_rate, generation_error_rate, empty_rate | category / total |
| cond_acc_valid | correct VALID_VERDICT / VALID_VERDICT. For R1, where the only correct answer is `insufficient`, this is 0 by definition; use `cond_acc_answered` or the R1 abstention share. |
| cond_acc_answered | correct answered / answered |
| overall_acc_nonanswer_wrong | correct answered / total. Equals the original EV1 accuracy (verified for all 8 systems). |
| flip_rate_vs_own_orig (I1, I2, I3) | verdict ≠ same system's ORIG verdict, among pairs where both are answered |

### Unit of analysis

Every MR has at most one item per post; `audit_metrics.py` asserts this. Per-MR rates therefore use Wilson intervals. Pooled ALL rows and kappa use a cluster bootstrap over posts.

### Test families (Holm correction within each)

| Family | Tests |
|---|---|
| F_I | I1 vs I2 flip, 8 systems |
| F_P | evidence vs direct on ORIG, 3 models |
| F_B | each LLM condition vs word-LR on ORIG, 6 tests |
| F_R | E1 residual-identity Fisher tests, 8 systems |

Each family is computed for each analysis variant, for example all posts vs posts answered in both conditions.

## 3. Experimental configuration (as run, 2026-11-09 to 2026-11-10)

### Hardware and software
- **Hardware:** Apple M3 Pro, 18 GB unified memory, macOS 27.2 (26B123).
- **Python:** 3.14.7. Runs used the project venv at the time; the audit used `~/.venvs/modkit` with the versions in §1.
- **Ollama:** 0.33.3, OpenAI-compatible endpoint `http://localhost:11434/v1`.

### Models (local tags and digests)

| Tag | Digest |
|---|---|
| qwen2.5:7b | `845dbda0ea48` |
| llama3.1:8b | `46e0c10c039e` |
| gemma2:9b | `ff02c3702f32` |

Default Ollama quantisation for each tag.

### Decoding
- temperature 0.0, seed 42, single user message, no system prompt.
- `max_tokens` 256 for all runs launched after the refactor (see A8 below).

### Prompts
`run_llm.py: p_direct`, `p_evidence`. These are byte-identical to the original kit (AST comparison against `Moderation_Study_Kit.zip` and git commit `d79b9a2`).

### Server configuration (non-uniform — threat A8)

| Run segment | Mode | Context | max_tokens |
|---|---|---|---|
| qwen2.5 direct, first 822 items | sequential, default server | 4096 | none |
| qwen2.5 direct (rest) and the other 5 runs | `OLLAMA_NUM_PARALLEL=6`, `--workers 6`, `OLLAMA_KEEP_ALIVE=30m` | 1024 | 256 |

A 150-item check gave identical verdicts sequential vs 1/4/6/8 parallel slots for qwen2.5. This was not checked for the other models.

### Run timeline (`logs/run_all.log`, start times, UTC+7)

| Run | Start |
|---|---|
| qwen2.5 direct | 2026-11-09 12:34, restarted 13:19 |
| qwen2.5 evidence | 14:40 |
| llama3.1 direct | 16:28 |
| llama3.1 evidence | 17:51 |
| gemma2 direct | 19:07 |
| gemma2 evidence | 22:24, finished ≈ 04:24 on 2026-11-10 |

### I3 construction
- **Paraphraser:** gemma2:9b at temperature 0.3, using the research-context prompt `run_llm.py: PARA`.
- **Judge:** qwen2.5:7b, prompt `EQUIV`, applied in both directions; `auto_valid` = both say "same".
- **Filter:** refusals, chat preambles, outputs under 40% of the original length, and censored slurs (`CENSORED` regex) are set to `text=None`, `refused=True`. Result: 98 of 600 items.
- **History:** a first attempt with llama3.1:8b produced 600/600 refusals and was discarded; the file is kept in `backup_20261109/bad_paraphrase/`. In the final paraphrase run the first 100 paraphrases were generated before the censorship filter existed, but every item was screened by the filter in the judge phase, so all 600 had the same screening.

### Data
- HateXplain was cloned with `--depth 1` from `github.com/hate-alert/HateXplain` on 2026-10-17. **The commit hash was not recorded.**
- SHA-1 values:

| File | SHA-1 |
|---|---|
| `data/dataset.json` | `d090baf2699c5ad488ccea7fd620db7fe1634d6b` |
| `data/post_id_divisions.json` | `8b5955029f7eda4835b83eea41a434d7dd5e959f` |
| `items_llm600.jsonl` (with I3 paraphrases) | `616319586f7809cd62d50121dc5a36be4ab8cb74` |
| `items_llm600.orig.jsonl` (kit original) | `890b094c22db048411de7dece5c1b8b8563fa603` |
| `human_validation_filled.xlsx` | `3c3e593d659c81fa4a93fcf465f4c3a355c17dbe` |

### Not recorded per response
Call timestamps, latency, `finish_reason`, server configuration, model digest, and call errors. `call()` retries 4 times and then aborts the run, so call errors leave no record (threat A9).

## 4. Code change log (relative to the kit as received)

| Date | File | Change | Affects main results? |
|---|---|---|---|
| 10-17 | `hitl_sheet.py` (new), `run_llm.py export/score` | Human-validation workbook; score reads typed cells | No (validation only) |
| 11-09 | `hitl_sheet.py`, `run_llm.py export` | Added E2 sample and R2 ambiguous/control strata; later simplified to Ya/Tidak dropdowns with locked cells | No |
| 11-09 | `run_llm.py paraphrase` | Atomic checkpoints every 25 items; two phases (paraphrase, then judge); research-context `PARA` prompt; refusal/censorship filter | **Yes, I3 construction** |
| 11-09 | `run_llm.py run`, `call()` | `--workers` (thread pool; order-preserving writes), `--max-tokens` (default 256) | Inference config (A8) |
| 11-09 | `run_all.sh` (new) | Orchestrates paraphrase → export → baselines → 6 runs → evaluation | — |
| 11-09 | `revise_eval.py`, `figs.py`, `results/revised_*.json` | Copied unchanged from the updated kit zip; `fig/` regenerated from `results/revised_full.json` (baselines only) | — |
| 11-10 | `run_llm.py parse()` | Refusals → verdict `refused` (after all runs; affects only re-parsing) | No (runs unchanged) |
| 11-10 | `relabel_refusals.py` (new) → `runs_rl/`, `results/refusal_rates.json` | Re-labels refusals in copies of the runs. Its regex counts 3 llama3.1 abstentions as refusals; **superseded by `response_classifier.py`**. | `results/*.json` outside `audited/` |
| 11-10 | `evaluate.py` | Invariance pass requires verdict ≠ `refused` | `results/llm600*.json` |
| 11-10 | `revise_eval.py` | Invariance and flip treat `refused` as not holding the verdict. A bug from this edit (commented-out `pairs.append`) was found and fixed the same day. | `results/revised_llm600.json` |
| 11-10 | `response_classifier.py`, `audit_metrics.py`, `tests/` (new) | Audited classification and metrics | `results/audited/` (canonical) |

Backups:
- `backup_20261109/`: pre-parallel `run_llm.py`, pre-simplification workbook and `hitl_sheet.py`, discarded llama3.1 paraphrase run.
- `backup_20261110/`: `evaluate.py`, `revise_eval.py`, `run_llm.py` before the refusal patches.
- `results/_sebelum_refusal/`: results before refusal handling.

## 5. Traceability

Every audited number can be traced back as follows:
1. `audited_metrics.csv` row → (system, MR).
2. `response_classification.json → records` gives each item's category, verdict, and `raw_sha1`.
3. The raw line is found in `runs/<file>.jsonl` by `item_id`.
4. The classification can be re-derived with `response_classifier.classify(raw)`.

Before/after values come from `results/_sebelum_refusal/revised_llm600.json` and `validation.json`.

## 6. Known environment pitfall

The project lives in an iCloud-synced `~/Documents` folder on a nearly full disk. macOS evicted about half of the old in-project `.venv` (files marked `dataless`), and Python imports hung waiting for downloads. Keep the venv outside synced folders, or disable "Optimize Mac Storage". Before re-running, check that the data files are fully local:

```bash
find . -flags +dataless
```

## 7. Open items

- I3 item `34250a0a4de0` (sheet `Keputusan`, row 259) awaits adjudication. It is excluded from analyses needing a final label; its effect on I3 invariance is ≤ 1.1 pt (`statistical_analysis.json → pending_item_sensitivity`). Re-run `audit_metrics.py` after it is filled.
- Rater identity, background, independence, and adjudicator: not documented.
- HateXplain commit hash: not recorded.

## 8. E1 counterfactual experiment (added 2026-11-10)

Files in `results/e1_counterfactual/`:

| File | Content |
|---|---|
| `PROTOCOL.md` | hypotheses, conditions, decision rule, deviations (fixed before data collection) |
| `items_e1cf.jsonl` | 440 items = 88 posts × 5 conditions, built by `build_e1_counterfactual.py` |
| `runs/` | raw responses (same configuration as the main runs) |
| `run_e1cf.sh`, `run.log` | run script and log |
| `analysis.json`, `summary.csv`, `RESULTS.md` | `analyze_e1_counterfactual.py` output |

Re-run the analysis: `~/.venvs/modkit/bin/python analyze_e1_counterfactual.py`. One server restart occurred during the last run (documented in `PROTOCOL.md §8`).
