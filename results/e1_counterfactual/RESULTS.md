# E1-CF results — identity-term counterfactual

Protocol: `PROTOCOL.md` (fixed before data collection). Full numbers: `analysis.json`, `summary.csv`. Unit: post (88 posts). Pairs are posts where both conditions were answered (VALID_VERDICT or ABSTENTION). McNemar exact; risk difference (RD) with post-bootstrap 95% CI; Holm within family F_CF (6 LLM conditions).

## Decision (protocol §6)

**SUPPORT** — H1 is Holm-significant with RD > 0 in all 4 qwen2.5/gemma2 conditions, and S1 has the same sign in all 4.

## H1: flag rate under placebo replacement (PLC) minus identity replacement (NEU)

Flag = verdict `violating`. Rates are among the n paired, answered posts.

| System | n pairs | Flag PLC | Flag NEU | RD [CI95] | b / c | Holm p |
|---|---|---|---|---|---|---|
| qwen2.5 direct | 88 | 0.455 | 0.227 | +0.227 [0.136, 0.330] | 21 / 1 | 6.6e-05 |
| qwen2.5 evidence | 88 | 0.511 | 0.341 | +0.170 [0.068, 0.273] | 20 / 5 | 0.012 |
| gemma2 direct | 88 | 0.841 | 0.591 | +0.250 [0.148, 0.352] | 25 / 3 | 1.4e-04 |
| gemma2 evidence | 88 | 0.773 | 0.591 | +0.182 [0.091, 0.273] | 18 / 2 | 0.0016 |
| llama3.1 direct (not in the decision) | 52 | 0.615 | 0.404 | +0.212 [0.077, 0.346] | 13 / 2 | 0.015 |
| llama3.1 evidence (not in the decision) | 12 | 0.500 | 0.500 | 0.0 | 2 / 2 | 1.0 (untestable: only 16–41% of the 88 posts answered) |
| word-LR (descriptive) | 88 | 0.386 | 0.386 | 0.0 [−0.091, 0.091] | 8 / 8 | — |
| char-LR (descriptive) | 88 | 0.205 | 0.182 | +0.023 [−0.045, 0.091] | 6 / 4 | — |

## Secondary analyses

- **S1 (deletion):** PLCDEL − DEL, same method. RD +0.22 / +0.18 (qwen2.5 direct / evidence), +0.26 / +0.22 (gemma2 direct / evidence); all Holm p ≤ 0.011. word-LR −0.09 and char-LR +0.06, neither significant.
- **S2 (placebo is a fair control):** REPLAY − PLC is close to 0 for the LLMs (qwen2.5 +0.03 / +0.08, gemma2 0.00 / −0.05; none significant). Replacing random content words did not change LLM verdicts, whereas replacing the identity terms did (REPLAY − NEU +0.14 to +0.26 for the four qwen2.5/gemma2 conditions). For the LR models REPLAY − PLC is +0.14 (word-LR) and +0.13 (char-LR), significant: any token change lowers the LR score, which is why NEU − PLC isolates the identity effect.
- **S3 (stability):** in 100% of answered pairs, REPLAY reproduced the main-run flag. The parallel inference configuration is equivalent to the main-run configuration for these items.
- **S4 (excluding the 4 posts humans judged invalid):** same conclusion (n = 84; qwen2.5 direct RD +0.226, evidence +0.167; gemma2 direct +0.238, evidence +0.167; Holm p ≤ 0.020).

## What the result does and does not show

Shows:
- For qwen2.5 and gemma2 (and llama3.1 direct), a post that is erased of its annotator-marked rationale is flagged substantially less often when only its group terms are replaced by "people/person" than when the same number of other content words are replaced. The group term carries part of the "violating" verdict. The LR models show no such effect.
- The effect appears under both prompts and with both deletion and replacement.

Does not show:
- **Mechanism.** It cannot separate "the model recalls a stereotype" from "the model reads the remaining sentence as an attack on a protected group, which is what the policy forbids" (clause (a) of the policy). Replacing the group term with "people" removes the protected attribute, so a legitimately lower flag rate is also expected. The counterfactual shows dependence on the identity token, not that this dependence is illegitimate.
- **Whether the residual text contains a real attack.** 4 of the 17 human-validated posts were judged to still contain an attack. The finding is robust to excluding them, but only 17 of 88 posts were validated.
- **Generality.** 88 posts, one dataset, three small models, lexical identity detection (ambiguous tokens such as "white", "man" are included), automatic replacement that is sometimes ungrammatical.

## Consequence for the paper's main claim

The pre-specified rule supports the claim that, for the qwen2.5 and gemma2 LLMs, the verdict depends on the replacement of the residual identity terms. The wording should be limited to "the verdict depends on the identity term", not "the model recalls stereotypes". A human check on whether the residual text (identity term removed) still contains an attack would be needed to claim illegitimate reliance.

## Post hoc analyses (not in the protocol; added 2026-11-10)

These analyses were added after the primary analysis and are not part of the pre-specified protocol (`PROTOCOL.md` section 8, entries 3 and 4). The decision rule in section 6 was not changed; the outcome **SUPPORT** above is the outcome of the pre-specified analysis.

### A. H1 on valid verdicts only (abstentions removed)

Source: `posthoc_valid_only.json` (script `posthoc_abstention_e1cf.py`, which reproduces the primary H1 rates in `analysis.json` before computing). Pairs = posts with a VALID_VERDICT under both PLC and NEU. Holm over the 4 qwen2.5/gemma2 conditions (post hoc family).

| Condition | Valid pairs | Risk difference PLC − NEU | b / c | Holm p (4 conditions) |
|---|---|---|---|---|
| qwen2.5 direct | 84 | +22.6 points | 20 / 1 | 8.4e-05 |
| qwen2.5 evidence | 73 | +16.4 points | 17 / 5 | 0.034 |
| gemma2 direct | 64 | +18.8 points | 12 / 0 | 0.001 |
| gemma2 evidence | 51 | +2.0 points | 1 / 0 | 1.0 |

The pre-specified decision (SUPPORT) is unchanged. **The gemma2 evidence result does not survive this analysis**: of the 18 posts that lose the flag under NEU, 17 moved to `insufficient` and 1 to `not_violating`, so most of its primary-analysis effect reflects abstention, not a change to a "not violating" verdict. Qwen2.5 (both prompts) and gemma2 direct remain positive and Holm-significant.

### B. Ambiguous identity tokens

Source: `posthoc_ambiguous_tokens.json` (script `posthoc_ambiguous_tokens.py`; the 88-post set reproduces all 8 contrasts of `analysis.json` first). Posts excluded when all their identity tokens are in the set: core {black, white, man} = 25 posts (63 remain); extended {black, blacks, white, whites, man, men} = 33 posts (55 remain). Holm over the 4 conditions per contrast.

| Condition | H1, 63 posts: RD [CI95] (Holm p) | S1, 63 posts: RD (Holm p) | H1, 55 posts: RD (Holm p) | S1, 55 posts: RD (Holm p) |
|---|---|---|---|---|
| qwen2.5 direct | +23.8 [+12.7, +34.9] (0.001) | +23.8 (<0.001) | +25.4 (0.002) | +25.4 (0.002) |
| qwen2.5 evidence | +20.6 [+7.9, +33.3] (0.008) | +17.5 (0.035) | +20.0 (0.038) | +16.4 (0.078) |
| gemma2 direct | +25.4 [+12.7, +38.1] (0.003) | +25.4 (<0.001) | +21.8 (0.023) | +21.8 (0.005) |
| gemma2 evidence | +19.1 [+7.9, +30.2] (0.008) | +23.8 (<0.001) | +14.5 (0.039) | +20.0 (0.007) |

Excluding posts whose only identity tokens are ordinary words does not remove the effect: all 4 conditions stay positive and Holm-significant for both contrasts on the 63 posts. On the 55-post comparison set one contrast (qwen2.5 evidence, S1) is no longer significant (Holm p = 0.078). The findings are conditional on the lexical identity detection and on the abstention convention; neither sensitivity analysis addresses whether the dependence is legitimate.
