# Respons audit #11 (v26 → v27), 19 Nov 2026

Naskah: `paper/JSC_v25/JSC_Manuscript_Firdaus_v27.tex` / `.pdf` (12 halaman, abstrak 149 kata). Pemeriksaan: `verify_v25_revisions.py` 104 cek `FAILS: []`, pytest 66 lulus, urutan sitasi 1–28 berurutan.

| Koreksi audit | Perubahan v27 |
|---|---|
| 1. §3.1 terlalu luas ("identity-cue sensitivity", "Their interaction") | Diganti **"sensitivity to identity-related edits"**: I1 menukar kelompok sasaran; E1-CF mengganti istilah identitas dengan *people*/*person* setelah rationale dihapus, yang juga dapat mengubah sasaran dan klausul yang berlaku. "Dual-axis" dinyatakan sebagai nama dua jenis pengujian; interaksi kedua sumbu ditulis **tidak diuji**. "Their interaction" dihapus; istilahnya menjadi *residual identity-term dependence*. Keterangan Gambar 1 disesuaikan. |
| 2. §3.7 kronologi | Ditulis tanpa menyimpulkan urutan: file protokol bertanggal 10 Nov **tanpa jam**; run log mencatat panggilan pertama **05:18:30, waktu lokal mesin tanpa zona waktu** (dibuat `date` di `run_e1cf.sh`); commit pertama 16 Nov (c60d6c4). Kalimat penutup: catatan ini *tidak* menetapkan bahwa isi protokol sudah ada sebelum panggilan pertama, sehingga E1-CF disebut *protocol-defined*. §3.6 kini hanya merujuk ke §3.7. Tidak ada bukti bertimestamp lain di repo. |
| 3. Keluarga Holm retensi | §3.6 menambahkan keluarga **$F_{\mathrm{RET}}$**: 8 uji retensi post hoc pada post yang di-flag di ORIG, dikoreksi terpisah dari $F_R$. Tabel 5 diberi kolom **Holm $p^\dagger$** dari data (`results/posthoc_e1_retention.json`), dan caption menyebut keluarga itu. Tes baru menghitung ulang Holm dari 8 p Fisher dan mencocokkannya dengan nilai tersimpan. |
| 4. §2, Tabel 1, §4.3: isolasi mekanisme | "separating the identity term from the effect of changing any word" diganti **"comparing the flag rate after identity-term replacement with an edit-count-matched placebo"**. Tabel 1 (baris identity-term work): "No edit-count-matched placebo on natural posts". §2: "an edit-count-matched control". Penutup §4.3: asosiasi antarpost, sedangkan §4.4 adalah **estimand berbeda** (kontras berpasangan pada 88 post). §4.4 dibuka dengan kalimat estimand. |

Supaya tetap 12 halaman: kalimat analisis daya, ukuran oracle-free R2, butir Threats (2)–(4), kontribusi penulis, deklarasi AI, dan rincian SHA-1 HateXplain dipadatkan. SHA-1 dihapus; commit 01d7422 tetap disebut. Tidak ada angka hasil yang berubah.

Kode: `paper/gen_tables.py` (kolom Holm retensi), `tests/test_jsc_v3_reproducibility.py` (indeks kolom + tes Holm $F_{\mathrm{RET}}$), `paper/revisi_v25/verify_v25_revisions.py` (string v27), `paper/JSC_v25/build.sh` (membangun v27).

## Langkah Q1 berikutnya (tidak bisa dari data saat ini)

Pertanyaan penentu dari auditor: *apakah selisih flag PLC−NEU tetap terlihat pada pasangan yang status pelanggarannya dinilai sama?* Bahannya sudah ada di E1-CF v2 (`results/e1_counterfactual_v2/`).

1. Commit dan push `PROTOCOL.md` v2 sebelum anotasi atau panggilan model pertama.
2. Dua penilai independen mengisi workbook untuk REPLAY, NEU, dan PLC pada 88 post: sasaran serangan, makna relevan, dan status pelanggaran.
3. Analisis utama tetap memakai seluruh sampel; tambahkan analisis pada pasangan yang dinilai mempertahankan status kebijakan, lengkap dengan denominator dan interval.
4. Jika fokusnya ketergantungan pada isyarat identitas, jalankan model pada item SWAP/SWAP2 (pertukaran antarkelompok terlindungi).
