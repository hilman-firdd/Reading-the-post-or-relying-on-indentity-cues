# Run-to-run stability (analysis_repeats.py)

Repetition 1 = original runs (Qwen2.5 direct: first 822 items from the uniform re-run unless --rep1-as-reported).

## Main runs: agreement of the label (verdict, or response category when not answered)

| Condition | Reps | Identical in all | Agreement with rep 1 | Fleiss κ | Coverage mean [min–max] | ORIG acc. mean [min–max] | E1 OR [min–max] |
|---|---|---|---|---|---|---|---|
| qwen2.5_7b_direct | 1,2,3 | 99.9% | rep2: 99.9%, rep3: 99.9% | 0.9982 | 94.5 [94.5–94.5] | 71.2 [71.2–71.2] | 3.09 [3.09–3.09] |
| qwen2.5_7b_evidence | 1,2,3 | 99.7% | rep2: 99.8%, rep3: 99.9% | 0.9964 | 91.5 [91.5–91.6] | 73.3 [73.3–73.3] | 5.17 [5.17–5.17] |
| llama3.1_8b_direct | 1,2,3 | 99.7% | rep2: 99.8%, rep3: 99.9% | 0.9971 | 43.4 [43.4–43.5] | 26.1 [26.0–26.2] | 4.90 [4.90–4.90] |
| llama3.1_8b_evidence | 1,2,3 | 99.8% | rep2: 99.8%, rep3: 99.9% | 0.9956 | 18.0 [18.0–18.1] | 7.9 [7.8–8.0] | 3.34 [2.84–3.65] |
| gemma2_9b_direct | 1,2,3 | 100.0% | rep2: 100.0%, rep3: 100.0% | 1.0 | 91.9 [91.9–91.9] | 73.8 [73.8–73.8] | 8.79 [8.79–8.79] |
| gemma2_9b_evidence | 1,2,3 | 100.0% | rep2: 100.0%, rep3: 100.0% | 1.0 | 84.1 [84.1–84.1] | 69.2 [69.2–69.2] | 4.69 [4.69–4.69] |

## E1-CF per repetition

| Rep | Decision | H1 RD (Holm p) per deciding condition | Valid-only H1 RD (Holm p over 4) |
|---|---|---|---|
| 1 | SUPPORT: causal role of residual identity terms (protocol §6) | qwen2.5:7b|direct: +22.7 (6.6e-05); qwen2.5:7b|evidence: +17.1 (0.0122); gemma2:9b|direct: +25.0 (0.000137); gemma2:9b|evidence: +18.2 (0.00161) | qwen2.5:7b|direct: +22.6 (8.4e-05, n=84); qwen2.5:7b|evidence: +16.4 (0.0338, n=73); gemma2:9b|direct: +18.8 (0.00146, n=64); gemma2:9b|evidence: +2.0 (1, n=51) |
| 2 | SUPPORT: causal role of residual identity terms (protocol §6) | qwen2.5:7b|direct: +22.7 (6.6e-05); qwen2.5:7b|evidence: +17.1 (0.0122); gemma2:9b|direct: +25.0 (0.000137); gemma2:9b|evidence: +18.2 (0.00161) | qwen2.5:7b|direct: +22.6 (8.4e-05, n=84); qwen2.5:7b|evidence: +16.4 (0.0338, n=73); gemma2:9b|direct: +18.8 (0.00146, n=64); gemma2:9b|evidence: +2.0 (1, n=51) |
| 3 | SUPPORT: causal role of residual identity terms (protocol §6) | qwen2.5:7b|direct: +22.7 (6.6e-05); qwen2.5:7b|evidence: +18.2 (0.00748); gemma2:9b|direct: +25.0 (0.000137); gemma2:9b|evidence: +18.2 (0.00161) | qwen2.5:7b|direct: +22.6 (8.4e-05, n=84); qwen2.5:7b|evidence: +18.9 (0.0132, n=74); gemma2:9b|direct: +18.8 (0.00146, n=64); gemma2:9b|evidence: +2.0 (1, n=51) |
