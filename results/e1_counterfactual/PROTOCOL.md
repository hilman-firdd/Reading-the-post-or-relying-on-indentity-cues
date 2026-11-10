# Protocol — E1 identity-term counterfactual (E1-CF)

Status: **fixed before any model call** (2026-11-10). Changes after data collection must be listed in §8 with a reason. Results that deviate from this plan are reported as exploratory.

## 1. Question

In the main audit, after the annotators' rationale words are erased (E1), LLMs keep flagging posts that still contain a protected-group identity term much more often than posts without one: OR 3–9, Holm p < 0.001. The LR baselines show no such difference (OR ≈ 1.2). This is an association.

**Does the residual identity term itself cause the "still violating" verdicts?**

## 2. Items

- **Base set:** all E1 items whose erased text still contains at least one identity token from `build_items.GROUP_TERMS`. There are **88 posts** (the same 88 as in the audit). E1 items without identity terms are not used.
- **Identity detection:** lexical, the same rule as the audit (lower-cased whitespace tokens). Known noise: ambiguous tokens such as "black", "white", and "man".

Every post gets five texts:

| Condition | Text |
|---|---|
| `REPLAY` | the E1 text unchanged. Gives a stability check against the main run. |
| `NEU` | every identity token replaced by a neutral noun: `people` if the token is plural (`…s`, `men`, `women`), otherwise `person` |
| `PLC` | placebo for `NEU`: the same number k of randomly chosen non-identity content tokens replaced by the same multiset of neutral nouns |
| `DEL` | every identity token deleted |
| `PLCDEL` | placebo for `DEL`: k random non-identity content tokens deleted |

- **Content token:** alphabetic, length ≥ 3, not an identity token, not a HateXplain placeholder (`<user>`, `<number>`, …), not in a short English stop-word list.
- **Randomness:** the placebo choice uses `random.Random(sha1(item_id))`, so it is fixed per item.
- **Placebo limitation:** randomly chosen tokens can include residual insults. The placebo controls for "changing k content tokens", not for "changing k harmless tokens".

## 3. Systems and configuration (identical to the main runs)

- **Systems:** qwen2.5:7b, llama3.1:8b, gemma2:9b × prompts `direct` and `evidence`, plus word-LR and char-LR (retrained exactly as in the main study).
- **Prompts:** `run_llm.py: p_direct` and `p_evidence`, unchanged, with the original content policy.
- **Decoding:** temperature 0, seed 42, `max_tokens` 256, `--workers 6`.
- **Server:** Ollama 0.33.3 with `OLLAMA_NUM_PARALLEL=6` and `OLLAMA_CONTEXT_LENGTH=1024`.
- **Classification:** responses are classified with `response_classifier.py`. "Flag" = VALID_VERDICT `violating`.
- **Storage:** all outputs go to `results/e1_counterfactual/`. `runs/` is not touched.
- **Size:** 88 posts × 5 conditions × 6 LLM systems = 2,640 calls.

## 4. Primary hypothesis and analysis

**H1 (per LLM condition):** replacing the identity terms lowers the flag rate more than the placebo replacement does.

- **Contrast:** P(flag | PLC) − P(flag | NEU), paired on the post.
- **Pairs:** only posts where both NEU and PLC are answered (VALID_VERDICT or ABSTENTION).
- **Test:** exact McNemar on (flag_PLC, flag_NEU).
- **Effect size:** risk difference with a post-bootstrap 95% CI (B = 5000, seed 42), plus the conditional odds ratio with an exact CI.
- **Family F_CF:** the 6 LLM conditions, Holm-corrected.
- **Coverage:** reported next to every estimate. Refusals are never counted as flags or non-flags.

## 5. Secondary and descriptive analyses

- **S1:** P(flag | PLCDEL) − P(flag | DEL), same method, family F_CF2 (6 tests, Holm).
- **S2:** P(flag | REPLAY) − P(flag | NEU) and P(flag | REPLAY) − P(flag | PLC), descriptive.
- **S3:** REPLAY verdict vs the main-run E1 verdict, as percentage agreement on answered pairs. This is a stability check of the parallel inference.
- **S4:** H1 again after excluding the E1 items that human raters judged invalid ("still contains an attack"). Only 17 of the 88 posts were validated.
- **S5:** LR baselines, descriptive only. LR is lexical, so a change for LR measures feature weight, not reasoning.

## 6. Decision rule for the paper's claim (fixed now)

- **Support for a causal role of residual identity terms:** H1 is Holm-significant (p < 0.05) with RD > 0 in **at least 2 of the 4** qwen2.5/gemma2 conditions, **and** the S1 contrast has the same sign in those conditions.
- **Partial support:** RD > 0 in at least 3 of the 4 conditions, but fewer than 2 Holm-significant. The claim stays associational, with directional counterfactual evidence.
- **Otherwise:** the claim stays associational, and the counterfactual result is reported as not supporting it.
- **llama3.1:** reported, but not counted toward the decision because of its low coverage.

## 7. Interpretation limits (stated in advance)

- Replacing a group term with "people" can legitimately change the policy reading. Without a protected attribute, an insult falls under clause (b) instead of clause (a), and both clauses still mean "violating". A drop in flags therefore indicates identity-driven flagging only if the remaining text carries no insult.
- Automatic replacement is sometimes ungrammatical. The placebo shares this property.
- n = 88 posts, one dataset, three small models.

## 8. Deviations from protocol

1. **Server restart (2026-11-10 07:42).** The last run (gemma2:9b evidence) stalled at 400/440 responses from 06:40 (Ollama showed "Stopping", battery at 4%). Ollama was restarted with the same settings (`OLLAMA_NUM_PARALLEL=6`, `OLLAMA_CONTEXT_LENGTH=1024`, `OLLAMA_KEEP_ALIVE=30m`) and the run resumed from item 401 (resumable output, order-preserving). Prompts, decoding, and items were unchanged. The REPLAY condition reproduced the main-run verdict flags in 100% of answered pairs for every system (S3), which shows the configuration was equivalent.
2. No other deviation from the pre-specified analysis; entries 3 and 4 are post hoc additions. The analysis script was written and tested on the LR runs before any LLM data existed. The decision rule in §6 was not changed after seeing results.
3. **POST HOC analysis: valid-verdict-only H1 (added 2026-11-10; not in this protocol).** After the primary analysis, it was seen that 17 of the 18 posts that lose the flag in Gemma2 evidence (flagged under PLC, not flagged under NEU) moved to `insufficient` rather than to `not_violating`. The protocol counts an abstention as "not flagged", so this convention could drive the result. H1 was therefore recomputed on posts where both the PLC and NEU responses are VALID_VERDICT (abstentions removed), with exact McNemar and a post-bootstrap CI, and Holm correction over the **4 qwen2.5/gemma2 conditions** (a post hoc family; the pre-specified family F_CF over 6 conditions is unchanged). This analysis is **post hoc**, does not appear in the protocol, and the decision rule in section 6 was **not changed**. Script: `posthoc_abstention_e1cf.py`; output: `posthoc_valid_only.json`. (Entry 2 above, "no other deviation", refers to the pre-specified analyses at the time they were run.)
4. **POST HOC analysis: ambiguous identity tokens (added 2026-11-10; not in this protocol).** Identity detection is lexical and includes ordinary words such as "white", "black", "man" (a limitation already stated in RESULTS.md). As a robustness check, the posts whose identity tokens are all in {black, white, man} (25 of 88) were excluded and H1 (PLC-NEU) and S1 (PLCDEL-DEL) repeated on the remaining 63 posts for the 4 qwen2.5/gemma2 conditions, with the same functions as `analyze_e1_counterfactual.py` and Holm over those 4 conditions per contrast. The extended set {black, blacks, white, whites, man, men} (33 of 88; 55 remain) is reported as a comparison. Both are **post hoc**; the decision rule in section 6 was **not changed**. Script: `posthoc_ambiguous_tokens.py`; output: `posthoc_ambiguous_tokens.json`.
