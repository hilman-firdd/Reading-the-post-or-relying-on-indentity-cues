# Respons audit #14 (v29 → v30), 19 Nov 2026

Files (folder `paper/JSC_v25/`):
- `JSC_Manuscript_Firdaus_v30.pdf`: naskah, 12 halaman, abstrak 150 kata.
- `JSC_Supplement_v30.pdf`: suplemen, 1 halaman, **Supplementary Table S1**.
- `JSC_v30_manuscript_plus_supplement.pdf`: salinan review berisi naskah + suplemen (13 halaman), supaya auditor atau rekan dapat memeriksa S1 dalam satu file.

Untuk ScholarOne, unggah naskah dan suplemen sebagai **dua file terpisah** (naskah tetap dalam batas 10–12 halaman).

Pemeriksaan: `verify_v25_revisions.py` 130 cek `FAILS: []`, pytest 68 lulus.

| Temuan | Perubahan v30 |
|---|---|
| 1. Suplemen S1 tidak ada di PDF yang diaudit | S1 sudah dibuat di v29 sebagai file terpisah; auditor hanya menerima PDF naskah. v30: (a) judul di suplemen diseragamkan menjadi **"Supplementary Table S1"**, sama persis dengan sitasi di §4.4; (b) §4.4 menyebut "(Supplementary Table S1, supplementary file)"; (c) Data availability menyebut sumber datanya (`results/e1cf_transitions.json`); (d) cover letter menyebut file suplemen; (e) disiapkan salinan review gabungan. |
| Rekonsiliasi Gemma 2 evidence | Suplemen kini memuat kalimat rekonsiliasi yang diminta: 88 pasangan, semuanya dijawab; 18 flag hilang di NEU (1 ke *not violating*, 17 ke *insufficient*); 2 flag muncul (keduanya dari *insufficient*); selisih bersih (18−2)/88 = 18,2 poin, sama dengan Tabel 6. Skrip `supp_e1cf_transitions.py` menegaskan n, b, c untuk keenam kondisi sama dengan Tabel 6. |
| 2. Pembuka §3.7 | Kutipan auditor ("whether a residual identity term itself contributes") sudah tidak ada di v29 (diganti di v29). Untuk v30 dipakai rumusan persis saran auditor: *"To compare flag rates after residual identity-term replacement and after an edit-count-matched placebo, we used the 88 E1 posts…"* |

Supaya tetap 12 halaman, kalimat Data availability dipadatkan. Tidak ada angka hasil yang berubah.

`paper/JSC_v25/build.sh` kini membangun v30 dan suplemennya; jika `pdfunite` tersedia, skrip itu juga membuat salinan review gabungan.

## Langkah berikutnya (saran auditor)

Revisi redaksional dihentikan. Lanjutkan dengan validasi langsung pasangan NEU–PLC pada 88 post: status pelanggaran, sasaran, dan perubahan makna, dengan penilai yang tidak melihat respons model. Analisis 88 post tetap menjadi hasil utama. Pasangan dengan status pelanggaran sama dilaporkan sebagai sensitivitas, lengkap dengan jumlah pasangan, selisih flag, dan intervalnya. Workbook sudah ada di `results/e1_counterfactual_v2/`; commit protokol v2 sebelum anotasi pertama.
