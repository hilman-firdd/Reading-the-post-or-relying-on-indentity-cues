# Prompt ablation (analysis_systems.py ablation)

Chain: direct → +A quote first → +B decide only from quotes → +C insufficient when quotes do not settle the case (= evidence).

## gemma2_9b (4233 items in every step)

| Prompt | Coverage | Abstention | Refusal | ORIG acc. | E1 flag (all) | R1 abst. (answered) | E1 OR |
|---|---|---|---|---|---|---|---|
| direct | 91.9 | 8.0 | 0.0 | 73.8 | 47.9 | 20.5 | 8.79 |
| abl_quote_first | 91.0 | 8.9 | 0.0 | 72.7 | 49.9 | 28.1 | 5.99 |
| abl_quote_only | 89.8 | 10.2 | 0.0 | 71.8 | 49.1 | 27.7 | 6.23 |
| evidence | 84.1 | 15.9 | 0.0 | 69.2 | 44.3 | 34.5 | 4.69 |

## qwen2.5_7b (4233 items in every step)

| Prompt | Coverage | Abstention | Refusal | ORIG acc. | E1 flag (all) | R1 abst. (answered) | E1 OR |
|---|---|---|---|---|---|---|---|
| direct | 94.5 | 5.4 | 0.0 | 71.2 | 29.2 | 32.2 | 3.09 |
| abl_quote_first | 95.5 | 3.9 | 0.0 | 72.5 | 28.2 | 21.1 | 4.36 |
| abl_quote_only | 94.3 | 5.3 | 0.0 | 71.8 | 24.7 | 28.7 | 3.59 |
| evidence | 91.5 | 8.1 | 0.0 | 73.3 | 30.0 | 29.3 | 5.17 |

## Adjacent steps (exact McNemar, paired by post; RD = later − earlier step, in points; Holm per metric)

| Metric | Step | n | RD [95% CI] | Holm p |
|---|---|---|---|---|
| ORIG_correct | gemma2_9b: direct -> abl_quote_first | 600 | -1.2 [-2.8, +0.3] | 1 |
| ORIG_correct | gemma2_9b: abl_quote_first -> abl_quote_only | 600 | -0.8 [-2.0, +0.2] | 1 |
| ORIG_correct | gemma2_9b: abl_quote_only -> evidence | 600 | -2.7 [-4.2, -1.3] | 0.00087 |
| ORIG_correct | qwen2.5_7b: direct -> abl_quote_first | 600 | +1.3 [-1.3, +3.8] | 1 |
| ORIG_correct | qwen2.5_7b: abl_quote_first -> abl_quote_only | 600 | -0.7 [-3.0, +1.5] | 1 |
| ORIG_correct | qwen2.5_7b: abl_quote_only -> evidence | 600 | +1.5 [-0.7, +3.7] | 1 |
| E1_flagged | gemma2_9b: direct -> abl_quote_first | 397 | +2.0 [+0.0, +4.0] | 0.289 |
| E1_flagged | gemma2_9b: abl_quote_first -> abl_quote_only | 397 | -0.8 [-2.5, +1.0] | 1 |
| E1_flagged | gemma2_9b: abl_quote_only -> evidence | 397 | -4.8 [-7.3, -2.5] | 0.00033 |
| E1_flagged | qwen2.5_7b: direct -> abl_quote_first | 393 | -0.5 [-3.3, +2.5] | 1 |
| E1_flagged | qwen2.5_7b: abl_quote_first -> abl_quote_only | 392 | -3.8 [-5.9, -2.0] | 0.0011 |
| E1_flagged | qwen2.5_7b: abl_quote_only -> evidence | 395 | +5.6 [+3.3, +7.8] | 3e-06 |
| R1_abstained | gemma2_9b: direct -> abl_quote_first | 599 | +7.5 [+5.2, +10.0] | 0 |
| R1_abstained | gemma2_9b: abl_quote_first -> abl_quote_only | 599 | -0.3 [-1.8, +1.2] | 1 |
| R1_abstained | gemma2_9b: abl_quote_only -> evidence | 600 | +6.8 [+4.8, +9.0] | 0 |
| R1_abstained | qwen2.5_7b: direct -> abl_quote_first | 597 | -11.1 [-14.2, -7.9] | 0 |
| R1_abstained | qwen2.5_7b: abl_quote_first -> abl_quote_only | 594 | +7.7 [+4.9, +10.6] | 0 |
| R1_abstained | qwen2.5_7b: abl_quote_only -> evidence | 596 | +0.7 [-1.8, +3.2] | 1 |

Compare every step difference with the run-to-run variation in results/repeats/stability.md before attributing it to the prompt part.
