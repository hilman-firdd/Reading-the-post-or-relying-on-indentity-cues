# Respons audit #12 (v27 → v28), 19 Nov 2026

Naskah: `paper/JSC_v25/JSC_Manuscript_Firdaus_v28.tex` / `.pdf` (12 halaman, abstrak 150 kata). Pemeriksaan: `verify_v25_revisions.py` 112 cek `FAILS: []`, pytest 66 lulus, urutan sitasi 1–28 berurutan.

| Penyesuaian | Perubahan v28 |
|---|---|
| 1. Konteks OR 3,1–8,8 di abstrak | Menjadi: *"In five of six LLM conditions, posts keeping an identity term after rationale erasure had significantly higher odds of being flagged (odds ratio 3.1–8.8)."* Kondisi keenam (Llama 3.1 evidence, OR 3,5, Holm p = 0,083) tetap dilaporkan di §4.3 dan Tabel 5. |
| 2. Asimetri E1/E2 (§4.3) | "The asymmetry is the main finding" dihapus. Ditambahkan: *descriptive asymmetry*; kedua uji memakai subset berbeda (post yang awalnya *violating* vs *not violating*) dan edit berbeda; selisihnya **tidak diuji**. |
| 3. Objek keputusan SUPPORT | §3.7: hasil *"meets the protocol's rule for the identity-edit versus placebo-edit contrast (label SUPPORT)"*. §4.4: *"meets the protocol's decision rule for the identity-edit versus placebo-edit contrast (SUPPORT); this concerns the tested edits, not the identity term in isolation."* Batasan kedua di §4.4 dan Kesimpulan memakai bahasa yang sama ("concerns the tested edits"). Kalimat terakhir abstrak: *"dependence on the tested edits"*. |

Supaya tetap 12 halaman, abstrak dipadatkan (tanpa "local", "online"), dan deskripsi penilai, butir (5) Threats, Kesimpulan, Data availability, dan kontribusi penulis dipersingkat. URL HateXplain diganti rujukan [6], tetapi commit 01d7422 tetap disebut. Tidak ada angka hasil yang berubah.

## Langkah Q1 (tidak berubah dari audit #11)

Analisis utama tetap memakai seluruh sampel. Analisis tambahannya: validasi langsung pasangan NEU dan PLC pada 88 post (sasaran, makna relevan, status pelanggaran), lalu selisih flag PLC−NEU pada pasangan yang dinilai mempertahankan status pelanggaran, lengkap dengan jumlah pasangan dan interval. Bahannya sudah ada di `results/e1_counterfactual_v2/`. Commit protokol v2 sebelum anotasi pertama.
