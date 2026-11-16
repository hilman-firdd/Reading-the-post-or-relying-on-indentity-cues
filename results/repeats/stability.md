# Run-to-run stability (analysis_repeats.py)

Repetition 1 = original runs (Qwen2.5 direct: first 822 items from the uniform re-run unless --rep1-as-reported).

## Main runs: agreement of the label (verdict, or response category when not answered)

| Condition | Reps | Identical in all | Agreement with rep 1 | Fleiss κ | Coverage mean [min–max] | ORIG acc. mean [min–max] | E1 OR [min–max] |
|---|---|---|---|---|---|---|---|

## E1-CF per repetition

| Rep | Decision | H1 RD (Holm p) per deciding condition | Valid-only H1 RD (Holm p over 4) |
|---|---|---|---|
| 1 | SUPPORT: causal role of residual identity terms (protocol §6) | qwen2.5:7b|direct: +22.7 (6.6e-05); qwen2.5:7b|evidence: +17.1 (0.0122); gemma2:9b|direct: +25.0 (0.000137); gemma2:9b|evidence: +18.2 (0.00161) | qwen2.5:7b|direct: +22.6 (8.4e-05, n=84); qwen2.5:7b|evidence: +16.4 (0.0338, n=73); gemma2:9b|direct: +18.8 (0.00146, n=64); gemma2:9b|evidence: +2.0 (1, n=51) |
