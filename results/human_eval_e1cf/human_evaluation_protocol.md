# Human Evaluation Protocol — Counterfactual E1 (HE-E1CF)

Status: **PROPOSED (revision R1), not yet in use. No rater has received any material.** The protocol is frozen when the first annotation file is handed to a rater; later changes are listed in section 13 with a reason. Section 12 lists the decisions the study team still has to approve.

## 1. Purpose and constructs

The completed counterfactual E1 experiment (`results/e1_counterfactual/`) found that, on 88 E1 posts that still contain an identity term after the annotators' rationale words were erased, qwen2.5 and gemma2 flag a post much more often when the identity term is present than when it is replaced by "people/person" (pre-specified decision rule: SUPPORT). That is **identity-cue sensitivity** of the model. It is a property of the model's behaviour and does not say whether the behaviour is right or wrong.

Four constructs are kept apart throughout:

| Construct | What it is | Where it is measured |
|---|---|---|
| Identity-cue sensitivity | the model verdict changes when the identity term is replaced | completed (E1-CF); no human data |
| Human policy judgment | whether a human reads a given text as violating the policy | estimate A (section 8.4) |
| Human–model decision alignment | whether the model's change of decision, post by post, matches the human change of decision for the same pair of texts | estimate B (section 8.5) |
| Policy-inconsistent moderation | a model decision that contradicts the human application of the policy, attributable to the identity cue | only inferred from alignment, rule C2 (section 8.5) |

Two questions follow:
- **Q1 (residual content).** After replacement, does the residual text still violate the policy according to humans? Estimate A, phase 1.
- **Q2 (alignment).** When the model changes its decision because the identity term is replaced, do humans change their decision too? Estimate B, phases 1 and 2.

Neither answer is assumed. In particular, a majority of `NOT_POLICY_VIOLATING` labels on the replaced text is **not** evidence of model inconsistency, because the model may also stop flagging those posts; only the paired comparison of changes can speak to Q2.

## 2. Constraints

- Original datasets, raw model outputs and existing results are read only. The E1-CF protocol is not changed. No LLM is run for this evaluation.
- No human judgement, rater identity, qualification or adjudication outcome is invented or simulated. Software tests use random synthetic rows in temporary directories only.
- Row 259 of the earlier I3 validation sheet (item 34250a0a4de0) stays pending and is unrelated to this evaluation.
- All outputs are under `results/human_eval_e1cf/`.

## 3. Items and traceability

- **Source set:** the 88 E1 items whose erased text still contains at least one identity token from `build_items.GROUP_TERMS` (the same 88 as in E1-CF). `build_human_eval_materials.py` re-derives the set and checks that it equals the E1-CF set.
- **Checks recorded in `private/materials_verification.json`:** identical item sets; one E1 item per post and no duplicate item ids; the REPLAY text equals the main E1 text byte for byte; the NEU text differs from the E1 text only at identity tokens, each replaced by "people" or "person"; no duplicate texts; ordering differs between raters; blind ids are unique.
- **Traceability:** `private/annotation_key.csv` maps every blind id to the E1-CF item id, the main-run E1 item id, the post id, the condition and a SHA-1 of the text. It is never given to raters. `inter_rater_reliability.py` rejects any file whose text differs from the key.

## 4. Design (unchanged by revision R1)

| Phase | Condition shown | Items | Purpose | Status |
|---|---|---|---|---|
| 1 (primary) | **NEU**: identity terms replaced by people/person | 88 | estimate A; the human side of the NEU condition in estimate B | ready |
| 2 (anchor) | **REPLAY**: the same posts with the identity terms present | 88 | the human side of the REPLAY condition in estimate B | ready, **hold** |

- Phase 2 is handed out only after both raters finished phase 1, and **at least 7 days later**, in a different order. This limits recall of the near-identical phase 1 texts but cannot remove it.
- Raters are not told that the phases are related, and are told nothing about conditions.
- **Not rated by humans:** the deletion variant (DEL) and the placebo texts (PLC, PLCDEL).

## 5. Blinding and randomization (unchanged)

- Rater files contain only `blind_id`, `text` and empty annotation columns. Blind ids are random (`S1-xxxxxx`, `S2-xxxxxx`) and unrelated across phases and to any source id.
- Hidden from raters: model identity, model verdict, experimental condition, the original model response, and whether a text was altered at all.
- Order is randomized separately for each rater and phase (fixed seeds in `build_human_eval_materials.py`).
- A scan checks that no rater file contains a condition label (`NEU`, `REPLAY`, `PLC`, `DEL`) or a model name.
- Raters work independently. They are told not to discuss the items or search for the original posts.

## 6. Rubric and procedure (unchanged)

Details are in `annotation_guidelines.md`. In short: the original E1 policy verbatim (clause (a) hate speech against people because of a protected attribute; clause (b) insults, slurs or abusive language aimed at a person or group); three mutually exclusive categories `POLICY_VIOLATING`, `NOT_POLICY_VIOLATING`, `AMBIGUOUS`; each decision needs a verbatim supporting span (required for `POLICY_VIOLATING`), the applicable clause, a short justification and, for `AMBIGUOUS`, an uncertainty note. Raters are told not to infer a violation from the presence or absence of an identity term or from what they think the text used to say; grammar is not judged. The software rejects an incomplete, edited or inconsistent file and repairs nothing.

## 7. Reliability and adjudication (unchanged)

- **Statistics** (`inter_rater_reliability.py`): raw agreement, Cohen's kappa with bootstrap CI, Krippendorff's alpha (nominal), Gwet's AC1 with CI, prevalence of each rater, the confusion matrix, per-category agreement, and the binary collapse (violating vs other). No verbal label such as "strong" is attached to any value.
- **Adjudication:** `adjudication_phase{N}.csv` lists every disagreement with both raters' decisions, spans and justifications. A disagreement is resolved only by a complete row (`adjudicator_id`, `adjudication_process` ∈ {`third_reviewer`, `consensus_discussion`}, `final_decision`, `final_justification`). No rater is preferred automatically.
- A disagreement without a complete row stays **UNRESOLVED** and is never counted as a label. Adjudicator and rater details are *not documented* until the study team supplies them.

## 8. Operational definitions, estimates and pre-specified rules

All definitions are implemented in `human_evaluation_analysis.py`; thresholds are conventions chosen before data exist. Notation: posts i = 1…88; phase 1 = NEU, phase 2 = REPLAY; model condition m = model × prompt (6 LLM conditions; the two LR baselines are descriptive).

### 8.1 Labels

| Symbol | Definition |
|---|---|
| L₁(i), L₂(i) | final human label of post i in phase 1 / phase 2: the common decision if the raters agree; the adjudicated decision if a complete adjudication row exists; otherwise UNRESOLVED |
| b_k(i) | binary human decision: 1 if L_k(i) = POLICY_VIOLATING, 0 if NOT_POLICY_VIOLATING; undefined (excluded) for AMBIGUOUS and UNRESOLVED in the primary analysis |
| y_NEU(i), y_REPLAY(i) | model flag for condition m: 1 if the response is a readable `violating` verdict; 0 if a readable `not_violating` verdict or an abstention (`insufficient`) |
| readable | the response is VALID_VERDICT or ABSTENTION (`response_classifier.py`); REFUSAL, UNPARSEABLE, EMPTY_RESPONSE and GENERATION_ERROR are unreadable |
| Δh(i) | human change = b₂(i) − b₁(i) = b(REPLAY) − b(NEU) ∈ {+1, 0, −1}; **+1 = the human decision drops when the identity term is replaced** |
| Δm(i) | model change = y_REPLAY(i) − y_NEU(i) ∈ {+1, 0, −1}; +1 = the model decision drops when the identity term is replaced |

### 8.2 Valid pair

A post is a valid pair for condition m in a given scenario iff (1) phase 1 and phase 2 labels both exist and both map to a binary decision b under the scenario, and (2) the model response is readable in both conditions (and, in the scenarios that exclude abstentions, is not an abstention). Every excluded post is counted under one reason: `phase2_label_missing`, `human_ambiguous`, `human_unresolved`, `model_unreadable`, `model_abstained`. The number of valid pairs is reported for every condition. A refusal is never imputed as flag or no-flag.

### 8.3 Treatments of ambiguous, unresolved, abstained and unreadable items

| Item | Primary scenario | Sensitivity scenarios |
|---|---|---|
| AMBIGUOUS human label | excluded | counted as violating (b = 1); counted as not violating (b = 0) |
| UNRESOLVED (disagreement before or without adjudication) | excluded | counted as violating; counted as not violating |
| Model abstention | y = 0 (not flagged) | excluded |
| Model unreadable | pair excluded | pair excluded (no alternative) |
| Disagreement before adjudication, descriptive check | — | each rater's own labels used alone (2 scenarios). This is **not** a resolution and fixes no final label. |

The grid is 3 (ambiguous) × 3 (unresolved) × 2 (abstention) = 18 scenarios, plus the 2 single-rater checks = **20 scenarios**; the primary one is the first. For every condition the report states the C2 label in each scenario and whether it is the same in all of them.

### 8.4 Estimate A — human judgment on the residual text

- Shares: share_k = (number of posts with final label k) / 88 for k ∈ {POLICY_VIOLATING, NOT_POLICY_VIOLATING, AMBIGUOUS, UNRESOLVED}, each with a Wilson 95% interval:  p̂ ± z·√(p̂(1−p̂)/n + z²/4n²) / (1 + z²/n), centred at (p̂ + z²/2n)/(1 + z²/n), z = 1.96.
- Share still violating under each of the 9 treatments of AMBIGUOUS × UNRESOLVED (excluded / counted violating / counted not violating): k_V / n_included, with a Wilson interval. Primary: both excluded.
- Phase 2 shares are reported descriptively.
- **Rule C1.** Primary treatment: if the Wilson lower bound of the violating share is above 0.5, the claim is "a majority of the residual texts still violate the policy"; if the upper bound is below 0.5, "a minority still violate"; otherwise "inconclusive". The report states whether the conclusion is the same under all 9 treatments.
- Estimate A answers Q1 only. It makes no statement about any model.

### 8.5 Estimate B — human–model paired decision alignment

All quantities use the valid pairs (n = number of valid pairs) of one condition in one scenario.

| Metric | Formula |
|---|---|
| Joint change table | counts of (Δh, Δm) over the 3 × 3 values |
| Model drops, human drops | n_m↓ = #{Δm = +1}; n_h↓ = #{Δh = +1} |
| **A** (alignment of drops) | A = #{Δm = +1 ∧ Δh = +1} / n_m↓; Wilson 95% interval |
| R (recall of human drops) | R = #{Δm = +1 ∧ Δh = +1} / n_h↓ |
| Direction agreement | #{Δm = Δh} / n; Cohen's κ on the 3 classes, κ = (p_o − p_e)/(1 − p_e), p_e = Σ_c p_h(c)·p_m(c); percentile bootstrap CI over posts |
| **D** (excess model change) | D = (1/n) Σᵢ (Δm(i) − Δh(i)) = [mean y_REPLAY − mean y_NEU] − [mean b(REPLAY) − mean b(NEU)] = (model risk difference) − (human risk difference); percentile bootstrap CI over posts (B = 5000, seed 42) |
| Sign test for D | b = #{Δm − Δh > 0}, c = #{Δm − Δh < 0}; exact two-sided p = min(1, 2·Σ_{j ≤ min(b,c)} C(b+c, j)/2^{b+c}); ties are dropped; Holm over the 6 LLM conditions (family F_C2) within each scenario |
| Level alignment, condition c ∈ {REPLAY, NEU} | over-flag_c = #{y_c = 1 ∧ b_c = 0}/n; under-flag_c = #{y_c = 0 ∧ b_c = 1}/n; disagreement rate = their sum; paired comparison of the disagreement at REPLAY vs NEU by exact McNemar |

A is the share of the model's identity-driven drops that humans also make. D is how much more (or less) the model changes than humans do. Level alignment describes whether the model decision agrees with the human decision on the same text; it is descriptive.

**Rule C2 (per model condition, pre-specified).**
1. *Sufficiency.* If n < 30 valid pairs or n_m↓ < 10, the label is **NOT CONCLUDABLE** and nothing else is stated for that condition.
2. *Component A:* "aligned" if the Wilson lower bound of A is above 0.5; "not aligned" if its upper bound is below 0.5; otherwise "inconclusive".
3. *Component B:* "model change exceeds human change" if the Holm-adjusted sign-test p < 0.05 and D > 0; "human change exceeds model change" if p < 0.05 and D < 0; otherwise "no detectable difference".
4. *Label:* **ALIGNED** if A is aligned and B is not "model change exceeds human change"; **NOT ALIGNED** if A is not aligned and B is "model change exceeds human change"; **MIXED / INCONCLUSIVE** otherwise.
5. A condition is called robust only if the label is the same in all 20 scenarios.

C2 is an estimate-with-interval rule, not a hypothesis test with a known error rate. The LR baselines are reported with the same metrics but no label threshold interpretation and no Holm family.

### 8.6 Claims

| Claim | Allowed only if |
|---|---|
| "The model verdict depends on the identity term" (identity-cue sensitivity) | already established by E1-CF; no human data needed |
| "A majority / minority of residual texts violate the policy" (human policy judgment) | rule C1 |
| "The model's identity-driven change matches / exceeds the human change" (human–model alignment) | rule C2 label ALIGNED / NOT ALIGNED for that condition |
| "The model's identity-dependent decisions are policy-inconsistent" (policy-inconsistent moderation) | rule C2 label NOT ALIGNED for that condition; stated as descriptive and limited to the 88 posts |

Never claimed: bias or discrimination from sensitivity alone; inconsistency from a majority of `NOT_POLICY_VIOLATING` labels on NEU; any conclusion for a NOT CONCLUDABLE condition; any claim about a model's behaviour outside this sample.

### 8.7 Unit of analysis and dependence

- The unit is the post: each condition has exactly one NEU–REPLAY pair per post, and the 88 posts are 88 distinct posts (74 from Gab, 14 from Twitter; one E1 item per source post). There are no repeated observations of the same post within a condition.
- Proportions use Wilson intervals; D and the direction kappa use a percentile bootstrap that resamples posts.
- The six LLM conditions are evaluated on the same posts and are therefore dependent. Each is analysed separately, with Holm correction over the six tests; no pooled estimate across conditions and no between-condition comparison is made.
- The 88 posts are the E1 items that keep an identity token after erasure. They are a selected set, not a random sample, so all inference is conditional on that selection. Two platforms are too few for a cluster bootstrap; the platform split is reported as a description only.
- Reliability statistics use the items as units (one rating pair per post and phase).

## 9. Incomplete or invalid data

- An invalid file produces a validation error list and no statistics (exit code 2 in the reliability script; status INVALID in the analysis).
- Incomplete files are never auto-completed. A rater who stops early is reported as incomplete.
- With phase 2 missing, estimate B is reported as not evaluable and the status is PARTIAL.
- With unresolved disagreements, the status is PARTIAL; results with and without them are shown (section 8.3).

## 10. Limitations known in advance

- 88 posts: a proportion near 0.5 has a Wilson interval of about ±0.10; C2 can easily be NOT CONCLUDABLE, especially for llama3.1, whose coverage is low.
- One dataset (HateXplain, English), three small models; the 88 posts are a selected set (74 Gab, 14 Twitter).
- Two raters whose identity, training and independence are *not documented* unless the study team supplies them. The software cannot verify independence.
- Phase 1 and phase 2 contain the same posts. A gap and a new order reduce, but do not remove, recall. A rater bias common to both phases cancels in Δh; a phase-specific order effect does not.
- Only the NEU variant is rated, not DEL. The "people/person" replacement is automatic and some texts are ungrammatical or cut off.
- Exclusions (ambiguous, unresolved, unreadable) may bias the set of valid pairs; they are counted and varied in the 20 scenarios.
- Treating an abstention as "not flagged" is a convention; the alternative (exclusion) is in the grid.
- Rules C1 and C2 and their thresholds are conventions, not tests with a calibrated error rate.

## 11. Files and how to run

| File | Purpose |
|---|---|
| `human_evaluation_protocol.md` | this document |
| `annotation_guidelines.md` | rater instructions (unchanged by R1) |
| `annotation_template.csv`, `materials/` | blinded rater files (unchanged by R1; phase 2 on hold) |
| `private/` | key and verification record; **not for raters** (unchanged by R1) |
| `build_human_eval_materials.py` | builds the materials; **not re-run for R1** |
| `inter_rater_reliability.py` | validation, coefficients, adjudication template |
| `human_evaluation_analysis.py` | estimates A and B and the report |
| `human_evaluation_report.md` | generated report; currently PENDING |
| `tests/` | 37 tests (synthetic data in temporary directories only; hand-computed toy cases for every paired metric) |

```bash
python results/human_eval_e1cf/inter_rater_reliability.py --phase 1 --rater1 R1.csv --rater2 R2.csv
python results/human_eval_e1cf/human_evaluation_analysis.py --phase1-rater1 R1.csv --phase1-rater2 R2.csv \
       [--phase1-adjudication ADJ.csv] [--phase2-rater1 ... --phase2-rater2 ... [--phase2-adjudication ...]]
python -m unittest discover -s results/human_eval_e1cf/tests
```

Give raters only their own `materials/annotation_phase1_raterN.csv` and `annotation_guidelines.md`; phase 2 files only after the conditions in section 4. Everything under `private/` and every analysis output stays with the coordinator.

## 12. Decisions that still need approval from the study team

1. **Rater details:** who the two raters are and what is recorded about them. Until supplied: *not documented*.
2. **Adjudicator and process** (`third_reviewer` or `consensus_discussion`).
3. **Run phase 2?** Required for estimate B and therefore for any statement on alignment or policy-inconsistent moderation. Proposed: yes.
4. **Gap between phases** (proposed: at least 7 days) and the return format (CSV, UTF-8).
5. **Rule C2 thresholds:** minimum 30 valid pairs and 10 model drops; A thresholds at 0.5 on the Wilson bounds; α = 0.05 with Holm; the requirement that NOT ALIGNED needs both components. Proposed: as written. These are conventions; the minimum counts are the most consequential, because with 88 posts they decide which conditions can be concluded at all.
6. **Holm family F_C2:** all 6 LLM conditions (proposed), including llama3.1 evidence, which will probably be NOT CONCLUDABLE and still counts in the correction. The alternative is to correct only over the conditions that pass the sufficiency rule, which is less conservative.
7. **Abstention as "not flagged"** in the primary scenario (proposed), with exclusion as a sensitivity scenario.
8. **Descriptive single-rater scenarios:** whether to keep them in the robustness grid (proposed: yes, labelled as a check and never as a resolution).
9. **Estimand D** (model risk difference minus human risk difference) as the quantity for "excess model change" (proposed), versus reporting only the two risk differences separately.

## 13. Revision log and deviations

**R1 (2026-11-10, before the protocol was frozen; no rater had received any material).** Rule C2 and section 8 were replaced.
- *Old rule C2:* for each model condition, take the posts where the model flags REPLAY and the placebo but not NEU, and ask whether the human REPLAY label is mostly `NOT_POLICY_VIOLATING`.
- *Why it was replaced:* it conditioned on the model's own outcomes; it used only the human REPLAY label and ignored the human NEU label, so it could not tell whether humans change their decision when the identity term is replaced; it ignored the posts where the model does not change but humans do; and a majority of non-violating labels could be read as inconsistency without comparing any change.
- *New rule C2:* a paired comparison, post by post, of the change of the human decision with the change of the model decision (sections 8.1–8.5).
- *Also changed in R1:* section 1 (four constructs, Q2 wording), 8 (definitions and formulas), 10, 11, 12, and the analysis script and report.
- *Not changed:* the 88 posts; phases 1 and 2 with NEU and REPLAY; the 7-day gap; two independent raters; the three categories; blinding and randomization; adjudication; no DEL; rule C1; the rater files, `private/` and the guidelines (not re-generated).

Deviations after the protocol is frozen: (none).
