# Protocol draft: E1-CF v2 (protected-group swap A→B and full human validation) + follow-up experiments

Status: DRAFT for the authors, 18 Nov 2026. Fix this protocol (commit it to the repo as `results/e1_counterfactual_v2/PROTOCOL.md`) **before any new model call or annotation**. It extends `results/e1_counterfactual/PROTOCOL.md` (fixed 2026-11-10); sections follow the same numbering. Items marked [DECIDE] need an author decision before freezing.

Ringkasan (ID): eksperimen ini menjawab temuan kritis audit v20/v21 (C1/C2): apakah penurunan flag pada NEU berasal dari ketergantungan pada nama kelompok, atau dari pembacaan kebijakan yang benar karena sasaran serangan berubah. Kunci desainnya: (1) SWAP A→B mempertahankan status terlindungi; (2) penilaian manusia atas SEMUA 88 pasangan; (3) uji H3 pada pasangan yang menurut penilai tetap melanggar setelah NEU (klausul b), sehingga penurunan flag di sana adalah kesalahan terhadap kebijakan.

---

## 1. Question

The v1 result (decision SUPPORT) shows that replacing residual identity terms with *people/person* (NEU) lowers the flag rate more than a placebo (PLC). Two readings remain:
- (R-a) the model relies on the presence of a protected-group term beyond what the policy requires;
- (R-b) the model correctly reads clause (a) of the policy, because NEU changes the target.

Under the tested policy, clause (b) also forbids insults aimed at any person or group, and the identity word list contains group names, not slurs. So (R-b) can only explain a drop where the remaining text attacks the group *as such* without insulting language. This protocol separates (R-a) from (R-b) and tests whether *which* protected group is named matters.

## 2. Items

Base set: the same 88 E1 posts (E1 text keeps ≥1 identity token from `build_items.GROUP_TERMS`).

| Condition | Text | Status |
|---|---|---|
| REPLAY | E1 text unchanged | re-run in the same session as SWAP (drift control) |
| NEU | identity tokens → *people/person* | existing v1 outputs, re-run once in the same session |
| PLC | k random content tokens → same neutral nouns | existing v1, re-run once |
| DEL, PLCDEL | as v1 | existing v1 (no re-run needed) |
| **SWAP** (new) | every identity token of group A → a term of group B with the **same number** (plural/singular) and part of speech | new |

**SWAP mapping (deterministic, fixed before any call).**
- Prefer a B with the **same protected attribute type** as A: race/ethnicity {African, Caucasian, Asian, Arab, Hispanic}; religion {Islam, Jewish, Christian, Hindu}; gender {Women, Men}.
- No same-type partner exists for {Homosexual, Refugee} in the word list. [DECIDE] either (i) add a same-type term fixed now (e.g. sexual orientation: "straight people/heterosexuals"; immigration status: none obvious) or (ii) use a cross-type protected group and report these posts as a separate stratum. Recommended: (ii), reported separately and excluded from H1.
- B chosen with `random.Random(sha1(item_id + "swap"))` among eligible groups ≠ A; one term per group, matching number (e.g. *muslims → jews*, *muslim → jewish* if adjectival; [DECIDE] a fixed noun/adjective table per group, written before generation).
- Posts with tokens of two groups: swap each group independently with distinct B's; flag as a stratum.
- A sensitivity set with a second, different B (`sha1(item_id + "swap2")`) is run for all posts (descriptive), to check that results are not driven by one particular B.

## 3. Human validation (all 88 posts; before any analysis of model outputs)

**Pairs judged:** REPLAY vs each of NEU, SWAP, PLC (full questionnaire); DEL and PLCDEL (attack persistence, naturalness, fidelity only). 88 × 5 = 440 pairs per rater.

**Questions** (answers: Yes / No / Cannot tell; "Cannot tell" is allowed and reported, never forced):

| Code | Question (per changed text, relative to REPLAY) |
|---|---|
| Q1 Meaning | Is the core meaning the same, apart from the planned change? |
| Q2 Attack | Does the text still insult, attack, dehumanise, or call for harm? |
| Q3 Target | Is the target of the attack still clear? |
| Q4 Protected (SWAP only) | Are A and B both protected attributes under clause (a)? |
| Q5 Policy | Does the changed text violate the policy? If yes, under (a), (b), or both? |
| Q6 Natural | Is the text natural and grammatical enough to be read as intended? |
| Q7 Fidelity | Was only the planned component changed? |

**Procedure.**
- Two raters, **separate workbooks/files** (no shared file), randomised pair order, no model outputs, no condition names shown (texts labelled A/B).
- Raters receive the policy text and written instructions; a 10-pair calibration set (not from the 88) is discussed before annotation and excluded.
- Adjudication by a **third person who is not the first author**, blind to which rater gave which answer; rule fixed now: adjudicator sees the two answers anonymised and the texts, decides, writes one line of reason.
- Report agreement **before** adjudication per question: % agreement, Cohen's κ and Gwet's AC1 (prevalence-robust), post-bootstrap CI.
- Raters' independence and procedure documented in `dokumentasi_penilai.xlsx` (no personal identifiers).

**Pair-validity definitions (fixed now).**
- SWAP-valid: Q1=Yes, Q3=Yes, Q4=Yes, Q6=Yes, Q7=Yes, and Q5 answer equals Q5 for REPLAY.
- NEU-still-violating: Q2=Yes and Q5=Yes for the NEU text (any clause).
- PLC-valid: Q6=Yes and Q7=Yes.

## 4. Runs

Same configuration as v1 (Ollama 0.33.3, digests as in the paper, temperature 0, seed 42, 6 parallel slots, context 1,024, max 256 tokens, `run_llm.py` prompts unchanged), 6 LLM conditions + word-LR/char-LR. Three repetitions of the new SWAP/REPLAY/NEU/PLC session (88 × 4 × 6 × 3 = 6,336 calls; SWAP2 once: 528 calls). Outputs to `results/e1_counterfactual_v2/`; `runs/` and v1 files untouched.

## 5. Hypotheses and analysis (outcome coding fixed now)

Outcome per response: flag (VALID `violating`), not violating, insufficient, refusal/unparseable. **Primary coding:** abstention = not flagged; refusals excluded pairwise. **Co-primary reporting (pre-specified, not post hoc):** valid-verdict-only analysis and a decomposition of every lost flag into → not violating / → insufficient / → no answer.

**H1 (confirmatory, equivalence).** On SWAP-valid pairs with a same-type B, the flag rate is equivalent under REPLAY and SWAP: the 90% CI of RD = flag(REPLAY) − flag(SWAP) lies within **±10 points** (TOST, α=0.05 per condition). [DECIDE margin; ±10 is proposed because it is half the smallest v1 H1 effect (17.1).]
- CI: post-level bootstrap (B=5,000, seed 42); exact McNemar reported alongside.
- Family: 4 deciding conditions (Qwen2.5, Gemma 2 × 2 prompts), Holm on the TOST p-values.
- Precision check (not a power justification): with n≈60–88 pairs and discordance 0.05–0.10, the 90% CI half-width is about 4–7 points, so ±10 is attainable if the true RD is near 0.

**H2 (secondary, difference of differences).** RD(PLC − NEU) − RD(REPLAY − SWAP) > 0, paired by post, post-bootstrap 95% CI, same 4 conditions (Holm). Interpretation: the NEU effect is larger than any group-specific effect, i.e. it reflects the presence of a protected-group term rather than which group.

**H3 (confirmatory, the decisive test for "beyond the policy").** On NEU-still-violating pairs (raters: the NEU text still violates, typically under clause (b)), RD(PLC − NEU) > 0, exact McNemar, Holm over the 4 conditions. A positive H3 means flags are lost when the group term disappears although the policy still applies → dependence beyond what the policy requires (reading R-a). A null H3 with a positive v1 effect points to reading R-b.

**Descriptive.** Direction by group pair (A→B and B→A where both occur), SWAP2 vs SWAP agreement, Llama 3.1 (not counted), LR baselines (lexical feature weights), three-run stability.

## 6. Decision rule (fixed now)

- **Group-name reliance beyond the policy:** H3 Holm-significant with RD>0 in ≥2 of 4 deciding conditions, in both the primary and the valid-only coding.
- **Group-invariant identity cue:** H1 equivalence holds in ≥3 of 4 conditions and H2 > 0 in ≥2 of 4.
- **Group-specific dependence:** H1 fails with |RD| > 10 points in ≥2 of 4 conditions (report direction per group pair; no fairness claim without a policy that treats the groups equally, which ours does).
- **Otherwise:** the v1 claim stays at "dependence on the tested replacement".
- The paper's wording follows this rule; no claim of bias, discrimination, or internal mechanism in any case.

## 7. Sample flow and limits (stated in advance)

Report: 88 built → n per exclusion reason (meaning, target, protected status, naturalness, fidelity, policy mismatch, cannot tell) → n analysed per hypothesis, with the label/platform/group distribution of excluded posts. If fewer than 40 SWAP-valid same-type pairs remain, H1 is reported as descriptive. Limits: one dataset, small models, lexical identity detection, swap terms chosen by the authors.

## 8. Deviations

Every change after freezing is logged here with date and reason; post hoc analyses are labelled.

---

# Follow-up experiments (priority order from the audits)

**P2 — Second dataset (replication of E1, E1-CF, SWAP).**
Candidate: SemEval-2021 Task 5 *Toxic Spans* (Pavlopoulos et al., 2021): English comments from Civil Comments with character-level toxic-span annotations (about 8.6k comments in the task data; nearly all have at least one span). Spans play the role of the HateXplain rationale for E1 erasure. Gaps to handle: (i) almost no non-toxic posts → take normal comments from Civil Comments for E2/ORIG; (ii) identity information → use the Civil Comments identity annotations (Borkan et al., 2019) where the comment IDs can be linked [VERIFY linkability and licence before committing]; (iii) a different platform and annotation scheme, which is the point of the replication. Pre-register sample size (e.g. 200 toxic + 200 normal posts, seed 42) and the same hypotheses before any model call.

**P3 — Comparable baselines (post-level split, no leakage of metamorphic variants).**
1. Lexical: keep word-LR/char-LR.
2. Fine-tuned encoder (e.g. a base-size transformer) on HateXplain train posts only.
3. **Policy-conditioned** baseline: input = [policy text; post]. Cheapest option: a zero-shot NLI model with the policy as hypothesis; stronger option: fine-tune the encoder on (policy, post, label) with the original and the narrowed (R2) policy so it can react to policy changes. Evaluate on ORIG, E1, E1-CF, R1–R3.

**P4 — Oracle validation still missing.** R2 hate-speech and normal strata (stratified 50 + 50); I2 neutrality (20% sample); I3 regenerated with a non-evaluated model (e.g. one of the extra models in `run_extra_models.sh`), screened by a second non-evaluated model and a human check of 20%; report the 98 missing paraphrases by label.

**P5 — Release.** English README section (install, Ollama setup, commands per table/figure), dataset manifest with full hashes (HateXplain commit 01d7422; `Data/dataset.json` SHA-1 d090baf2699c5ad488ccea7fd620db7fe1634d6b, verified 18 Nov 2026), frozen release + Zenodo DOI at submission.

**Manuscript after P1:** replace E1-CF limitation 2 and the Discussion "What they do not establish" paragraph with the H1–H3 results; keep NEU as identity neutralisation; decide the title only after the decision rule in §6 is applied.
