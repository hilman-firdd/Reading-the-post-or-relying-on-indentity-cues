# Respons audit #13 (v28 → v29), 19 Nov 2026

Naskah: `paper/JSC_v25/JSC_Manuscript_Firdaus_v29.tex` / `.pdf` (12 halaman, abstrak 150 kata) + **suplemen baru** `JSC_Supplement_v29.pdf` (Tabel S1). Pemeriksaan: `verify_v25_revisions.py` 127 cek `FAILS: []`, pytest 68 lulus, urutan sitasi 1–28 berurutan.

| Temuan | Perubahan v29 | Bukti dari data |
|---|---|---|
| Abstrak: OR dihitung pada respons yang dijawab | "In five of six LLM conditions, **answered** posts keeping an identity term after rationale erasure had significantly higher odds of being flagged (odds ratio 3.1–8.8)." | Tabel 5, blok asosiasi |
| §3.7 pembuka: "whether a residual identity term itself contributes" | Diganti: "To compare identity-term edits with placebo edits on posts that keep such a term after E1…" | — |
| §3.7 sisi uji McNemar | "tested with the **two-sided** exact McNemar test…; the direction enters through the decision rule, which also requires RD > 0." | `audit_metrics.mcnemar_exact` = 2 × ekor terkecil (dua sisi) |
| §4.4 presisi p Holm | H1: "Holm-adjusted p from <0.001 to **0.0122**"; S1: "<0.001 to **0.0112**". | `analysis.json`: maks H1 0.012231, S1 0.011157 (dicek di verify) |
| Abstensi: transisi satu arah vs selisih bersih | §4.4: angka 1/21, 3/20, 13/25, 17/18 disebut **one-way counts**; selisih bersih juga menghitung post yang hanya di-flag pada NEU (Gemma 2 evidence b/c = 18/2). **Tabel S1** (suplemen) memuat matriks transisi PLC→NEU lengkap (flag / not violating / insufficient / refusal-other) untuk enam kondisi LLM. | `paper/supp_e1cf_transitions.py` → `results/e1cf_transitions.json`; skrip memastikan n, b, c sama dengan Tabel 6 untuk keenam kondisi |
| §4.5 denominator R3 | "Of the 600 eligible posts, the pairs with both ORIG and R3 answered number 598–600 for Qwen2.5 and Gemma 2 and 166 and 45 for Llama 3.1…" Kolom R3 di Tabel 7 kini **k/n (%)**, misalnya 68/600 (11) dan 6/45 (13). Subset 119 post dengan oracle terkonfirmasi tetap dibedakan di kalimat berikutnya. | `statistical_analysis.json` → `behaviour_E_R[*].R3` (`gen_tables.py` memeriksa k/n terhadap persentase lama) |

Supaya tetap 12 halaman, beberapa kalimat di §4.1, §4.3, §4.4, §5, §6, dan §7 dipadatkan; Contamination digabung ke External. Tidak ada angka hasil yang berubah.

Kode: `paper/supp_e1cf_transitions.py` (baru), `paper/gen_tables.py` (sel R3 k/n), `tests/test_jsc_v3_reproducibility.py` (2 tes baru), `paper/revisi_v25/verify_v25_revisions.py` (blok A8 + string v29), `paper/JSC_v25/build.sh` (tabel S1 dan kompilasi suplemen).

## Saran auditor yang saya ikuti

Sesuai saran auditor, putaran revisi redaksional dihentikan di sini. Langkah berikutnya adalah validasi 88 pasangan NEU–PLC: rubrik yang sama, penilai tidak melihat respons model, dan setiap pasangan dicatat status pelanggaran, sasaran, serta perubahan maknanya. Analisis 88 post tetap menjadi hasil utama, dan pasangan dengan status pelanggaran sama dilaporkan sebagai sensitivitas, lengkap dengan denominator dan interval. Workbook dan item SWAP sudah tersedia di `results/e1_counterfactual_v2/`; commit protokol v2 sebelum anotasi pertama.
