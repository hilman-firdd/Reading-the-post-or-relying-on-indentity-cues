# Respons audit #16 (v30(2) → v31), 19 Nov 2026

Naskah: `paper/JSC_v25/JSC_Manuscript_Firdaus_v31.pdf` (12 halaman, abstrak 149 kata), suplemen `JSC_Supplement_v31.pdf` (1 halaman, isi sama dengan v30). Paket unggah ada di `paper/JSC_v25/submission_v31/`. Pemeriksaan: `verify_v25_revisions.py` 142 cek `FAILS: []`.

## Temuan minor (semua ditutup)

| # | Temuan | Perubahan v31 | Bukti dari data |
|---|---|---|---|
| 1 | §4.4: "REPLAY−PLC near zero (none significant)" menggabungkan besar efek dan uji | Selisih teramati dilaporkan: REPLAY−PLC **+3,4; +8,0; 0,0; −4,5** poin (Qwen2.5 direct/evidence, Gemma 2 direct/evidence), "exact McNemar, uncorrected p ≥ 0.14; **not a test of equivalence**". Pembanding REPLAY−NEU **+13,6 sampai +26,1**. Classifier: REPLAY−PLC **+13,6 dan +12,5** (sebelumnya dibulatkan +14 dan +13). | `analysis.json` → `S2_REPLAY_minus_PLC/NEU` (blok cek A9 baru) |
| 2 | §4.4: hasil 84 post | Kini ditulis sebagai **sensitivitas** terhadap pengeluaran **empat post yang diketahui masih menyerang** (dari 17 yang dinilai; 71 lainnya tidak dinilai). | `S4_H1_excluding_human_invalid` |
| 3 | Paket pengajuan | Folder `submission_v31/` berisi file terpisah: naskah, suplemen, cover letter, dan **Gambar 1 dalam TIFF (600 dpi), EPS, dan JPEG** sesuai panduan JSC. Salinan gabungan diberi nama `JSC_v31_review_copy_…` dan **tidak** untuk diunggah. | — |
| 4 | §2 dan Tabel 1: cakupan klaim pembanding | §2: "none of **the works we examined** reports an edit-count-matched control". Caption Tabel 1: "closest work **examined (targeted search, partly by abstract)**". | — |
| 5 | Abstrak tanpa ukuran efek E1-CF | Abstrak kini menyebut **17,0–25,0 poin**: "replacing identity terms lowers the flag rate by 17.0–25.0 points more than an edit-count placebo for Qwen2.5 and Gemma 2". Panjang tetap 149 kata. | Tabel 6 |

Penyesuaian kecil yang ikut dibuat:
- Threats (1) kini menyebut terus terang bahwa **NEU dan PLC belum dinilai status kebijakannya**.
- Kalimat sosial di §5 memakai angka bersih: **15 dari 16** penurunan flag bersih pada Gemma 2 evidence berpindah ke *insufficient* (Tabel S1).

Supaya tetap 12 halaman, Diskusi, Threats, dan Data availability dipadatkan. Tidak ada angka hasil yang berubah.

## Major (tidak bisa dari data yang ada)

Validasi NEU–PLC pada 88 pasangan: rubrik kebijakan yang sama, penilai tidak melihat respons model, dan setiap pasangan dicatat status pelanggaran, sasaran, serta perubahan maknanya. Analisis 88 post tetap utama; pasangan berstatus sama dilaporkan sebagai sensitivitas, lengkap dengan n, selisih flag, interval, dan transisi. Workbook ada di `results/e1_counterfactual_v2/`; commit protokol v2 sebelum anotasi pertama.

## Catatan commit

`verify_v25_revisions.py` berubah (cek A9 dan string v31), sehingga repo kini punya perubahan yang belum di-commit. Kode analisis dan data tidak berubah. Setelah commit dan push, minta saya kompilasi ulang supaya hash di naskah mengikuti commit baru (saat ini `60894b4`).
