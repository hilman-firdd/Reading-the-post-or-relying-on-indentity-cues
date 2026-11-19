# Respons audit #15 (v30), 19 Nov 2026

Auditor tidak menemukan koreksi substantif baru. **Naskah v30 tidak diubah** (`JSC_Manuscript_Firdaus_v30.pdf`, 12 halaman).

Perubahan hanya di suplemen (`JSC_Supplement_v30.pdf`, tetap 1 halaman; salinan gabungan `JSC_v30_manuscript_plus_supplement.pdf` diperbarui):

- Temuan auditor dari matriks transisi diverifikasi dari respons mentah lalu dicantumkan di suplemen. Untuk Gemma 2 evidence, **15 dari 16** penurunan flag bersih berasal dari transisi flag↔`insufficient` (17 − 2), dan 1 dari flag → `not violating`.
- Setiap kondisi kini menampilkan dekomposisi bersih $b-c$ (via *insufficient* / via *not violating*) dan jumlah pasangan dengan dua verdict valid. Untuk Qwen2.5/Gemma 2, jumlah itu adalah **84, 73, 64, dan 51**, sama dengan subset *valid verdicts only* di §4.4.
- `paper/supp_e1cf_transitions.py` kini juga memastikan ukuran subset itu sama dengan `results/e1_counterfactual/posthoc_valid_only.json`, dan bahwa jumlah kedua komponen sama dengan $b-c$.

Dekomposisi per kondisi (dihitung dari data):

| Kondisi | net b−c | via insufficient | via not violating | dua verdict valid |
|---|---:|---:|---:|---:|
| Qwen2.5 direct | 20 | 1 | 19 | 84 |
| Qwen2.5 evidence | 15 | 3 | 12 | 73 |
| Gemma 2 direct | 22 | 10 | 12 | 64 |
| Gemma 2 evidence | 16 | 15 | 1 | 51 |
| Llama 3.1 direct | 11 | 0 | 11 | 52 |
| Llama 3.1 evidence | 0 | 0 | 0 | 12 |

Pemeriksaan: pytest 68 lulus (tes transisi diperluas), `verify_v25_revisions.py` `FAILS: []`.

**Putaran revisi redaksional selesai di v30**, sesuai saran auditor. Langkah berikutnya: validasi langsung pasangan NEU–PLC pada 88 post (`results/e1_counterfactual_v2/`), dengan protokol v2 di-commit sebelum anotasi pertama.
