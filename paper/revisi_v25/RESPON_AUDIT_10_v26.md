# Respons audit #10 (v25 → v26), 19 Nov 2026

Naskah: `paper/JSC_v25/JSC_Manuscript_Firdaus_v26.tex` / `.pdf` (12 halaman, abstrak 149 kata). Pemeriksaan: `verify_v25_revisions.py` 91 cek `FAILS: []`, pytest 65 lulus.

## Temuan yang diperbaiki dari data dan teks

| Temuan | Perbaikan v26 | Bukti |
|---|---|---|
| §4.3/§5: hitungan retensi tidak tampil; "far more strongly" tanpa uji | Tabel 5 kini punya blok retensi lengkap: kept/n dengan dan tanpa istilah identitas + OR retensi (ditandai † post hoc, CI eksak). Kalimat diganti: OR yang diamati lebih tinggi pada kondisi LLM tersebut dalam sampel ini; selisih antarsistem **tidak diuji langsung**. | `results/posthoc_e1_retention.json` (baru, dibaca `gen_tables.py`); jumlah n retensi diuji sama dengan n transisi |
| §5: E1 dan E1-CF digabung | Diskusi menulis dua temuan terpisah: E1 = asosiasi antarpost (397 post); E1-CF = kontras berpasangan dalam post (88 post), masing-masing dengan batas interpretasi. | §5 |
| §4.5: "offensive posts without a protected-attribute attack" | Diganti "non-ambiguous offensive stratum" (tidak ada anotator yang memilih hate speech), dengan catatan bahwa anotasi itu tidak membuktikan tiadanya serangan atribut terlindungi. Selisih estimasi berbobot antarmodel disebut deskriptif. Istilah "other/control" diganti di §3.5, Tabel 4, Tabel 7. | §3.5, §4.5 |
| Status *pre-specified* | Tidak ada bukti bertimestamp lain di repo (dicek: `logs/`, `backup_*`, `build_summary.json`). Jadi abstrak, kontribusi, kesimpulan, dan cover letter memakai **"protocol-defined"**; §3.6 dan §3.7 menjelaskan kronologi; judul §4.4 "(primary, protocol-defined)", bukan "(confirmatory)". | `git log` (PROTOCOL.md pertama di c60d6c4, 16 Nov), `run.log` |
| I3 "not missing at random" | Ditulis langsung: paraphrase hilang untuk 59 hate speech, 22 offensive, 17 normal; ketersediaan berbeda menurut label (χ² = 38,5); hasil I3 berlaku untuk 502 post yang punya paraphrase. | `statistical_analysis.json` → `I3.lost_by_label` |
| HateXScore (positioning) | Diverifikasi dari PDF EACL 2026: HateXScore **mem-mask span yang dikutip model di input dan menghitung ulang probabilitas**. §2 diperbaiki dan Tabel 1 diberi baris ERASER/HateXScore. Perbedaan v26: rationale **anotator**, kategori verdict (abstensi, refusal), kontras identitas versus placebo. | ACL Anthology 2026.eacl-long.198 |
| Fasching & Lelkes | Diverifikasi dari abstrak: desain faktorial, 1,3 juta kalimat, **125 kelompok**. §2 kini mengakui preseden kuat dan menyebut nilai tambah yang spesifik (edit berpasangan pada post alami yang sama setelah rationale dihapus, placebo, flag dipisah dari abstensi). Klaim "kontrol positif/netral" dari audit tidak saya tulis karena tidak terlihat di abstrak. | 2025.findings-acl.1144 |
| HateModerate dan Sadhu et al. | Diverifikasi: HateModerate memuat **41 kebijakan** Facebook; Sadhu et al. menghapus, menukar, atau menegasikan aturan dengan kasus tetap. §2 menyatakan relasi kebijakan v26 punya preseden; nilai tambahnya adalah perubahan pembacaan setelah oracle dikoreksi (R2). | 2024.findings-naacl.172; 2026.nllp-1.12 |
| Judul: "evidence grounding" terlalu luas | Judul menjadi *Auditing LLM Content Moderation for Identity-Term Dependence: Dual-Axis Metamorphic Testing of Rationale and Policy Sensitivity*; kata kunci "evidence grounding" diganti "annotator rationales"; konstruk di §3.1 menjadi "rationale sensitivity". | Judul, §3.1 |
| Interaksi teks × kebijakan tidak diuji | Ditambahkan sebagai keterbatasan (4) di §6. | §6 |
| Implikasi sosial | §5 menambahkan contoh flag → abstain (17 dari 18 pada Gemma 2 evidence) dan bahwa dampaknya bergantung pada cara platform merutekan abstensi, yang tidak diteliti. | §5 |

Kode yang berubah: `paper/gen_tables.py` (blok retensi, label strata), `paper/posthoc_e1_retention.py` (output ke `results/`), `paper/JSC_v25/build.sh` (urutan + v26), `paper/revisi_v25/verify_v25_revisions.py` (string v26), `tests/test_jsc_v3_reproducibility.py` (indeks kolom + tes retensi).

## Yang tidak bisa diselesaikan tanpa eksperimen baru (roadmap 2–3)

Repo sudah berisi **E1-CF v2** (`results/e1_counterfactual_v2/`): protokol draf dengan keputusan [DECIDE] yang sudah dicatat, item SWAP/SWAP2 antarkelompok terlindungi, dan workbook penilai untuk 256 pasangan dan 88 baris dasar (commit 2b28241–3417bcb). Itu persis yang diminta audit:

1. **Penilaian langsung 88 pasangan** (status pelanggaran, sasaran serangan, makna) pada REPLAY, NEU, dan PLC → isi workbook oleh dua penilai independen.
2. **Pertukaran antarkelompok terlindungi** → jalankan model pada item SWAP/SWAP2, lalu analisis H1–H3 sesuai protokol v2.

Sebelum panggilan model atau anotasi pertama, commit dan push `PROTOCOL.md` v2. Dengan begitu, klaim *pre-specified* untuk v2 bisa diperiksa dari riwayat git, tidak seperti v1.

**Rekomendasi:** v26 konsisten untuk klaim "efek penggantian istilah terhadap flag dan abstensi dalam sampel ini". Untuk target Q1, jalankan E1-CF v2 dulu.
