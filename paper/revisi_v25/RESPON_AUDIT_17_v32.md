# Respons audit #17 (v31 → v32), 19 Nov 2026

Auditor tidak menemukan koreksi substantif baru. Satu saran rumusan abstrak diterapkan:

- **Sebelum (v31):** "replacing identity terms lowers the flag rate by 17.0–25.0 points more than an edit-count placebo for Qwen2.5 and Gemma 2"
- **Sesudah (v32):** "the flag rate was **17.0–25.0 percentage points lower under identity-term replacement than under an edit-count placebo** for Qwen2.5 and Gemma 2"

Abstrak tetap 150 kata dan naskah 12 halaman. Suplemen isinya identik dengan v31. Naskah kini mengutip commit **655d9b8** (sudah ada di GitHub). Pemeriksaan: `verify_v25_revisions.py` `FAILS: []`.

Paket unggah: `paper/JSC_v25/submission_v32/` (naskah, suplemen, cover letter, Gambar 1 dalam TIFF/EPS/JPEG).

Satu baris di `verify_v25_revisions.py` (string pemeriksa abstrak) belum di-commit; kode analisis dan data di 655d9b8 tidak berubah.

Langkah berikutnya untuk Q1: validasi 88 pasangan NEU–PLC (`results/e1_counterfactual_v2/`), dengan protokol v2 di-commit sebelum anotasi pertama.
