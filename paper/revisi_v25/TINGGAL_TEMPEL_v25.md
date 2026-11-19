# Tinggal tempel: etik, persetujuan penilai, acknowledgment, hash commit

Semua isi di bawah hanya memakai fakta yang tercatat di repo (`dokumentasi_penilai.xlsx`, lembar penilai `human_validation_round3_filled.xlsx`, `audit_report.md`). Tidak ada fakta yang ditambahkan.

## 0. Koreksi: apa yang benar-benar diwajibkan JSC (dibaca 19 Nov 2026)

Dari *Submission Guidelines*, *About Journal*, dan *Publishing Ethics* JSC di SciOpen:

| Hal | Status menurut halaman JSC |
|---|---|
| **Pernyataan persetujuan etik / IRB / consent penilai** | **Tidak disebut sebagai syarat.** "Wajib" yang saya tulis sebelumnya berasal dari temuan audit, bukan dari JSC. Satu catatan: *initial check* dapat menolak naskah yang "tidak memenuhi ... ethical requirements", tetapi syaratnya tidak dirinci di halaman itu (merujuk COPE). Formulir ScholarOne tidak bisa saya lihat tanpa login; kalau di sana ada kotak etik, ikuti isinya. |
| **Pendanaan** | Wajib diungkap: "give clear indication of research funding sources" (1.5) dan "all sources of financial support should be disclosed" (2.7). "Tidak ada dana" sudah memenuhi. |
| **Conflict of interest** | Wajib dinyatakan, boleh "The author(s) declare no conflicts of interest" (v24 sudah punya). |
| **Penggunaan AI** | Wajib diungkap **di cover letter saat submit** *dan* di Method/Acknowledgment/bagian terkait. v24 punya "Declaration of AI use"; cover letter belum ada. AI tidak boleh membuat atau mengubah data penelitian (v24 sudah menyatakan itu). |
| **Acknowledgment** | Pedoman: pihak non-penulis yang berpartisipasi substantif "should be named in an Acknowledgment section"; bantuan penilai termasuk. Bukan syarat keras, tetapi dianjurkan. |
| **Kemiripan teks** | Semua naskah diperiksa iThenticate. **Ditolak bila >30% mirip sumber lain atau >35% mirip karya penulis sebelumnya.** |
| **Daftar pustaka** | Minimal 10 referensi, bernomor sesuai urutan kutip. v24 memenuhi (28). |

**Akibatnya:** pernyataan etik di §5 tetap sebaiknya ada sebagai pengungkapan jujur (penilai membaca ujaran kebencian asli, dan reviewer bisa menanyakannya), tetapi **Versi A cukup**. Mengurus surat pembebasan etik bukan syarat JSC; itu pilihan untuk memperkuat naskah. Pilihan itu menjadi **opsional**, bukan penghalang submit.

## Fakta penilai yang terbukti di repo

| Fakta | Sumber |
|---|---|
| 2 penilai, rekan peneliti atau mahasiswa, **bukan penulis** | `dokumentasi_penilai.xlsx`, Isian 1-2 |
| Persiapan: **hanya petunjuk tertulis di lembar** (tidak ada briefing lisan, tidak ada formulir tanda tangan) | Isian 6 |
| Lembar memuat peringatan: "berisi ujaran kebencian dan kata kasar asli. Hanya untuk riset. Boleh berhenti dan istirahat kapan saja." | lembar `Petunjuk`, ronde 3 |
| Pemutus perbedaan = penulis pertama | Isian 4 |
| Persetujuan etik/pembebasan: **tidak ada di repo atau dokumen** | `reproducibility_notes.md`, audit #8 |

### Satu ketidakcocokan yang harus Mas pilih

`dokumentasi_penilai.xlsx` mencatat pemutus "memutuskan **tanpa** melihat jawaban penilai". Tetapi lembar `Keputusan` (kolom E-F) **menampilkan jawaban kedua penilai** di baris yang diputuskan, dan naskah v24 menulis "the decision sheet showed both answers". `reproducibility_notes.md` sendiri menandai klaim itu "to be confirmed".

**Pakai kalimat naskah v24** (pemutus melihat kedua jawaban): itu yang dapat dibuktikan dari struktur berkas. Jangan menulis "tanpa melihat" di naskah. Opsional: koreksi Isian 5 di `dokumentasi_penilai.xlsx` agar repo tidak bertentangan dengan naskah.

---

## 1. Pernyataan etik (ganti paragraf "Social computing and ethics" di §5)

Pilih **satu** versi. Versi A benar jika memang tidak ada surat etik. Versi B dipakai hanya setelah surat benar-benar ada.

**Versi A (sesuai bukti yang ada sekarang):**
```latex
\textbf{Social computing and ethics.} Moderation decides whose speech stays visible: if a verdict changes with the group named and nothing else, two communities get different protection from the same policy. We use a public dataset and create no new data about people. The items contain hateful language and are released for research use only; examples are masked. Two raters, research colleagues or students who are not authors, judged items that contain real hate speech. Their only preparation was the written instruction sheet, which stated that it held real hate speech and offensive words, that it was for research only, and that they could stop and rest at any time. No signed consent form was collected, and the study was not submitted to an institutional ethics committee. The risk to the raters is limited to exposure to offensive text, and no personal data about them is reported.
```

**Versi B (hanya jika ada surat pembebasan/persetujuan, lalu isi tanda kurung dari surat itu):**
```latex
\textbf{Social computing and ethics.} Moderation decides whose speech stays visible: if a verdict changes with the group named and nothing else, two communities get different protection from the same policy. We use a public dataset and create no new data about people. The items contain hateful language and are released for research use only; examples are masked. Two raters, research colleagues or students who are not authors, judged items that contain real hate speech. The rating sheet stated that it held real hate speech and offensive words, that it was for research only, and that they could stop and rest at any time. The [nama komite etik], Universitas Muhammadiyah Semarang, [approved / exempted] the study (ref.~[nomor surat], [tanggal surat]). The raters [confirmed in writing on [tanggal penandatanganan] that they had been informed and agreed to take part / ...sesuai isi dokumen].
```

Catatan jujur: Versi A mengungkap kekurangan apa adanya. Itu lebih aman daripada menulis persetujuan yang tidak ada, tetapi redaksi atau reviewer bisa meminta bukti etik. Cara yang memperkuat posisi: minta **surat pembebasan retrospektif** ke komite etik/LPPM UNIMUS (data publik, risiko minimal, penilai dewasa). Saya tidak bisa memastikan komite akan menerbitkannya.

## 2. Konfirmasi penilai (opsional, hanya sah bila ditandatangani penilai sungguhan)

Ini bukan "persetujuan yang dibuat mundur". Ini surat konfirmasi yang ditandatangani **pada tanggal tanda tangan sebenarnya**. Jangan diberi tanggal lama. Jika dipakai, Versi B menyebut tanggal itu.

```text
KONFIRMASI PENILAI

Saya, [nama penilai], menyatakan bahwa:
1. Saya menilai item validasi untuk penelitian "[judul naskah]" yang ditulis oleh Hilman Firdaus dkk.
2. Lembar penilaian memberi tahu saya bahwa teks berisi ujaran kebencian dan kata kasar asli, hanya untuk riset, dan bahwa saya boleh berhenti dan beristirahat kapan saja.
3. Saya menilai atas kemauan sendiri dan boleh menarik diri.
4. Saya bukan penulis naskah ini. Jawaban saya dipakai tanpa nama saya.
5. Saya mengizinkan / tidak mengizinkan* nama saya disebut di bagian Acknowledgment.   (*coret salah satu)

Tempat, tanggal penandatanganan: ____________
Tanda tangan: ____________
```

## 3. Acknowledgment (bagian baru, sebelum References)

Tidak ada dana: ditulis apa adanya. Nama penilai tidak disebut (belum ada izin tertulis); ganti jika mereka mengizinkan.
```latex
\section*{Acknowledgment}
This research received no external funding. We thank the two raters who judged the validation items.
```

## 4. Data and code availability (paragraf kedua)

Commit terverifikasi: `master` lokal = `origin/master`, 18 commit, HEAD **`4f5bc37`** ("perbaikan full", 19 Nov 2026 07:54 WIB), memuat `gen_tables.py`, `posthoc_e1_retention.py`, dan `paper/revisi_v25/`. GitHub juga menunjukkan 18 commit.
```latex
Items, prompts, raw responses, and analysis code are at \url{https://github.com/hilman-firdd/Reading-the-post-or-relying-on-indentity-cues} (commit 4f5bc37). Run~1, which all tables and figures report, is in \texttt{runs/} (main items) and \texttt{results/e1\_counterfactual/runs/} (counterfactual items). The uniform rerun of the first 822 Qwen2.5 direct items is \texttt{runs\_uniform/qwen2.5\_7b\_direct\_first822.jsonl}; repetitions 2 and 3, used only for the stability analysis, are in \texttt{runs\_repeat/} and \texttt{results/repeats/}. The counterfactual protocol is \texttt{results/e1\_counterfactual/PROTOCOL.md}, first committed in c60d6c4 (Section~3.7); its post hoc additions are listed in its Section~8.
```
**Bekukan hash ini di akhir.** Commit apa pun setelahnya (termasuk README) mengubah HEAD; kalau itu terjadi, ganti `4f5bc37` dengan hash terbaru.
File `*.tex` di-`.gitignore`, jadi `tab_*_body.tex` tidak ada di GitHub. Itu tidak masalah: `python3 paper/gen_tables.py . <folder>` membuatnya ulang dari data.

---

## 5. Yang masih kurang (urut)

1. **Sumber `.tex` v24.** Saya tidak punya file ini, jadi teks pengganti di `REVISI_v25_per_temuan.md` belum diterapkan. Unggah `.tex` (atau letakkan di folder `Moderation_Study_Kit`) dan saya terapkan, kompilasi, dan cek 12 halaman.
2. **Pilih Versi A atau B** untuk etik (§1). Versi A cukup bila tidak ada surat; JSC tidak mewajibkan surat etik (lihat bagian 0).
3. **Keputusan judul** (pedoman JSC: judul deskriptif, bukan kalimat tanya).
4. **Hapus Gambar 3** dan ubah Tabel 5 menjadi `table*` (ada di `REVISI_v25_per_temuan.md`, bagian "dua populasi E1").
5. **Jalankan** `verify_v25_revisions.py . body.tex` setelah semua penggantian; Part B harus lulus, termasuk "tidak ada placeholder tersisa".
6. **Saat submit**: DOI Zenodo (audit #8 sudah menunda), dan README berbahasa Inggris bila ingin dirujuk reviewer.
6a. **Cover letter** dengan pengungkapan penggunaan AI (syarat JSC, 7 Publishing Ethics) dan pernyataan naskah tidak sedang diajukan ke jurnal lain.
6b. **Cek similarity** sebelum submit (batas JSC 30%; skill `cek-similarity-maksimal-20` memakai 20% secara default, jadi lebih ketat).

## 6. File yang disiapkan untuk ScholarOne

Menurut pedoman JSC, naskah dikirim lewat ScholarOne (`mc03.manuscriptcentral.com/jsc-tup`). Yang diminta secara tertulis:

| File | Syarat | Status |
|---|---|---|
| Naskah (template JSC) | 10-12 halaman, dua kolom | v24 = 12 halaman; cek ulang setelah revisi |
| Gambar terpisah | **TIFF, EPS, atau JPEG**, disarankan 600 dpi, nomor dan keterangan di naskah | `paper/make_figs.py` menghasilkan png 600 dpi, jpg, dan eps: lengkap |
| Cover letter | Pengungkapan AI | belum ada |
| Foto penulis | Template biografi memakai foto | v24 sudah memuat 4 foto |

**Tidak diminta** oleh halaman JSC: surat etik, formulir persetujuan, ZIP repositori, atau data mentah. Data dan kode cukup lewat tautan GitHub di *Data and code availability*. Saya tidak bisa melihat kolom unggah ScholarOne tanpa login; kalau di sana ada kolom tambahan, ikuti isinya.
7. **Kesesuaian scope JSC**: satu kalimat bingkai sosial di Intro (sudah ada teksnya di `REVISI_v25_per_temuan.md`, §2.3).
8. Opsional: nama repo memuat salah ketik "indentity". Jika diganti di GitHub, perbarui URL di naskah.
