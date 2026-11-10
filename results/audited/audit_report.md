# Laporan Audit Forensik dan Re-evaluasi — Moderation Study Kit (llm600)

Tanggal audit: 2026-11-10 · Ruang lingkup: 6 run LLM (qwen2.5:7b, llama3.1:8b, gemma2:9b × prompt direct/evidence) dan 2 baseline (word-LR, char-LR) pada `items_llm600.jsonl` · Semua angka dapat direproduksi dengan `python audit_metrics.py` (lihat `reproducibility_notes.md`).

> **Status data.** `runs/` tidak diubah (SHA-1 setiap file run tercatat di `response_classification.json → systems`). Prompt eksperimen utama `p_direct` dan `p_evidence` identik dengan kit asli (diverifikasi melalui perbandingan AST terhadap `Moderation_Study_Kit.zip` dan commit `d79b9a2`). Tidak ada rerun. Semua keluaran baru ada di `results/audited/`.

---

## 0. Ringkasan eksekutif

1. **Refusal llama3.1 bukan abstention.** Dari 4.233 item, llama3.1 menolak 2.380 (56,2%; direct) dan 3.436 (81,2%; evidence). Kode lama memetakan penolakan menjadi `insufficient`, sehingga skor R1 llama3.1 evidence tampak 94,5%. Setelah audit, angkanya 4,8% bila penolakan dihitung tidak lulus, atau 46,8% abstensi di antara 62 respons yang benar-benar menjawab.
2. **Coverage dan akurasi bersyarat harus dilaporkan bersama.** Akurasi llama3.1 pada respons yang menjawab adalah 63,8% (n = 246) dan 63,2% (n = 76), bukan 26,2% dan 8,0%. Coverage-nya hanya 41,0% dan 12,7%, sehingga llama3.1 tidak dapat dibandingkan langsung dengan dua LLM lain.
3. **Tidak ada kondisi LLM yang lebih akurat daripada word-LR** pada postingan asli (ORIG). gemma2 evidence bahkan lebih buruk secara signifikan (−7,2 poin; Holm p = 0,017). Prompt *evidence* menurunkan akurasi gemma2 (−4,7 poin; Holm p < 0,001) dan tidak menaikkan akurasi qwen2.5 secara signifikan.
4. **Temuan terkuat (asosiasional):** setelah kata bukti dihapus (E1), LLM jauh lebih sering tetap menandai postingan yang masih memuat istilah identitas (OR 3,0–8,8; Holm p < 0,001). Efek ini bertahan setelah item yang dinilai manusia tidak valid dikeluarkan. Pada kedua baseline LR efek ini tidak ada (OR ≈ 1,2).
5. **I1 vs I2:** setelah koreksi Holm atas 8 sistem, hanya gemma2 direct yang signifikan (beda risiko +11,2 poin, CI95 [6,0; 17,2]; Holm p = 0,002). Baseline LR menunjukkan efek dengan besaran serupa (sekitar +10 poin; Holm p sekitar 0,07), dan hanya sekitar 48% item I1 yang valid. Klaim "bias sistematis" tidak dapat dipertahankan.
6. **Oracle R2:** kegagalan dramatis gemma2 pada kasus R2 ambigu (8,5% dan 0%) sebagian besar adalah artefak oracle. Dengan label hasil koreksi manusia, angkanya 76,3% dan 67,8%. Validitas R2 tertimbang hanya dapat diestimasi untuk strata offensive (0,599, CI95 [0,493; 0,704]). Strata hatespeech dan normal (400 item) tidak pernah divalidasi.
7. **I3 punya masalah konstruksi:** parafrase dibuat oleh gemma2 dan dinilai oleh qwen2.5, keduanya model yang dievaluasi. Selain itu, 98 item hilang secara tidak acak (χ² = 38,5; p = 4×10⁻⁹; condong ke hatespeech).

---

## 1. Integritas data dan perubahan kode

| Aspek | Status |
|---|---|
| `runs/*.jsonl` | Tidak diubah. 8 file × 4.233 baris, tanpa duplikat, dengan set item yang identik di semua sistem. |
| Respons mentah | Tersimpan di field `raw`. Klasifikasi audit hanya memakai `raw`. Field `verdict` yang tersimpan (hasil parser lama) disimpan berdampingan sebagai `stored_verdict`. |
| Prompt utama | Identik dengan kit asli (verifikasi AST). |
| Hasil lama | `results/_sebelum_refusal/` (sebelum penanganan refusal); `results/*.json` (refusal-aware dengan regex awal); `results/audited/` (**kanonis**). |
| Backup | `backup_20261109/`, `backup_20261110/` tidak disentuh. |
| Log perubahan kode | Lihat `reproducibility_notes.md §4`. |

**Bug dari auditor yang ditemukan dan diperbaiki sendiri.** Patch refusal pada `revise_eval.py` (2026-11-10) tanpa sengaja menjadikan `pairs.append(...)` sebagai komentar. Akibatnya bagian I1 vs I2 di `results/revised_llm600.json` sempat kosong. Bug ini sudah diperbaiki dan file dijalankan ulang; hasil qwen2.5, gemma2, dan LR identik dengan versi sebelum patch.

**Regex refusal awal terlalu longgar.** `relabel_refusals.py` menghitung 2.383 refusal llama3.1 direct. Classifier yang diaudit menemukan 2.380 refusal dan 3 abstensi teks bebas ("I cannot determine whether the post violates the content policy…"). Ketiganya masuk `manual_review_queue.csv`. `results/*.json` di luar `audited/` masih memakai label lama untuk ketiga item itu; gunakan `results/audited/` untuk naskah.

---

## 2. Audit forensik (ringkasan temuan)

| # | Temuan | Lokasi | Dampak | Keparahan |
|---|---|---|---|---|
| A1 | Refusal dan JSON rusak dilebur ke `insufficient` | `run_llm.py: parse()` (lama) | R1, abstensi, dan invariansi llama3.1 tidak sah | Kritis |
| A2 | Tidak ada coverage maupun akurasi bersyarat; refusal masuk denominator sebagai jawaban salah | `evaluate.py`, `revise_eval.py` | Perbandingan antar-model bias | Kritis |
| A3 | Oracle R2 lemah; strata hatespeech dan normal belum divalidasi | `build_items.py` R2 | R2 bukan bukti kepatuhan kebijakan | Tinggi |
| A4 | Item I1 hanya ~48% valid | `build_items.py` I1 | Flip bisa disebabkan teks yang janggal | Tinggi |
| A5 | I3 dibuat dan dinilai oleh model yang dievaluasi; item hilang secara tidak acak | `run_all.sh`, `run_llm.py paraphrase` | Sirkularitas dan bias seleksi | Tinggi |
| A6 | Uji I1 vs I2 tanpa koreksi multiplisitas | `revise_eval.py` | Signifikansi berlebih | Tinggi |
| A7 | Oracle E1 83,5% valid | E1 | Pass E1 terdistorsi | Sedang |
| A8 | Kondisi inferensi tidak seragam: 822 item awal qwen2.5 direct berurutan dengan konteks 4.096 tanpa batas token; sisanya 6 slot paralel, konteks 1.024, `max_tokens` 256 | `run_llm.py`, server Ollama | Ancaman reproduksibilitas; 2 respons gemma2 terpotong | Sedang |
| A9 | `GENERATION_ERROR` tidak dapat diamati: `call()` mencoba ulang 4 kali lalu menghentikan run tanpa menulis record | `run_llm.py: call()` | "0 error" adalah batas mekanisme pencatatan, bukan bukti tidak ada error | Sedang |
| A10 | Dua evaluator dengan definisi "pass" berbeda (`evaluate.py`: wajib dukungan bukti untuk E2 dan mencakup I3; `revise_eval.py`: hanya verdict, tanpa I3) | — | Naskah harus memilih dan menyebutkan definisinya | Sedang |
| A11 | R3 terkonfaund; EV3 dan profil mewarisi oracle yang tidak valid | `evaluate.py` | Skor komposit tidak dapat ditafsirkan | Sedang |
| A12 | Metadata run (digest model, konfigurasi server, waktu, `finish_reason`) tidak tersimpan per record | `run_llm.py` | Direkonstruksi di `reproducibility_notes.md` | Rendah–Sedang |

---

## 3. Klasifikasi respons (n absolut; denominator = 4.233 item per sistem)

| Sistem | VALID_VERDICT | ABSTENTION | REFUSAL | UNPARSEABLE | GENERATION_ERROR* | EMPTY |
|---|---|---|---|---|---|---|
| qwen2.5 direct | 4.001 | 230 | 0 | 2 | 0 | 0 |
| qwen2.5 evidence | 3.874 | 343 | 0 | 16 | 0 | 0 |
| llama3.1 direct | 1.836 | 17 | 2.380 | 0 | 0 | 0 |
| llama3.1 evidence | 765 | 32 | 3.436 | 0 | 0 | 0 |
| gemma2 direct | 3.891 | 340 | 0 | 2 | 0 | 0 |
| gemma2 evidence | 3.560 | 673 | 0 | 0 | 0 | 0 |
| word-LR / char-LR | 4.233 | — | — | — | — | — |

\* Lihat A9: error pemanggilan tidak tercatat per item. Nol berarti tidak ada record error, bukan bukti tidak ada error.

Rincian UNPARSEABLE:
- qwen2.5 evidence: 14 JSON tanpa key `verdict` dan 2 JSON rusak (tanda kutip dalam kutipan tidak di-escape).
- qwen2.5 direct: 2 JSON rusak.
- gemma2 direct: 2 JSON terpotong di 256 token (kutipan berulang).

Ke-20 kasus ini dan 3 abstensi teks bebas llama3.1 ada di `manual_review_queue.csv` (total 23). Verdict yang masih terbaca dari JSON rusak disimpan sebagai `recovered_verdict` dan hanya dipakai untuk analisis sensitivitas (`overall_acc_with_recovered_unparseable`).

Refusal llama3.1 per kelas gold: hatespeech 78% / 92%, offensive 50% / 81%, normal 41% / 70% (direct / evidence). Pada item E2 (postingan normal yang disisipi kata kasar), refusal mencapai 88% dan 98%.

---

## 4. Coverage dan akurasi bersyarat

**Postingan asli (ORIG, n = 600 postingan).** CI95 Wilson; unit = postingan.

| Sistem | Coverage (valid) | Akurasi bersyarat (valid) [CI95] | Akurasi keseluruhan (non-jawaban = salah) |
|---|---|---|---|
| qwen2.5 direct | 0,997 | 0,714 [0,677; 0,749] | 0,712 |
| qwen2.5 evidence | 0,980 | 0,748 [0,712; 0,782] | 0,733 |
| llama3.1 direct | 0,410 | 0,638 [0,577; 0,696] | 0,262 |
| llama3.1 evidence | 0,127 | 0,632 [0,519; 0,731] | 0,080 |
| gemma2 direct | 0,980 | 0,753 [0,717; 0,787] | 0,738 |
| gemma2 evidence | 0,938 | 0,737 [0,699; 0,772] | 0,692 |
| word-LR | 1,000 | 0,763 [0,728; 0,796] | 0,763 |
| char-LR | 1,000 | 0,743 [0,707; 0,777] | 0,743 |

**Seluruh item (4.233; CI95 dari cluster bootstrap per postingan).**
- Refusal: llama3.1 0,562 [0,534; 0,590] (direct) dan 0,812 [0,790; 0,832] (evidence); sistem lain 0.
- Coverage: qwen2.5 0,945 / 0,915; llama3.1 0,434 / 0,181; gemma2 0,919 / 0,841.
- Abstention: qwen2.5 0,054 / 0,081; gemma2 0,080 / 0,159.

Akurasi per kelas (abstensi dihitung salah), dalam persen hatespeech / offensive / normal:
- gemma2: 100 / 93,5 / **28,0** (direct) dan 100 / 94,5 / **13,0** (evidence). Ada bias kuat ke arah "melanggar".
- qwen2.5: 91 / 69 / 53,5 dan 93 / 76,5 / 50,5.
- word-LR: 89 / 64 / 76.

**Uji berpasangan pada ORIG** (McNemar eksak; beda risiko dengan CI bootstrap per postingan).

Keluarga F_P (evidence − direct, 3 model):

| Model | Beda risiko [CI95] | Holm p |
|---|---|---|
| qwen2.5 | +2,2 poin [−0,5; +4,8] | 0,148 |
| gemma2 | −4,7 poin [−6,8; −2,7] | < 0,001 |
| llama3.1 (semua postingan) | −18,2 poin | — (didorong refusal) |
| llama3.1 (76 postingan yang dijawab kedua prompt) | −11,8 poin [−21,1; −2,6] | 0,070 |

Keluarga F_B (LLM − word-LR, 6 kondisi):
- Tidak ada kondisi LLM yang lebih baik.
- gemma2 evidence lebih buruk: −7,2 poin [−12,0; −2,5]; Holm p = 0,017.
- qwen2.5 direct: −5,2 poin [−9,8; −0,5]; Holm p = 0,100.

---

## 5. Hasil per relasi metamorfik

### E1 — penghapusan bukti (397 postingan yang melanggar)

| Sistem | Pass ketat (dijawab) | Pass lenient (insufficient diterima) | Verdict "melanggar" dipertahankan (ORIG = melanggar) | Pindah ke tidak melanggar | Pindah ke insufficient | Oracle terkoreksi (n = 79) |
|---|---|---|---|---|---|---|
| qwen2.5 direct | 0,635 | 0,708 | 36,3% (115/317) | 54,9% | 8,8% | 0,582 |
| qwen2.5 evidence | 0,435 | 0,695 | 35,6% (119/334) | 38,6% | 25,8% | 0,519 |
| llama3.1 direct | 0,575 (n = 320) | 0,481 | 42,4% (36/85) | 55,3% | 2,4% | 0,576 (n = 59) |
| gemma2 direct | 0,232 | 0,521 | 49,5% (190/384) | 20,8% | 29,7% | 0,405 |
| gemma2 evidence | 0,098 | 0,557 | 45,6% (176/386) | 9,6% | 44,8% | 0,266 |
| word-LR | 0,509 | 0,509 | 61,7% (187/303) | 38,3% | — | 0,506 |
| char-LR | 0,698 | 0,698 | 39,9% (119/298) | 60,1% | — | 0,570 |

Batas sensitivitas oracle (kontaminasi maksimum = batas atas CI Wilson tingkat ketidakvalidan): gemma2 direct [0,08; 0,47], gemma2 evidence [0,05; 0,34]. Lihat `oracle_validity_analysis.csv`.

- **Revisi tafsiran.** Pass E1 gemma2 yang rendah bukan terutama karena model mempertahankan verdict "melanggar". Hanya sekitar 46–50% yang dipertahankan; 30–45% berpindah ke `insufficient`, yang ditolak oracle ketat.
- **Grounding.** Tidak ada sistem yang mengutip kata yang sudah dihapus (0 kasus). Kutipan non-verbatim ≤ 1,7%. Model tidak "mengarang" bukti yang sudah tidak ada.
- **Istilah identitas yang tersisa** (`statistical_analysis.json → E1_residual_identity_terms`; keluarga F_R, 8 uji Fisher, Holm):

| Sistem | Tetap ditandai: ada istilah identitas | Tetap ditandai: tanpa istilah identitas | OR | Holm p |
|---|---|---|---|---|
| gemma2 direct | 84,1% (74/88) | 37,5% (116/309) | 8,8 | < 10⁻⁶ |
| gemma2 evidence | 72,7% | 36,3% | 4,7 | < 10⁻⁶ |
| qwen2.5 evidence | 59,1% | 21,8% | 5,2 | < 10⁻⁶ |
| qwen2.5 direct | 48,9% | 23,6% | 3,1 | < 0,001 |
| llama3.1 direct (dijawab) | 71,7% (38/53) | 34,1% | 4,9 | < 0,001 |
| llama3.1 evidence (dijawab) | 50,0% (8/16) | 22,0% | 3,5 | 0,083 |
| word-LR | 52,3% | 48,2% | 1,18 | 1,0 |
| char-LR | 33,0% | 29,4% | 1,18 | 1,0 |

Efek ini bertahan bila 13 item E1 yang dinilai manusia tidak valid dikeluarkan (OR berubah < 0,1; llama3.1 evidence menjadi Holm p = 0,040). Pada sampel validasi, proporsi item tidak valid tidak berbeda nyata antara item dengan dan tanpa istilah identitas (4/17 vs 9/62; Fisher p = 0,46), tetapi kekuatan ujinya rendah.

### E2 — penyisipan bukti (200 postingan normal)

| Sistem | ORIG tidak melanggar → E2 melanggar | Kutipan mencakup kata sisipan | Oracle terkoreksi (n = 40) |
|---|---|---|---|
| qwen2.5 direct / evidence | 85,2% (92/108) / 91,7% (99/108) | 97,3% / 98,4% | 0,80 / 0,80 |
| llama3.1 direct | 66,7% (10/15) | 78,9% | 0,60 (n = 5) |
| gemma2 direct / evidence | 100% (67/67) / 100% (54/54) | 98,0% / 99,5% | 0,85 / 0,85 |
| word-LR / char-LR | 62,5% / 75,3% | 97,9% / — | 0,75 / 0,75 |

Pass E2 gemma2 (100%) harus dibaca bersama bias "melanggar"-nya. Hanya 67 dan 54 dari 200 postingan normal yang dinilai tidak melanggar pada ORIG, sehingga uji responsivitasnya hanya mencakup subset itu. llama3.1 evidence hanya menjawab 3 item E2, jadi tidak dapat ditafsirkan.

### R1 — kebijakan dihapus (benar = abstain)

Proporsi abstain di antara respons yang menjawab:
- qwen2.5: 0,32 / 0,29.
- gemma2: 0,21 / 0,35.
- llama3.1: 0,05 (n = 203) / 0,47 (n = 62). Selain itu ada 397 / 538 refusal dari 600.
- LR tidak dapat abstain secara konstruksi.

### R2 — kebijakan dipersempit

Nilai pass di antara respons yang menjawab, dengan oracle asli. Bagian "label berubah" adalah strata offensive (ambigu dan kontrol); "label tetap" adalah hatespeech dan normal.

| Sistem | Offensive ambigu (59) | Offensive kontrol (141) | Hatespeech (200) | Normal (200) | Oracle terkoreksi: ambigu (sensus) | Estimasi offensive tertimbang, terkoreksi |
|---|---|---|---|---|---|---|
| qwen2.5 direct | 0,356 | 0,723 | 0,790 | 0,720 | 0,729 | 0,744 |
| qwen2.5 evidence | 0,228 | 0,614 | 0,865 | 0,590 | 0,702 | 0,736 |
| llama3.1 direct | 0,600 (n = 15) | 0,689 (n = 74) | 0,778 (n = 18) | 0,757 | 0,733 | 0,720 |
| llama3.1 evidence | 0,500 (n = 8) | 0,730 (n = 37) | 0,800 (n = 5) | 0,742 | 0,625 | 0,607 |
| gemma2 direct | 0,085 | 0,213 | 1,000 | 0,330 | 0,763 | 0,527 |
| gemma2 evidence | 0,000 | 0,064 | 1,000 | 0,100 | 0,678 | 0,401 |
| word-LR | 0,322 | 0,376 | 0,890 | 0,760 | 0,627 | 0,462 |
| char-LR | 0,356 | 0,426 | 0,905 | 0,730 | 0,729 | 0,568 |

**Responsivitas kebijakan**, yaitu proporsi ORIG "melanggar" yang berubah menjadi "tidak melanggar" pada postingan offensive (ambigu / kontrol):
- qwen2.5 direct: 26% / 56%.
- gemma2 direct: 5% / 15%; gemma2 evidence: 0% / 5%.
- LR: 0% (pemeriksaan kewajaran, karena LR buta kebijakan).

Pada strata hatespeech dan normal, oracle tidak tervalidasi, sehingga nilai terkoreksinya tidak teridentifikasi (batas [0; 1]).

### R3 — kebijakan dinegasikan

Perubahan verdict terhadap ORIG di antara pasangan yang dijawab: qwen2.5 11,3% / 11,4%, llama3.1 12,7% / 13,3%, gemma2 5,3% / 4,8%, LR 0%.

Pass R3 (23–37%) sebagian besar terjadi **tanpa** perubahan verdict. Pada qwen2.5 direct, 132 dari sekitar 161 pass berasal dari postingan yang verdict ORIG-nya salah. Pass R3 karena itu bukan ukuran kepatuhan kebijakan; yang relevan adalah tingkat perubahan verdict.

### I1 vs I2 — tukar kelompok vs kalimat netral (134 postingan)

Keluarga F_I terdiri dari 8 uji (satu per sistem), dengan McNemar eksak berpasangan per postingan dan koreksi Holm. Flip didefinisikan sebagai verdict yang berbeda dari verdict ORIG sistem yang sama, dan hanya pada postingan di mana ORIG, I1, dan I2 semuanya dijawab.

| Sistem | Triple lengkap | Flip I1 | Flip I2 | Beda risiko [CI95] | OR b/c [CI95 eksak] | p | Holm p | Holm p tanpa I1 tidak valid (n = 120) |
|---|---|---|---|---|---|---|---|---|
| gemma2 direct | 134 | 13,4% | 2,2% | +11,2 [6,0; 17,2] | 16,0 [2,5; 671] | 0,0003 | **0,002** | **0,004** |
| gemma2 evidence | 134 | 11,2% | 3,0% | +8,2 [3,0; 14,2] | 4,7 [1,3; 25] | 0,013 | 0,076 | 0,074 |
| word-LR | 134 | 17,9% | 7,5% | +10,4 [3,0; 17,9] | 3,3 [1,3; 10] | 0,009 | 0,065 | 0,074 |
| char-LR | 134 | 14,9% | 5,2% | +9,7 [3,0; 17,2] | 3,2 [1,2; 9,7] | 0,015 | 0,076 | 0,074 |
| qwen2.5 direct | 134 | 11,9% | 9,0% | +3,0 [−3,0; 9,0] | 1,7 [0,5; 5,6] | 0,45 | 0,91 | 1,0 |
| qwen2.5 evidence | 133 | 15,0% | 9,8% | +5,3 [−2,3; 12,8] | 1,7 [0,7; 4,2] | 0,25 | 0,74 | 0,92 |
| llama3.1 direct | 41 (31%) | 19,5% | 4,9% | +14,6 [2,4; 26,8] | 7,0 [0,9; 315] | 0,070 | 0,28 | 0,28 |
| llama3.1 evidence | 6 (4%) | — | — | tidak dapat ditafsirkan | — | — | — | — |

- **Arah perubahan (gemma2 direct):** 16 dari 18 flip I1 bergerak dari "melanggar" ke "tidak melanggar" (12) atau "insufficient" (4), dan 14 di antaranya menjauh dari verdict ORIG yang benar. Akurasi terhadap oracle: I1 0,746 vs I2 0,836.
- **Pada item I1 yang divalidasi manusia (deskriptif):** gemma2 direct flip 2 dari 13 item valid dan 1 dari 14 item tidak valid.

### I3 — parafrase

| Sistem | Flip semua (n) | Judge setara | Judge tidak setara | Valid menurut manusia | I3 − I2 berpasangan [CI95] |
|---|---|---|---|---|---|
| qwen2.5 direct | 20,2% (500) | 18,7% | 23,2% | 19,2% (73) | +10,6 [6,6; 14,8] |
| qwen2.5 evidence | 22,8% (496) | 23,0% | 22,4% | 26,8% (71) | +11,9 [7,5; 16,3] |
| llama3.1 direct | 32,0% (206) | 30,3% | 37,0% | 34,6% (26) | +21,4 [14,1; 28,7] |
| gemma2 direct | 18,1% (502) | 18,3% | 17,8% | 19,2% (73) | +12,6 [9,2; 15,9] |
| gemma2 evidence | 17,1% (502) | 18,6% | 14,2% | 16,4% (73) | +13,9 [10,6; 17,3] |
| word-LR | 31,5% (502) | 32,1% | 30,2% | 32,9% (73) | +23,7 [19,1; 28,3] |
| char-LR | 32,3% (502) | 31,5% | 33,7% | 35,6% (73) | +25,5 [20,9; 29,9] |

- **Bias seleksi:** 98 item I3 tidak punya teks (59 hatespeech, 22 offensive, 17 normal; χ² = 38,5, df = 2, p = 4×10⁻⁹). Postingan yang paling ofensif kurang terwakili.
- **Sirkularitas:** gemma2, pembuat parafrase, memiliki flip I3 terendah di antara sistem dengan coverage tinggi. Tetapi selisih I3 − I2-nya (+12,6 dan +13,9) serupa dengan qwen2.5 (+10,6 dan +11,9), sehingga tidak ada bukti jelas keuntungan "parafrase sendiri". qwen2.5, sang judge, tidak menunjukkan pola konsisten antara subset setara dan tidak setara. Pemeriksaan ini deskriptif dan tidak dapat menyingkirkan sirkularitas.
- **Item pending (34250a0a4de0):** mengubah tingkat invariansi I3 pada subset yang valid menurut manusia ≤ 1,1 poin, apa pun keputusannya (`pending_item_sensitivity`). Untuk sementara item ini dikeluarkan dari semua analisis yang membutuhkan label final.

---

## 6. Validasi manusia dan validitas oracle

| Aspek | Status |
|---|---|
| Jumlah penilai | 2 (+ pemutus untuk ketidaksepakatan) |
| Identitas dan latar belakang | **not documented** |
| Prosedur | Dropdown Ya/Tidak per item (`hitl_sheet.py`), kriteria tertulis di lembar `Petunjuk` |
| Independensi | **not enforced / not documented**: kedua lembar ada di satu workbook |
| Pemutus | **not documented** |
| Kesepakatan | 333 item; 92,2% sepakat; Cohen's κ = 0,823 (CI95 cluster bootstrap [0,753; 0,886]); 26 tidak sepakat, 25 sudah diputuskan, 1 pending |
| κ per MR | E1 0,735 [0,524; 0,894]; E2 0,828 [0,538; 1,0]; R2 0,749 [0,600; 0,884]; I1 1,0 (n = 27); I3 0,848 [0,718; 0,951] |

| MR / strata | N populasi | n disampel | Desain | Validitas [CI95] |
|---|---|---|---|---|
| E1 | 397 | 79 | acak 20% | 0,835 [0,739; 0,901] |
| E2 | 200 | 40 | acak 20% | 0,850 [0,709; 0,929] |
| I1 | 134 | 27 | acak 20% | 0,481 [0,307; 0,660] |
| I3 | 502 | 100 (99 sudah diputuskan) | acak 20% | 0,737 [0,643; 0,814] (sensitivitas pending: 0,730–0,740) |
| R2 offensive ambigu | 59 | 59 | sensus | 0,322 [0,217; 0,449] |
| R2 offensive kontrol | 141 | 28 | acak 20% | 0,714 [0,529; 0,848] |
| R2 offensive (tertimbang) | 200 | 87 | bobot N_h/N, dengan FPC | 0,599 [0,493; 0,704] |
| R2 hatespeech / normal | 200 / 200 | 0 | tidak divalidasi | **tidak teridentifikasi** |

Angka 44,8% di `validation.json` adalah rata-rata tanpa bobot dari sensus kasus ambigu dan sampel kontrol yang kecil. Angka itu tidak menggambarkan R2 secara keseluruhan dan tidak boleh dilaporkan sebagai validitas R2.

---

## 7. Perbandingan sebelum dan sesudah audit

Detail per sistem ada di `before_after.csv`.

| ID | Temuan awal | Hasil audit | Perubahan | Alasan metodologis | Dampak pada naskah |
|---|---|---|---|---|---|
| F1 | Akurasi llama3.1 26,2% / 8,0% | Akurasi bersyarat 63,8% / 63,2%; coverage 41,0% / 12,7% | +37,7 / +55,2 poin (metrik berbeda) | Refusal bukan jawaban salah; laporkan coverage dan akurasi bersyarat bersama | llama3.1 tidak dibandingkan langsung; refusal menjadi temuan tersendiri |
| F2 | R1 llama3.1 evidence 94,5% ("terbaik") | 4,8% bila refusal dihitung tidak lulus; abstain 46,8% dari 62 respons yang menjawab | −89,7 poin | Refusal tercatat sebagai `insufficient` | Klaim gugur |
| F3 | Invariansi I1/I2 llama3.1 80–90% | Flip dihitung hanya pada pasangan yang dijawab; coverage triple 31% / 4% | Tidak dapat dibandingkan | Refusal = refusal sempat dihitung "konsisten" | Klaim gugur |
| F4 | gemma2 direct I1 vs I2 p = 0,000275 | Holm p = 0,002; beda risiko +11,2 [6,0; 17,2] | Tetap signifikan | Koreksi untuk keluarga 8 uji | Bertahan, dengan tafsiran yang dibatasi |
| F5 | gemma2 evidence, word-LR, char-LR p < 0,05 | Holm p = 0,065–0,076 | Tidak lagi signifikan | Multiplisitas | Direvisi |
| F6 | Validitas oracle R2 44,8% | Offensive tertimbang 0,599; hatespeech dan normal tidak teridentifikasi | +15,1 poin (cakupan berbeda) | Desain sampling bertingkat | Direvisi |
| F7 | gemma2 gagal mengikuti kebijakan sempit (R2 ambigu 8,5% / 0%) | Oracle terkoreksi 76,3% / 67,8%; offensive tertimbang 52,7% / 40,1% | Besar | 68% label acuan kasus ambigu ditolak manusia | Direvisi besar |
| F8 | E1 gemma2 23,2% / 9,8% ("tetap menandai melanggar") | Mempertahankan "melanggar" 49,5% / 45,6%; sisanya banyak berpindah ke insufficient; oracle terkoreksi 40,5% / 26,6% | +17,3 / +16,8 poin | Abstensi dihitung gagal oleh oracle ketat, dan 16,5% oracle E1 salah | Direvisi |
| F9 | Abstensi qwen2.5 / gemma2 = jumlah `insufficient` yang tersimpan | 2–16 item per sistem dipindah ke UNPARSEABLE | Kecil | JSON rusak bukan abstensi | Kategori dikoreksi |
| F10 | Refusal llama3.1 direct 2.383 | 2.380 refusal + 3 abstensi | −3 | Regex awal terlalu longgar | Minor |
| F11 | I3 "tidak dievaluasi" (`revise_eval.py`), tetapi masuk EV3 (`evaluate.py`) | Dianalisis per kelompok; ada bias seleksi dan risiko sirkularitas | Baru | Konstruksi dataset | Perlu caveat besar atau eksperimen ulang |
| F12 | (ringkasan sebelumnya) "LLM gagal mengikuti bukti pada E1" | Asosiasi dengan istilah identitas yang tersisa kuat pada LLM dan tidak ada pada LR | Baru | Analisis residual yang sadar refusal, dengan sensitivitas oracle | Temuan inti, tetapi asosiasional |

---

## 8. Keputusan llama3.1

Keputusan peneliti: **opsi A**, yaitu llama3.1 tetap di eksperimen utama dengan refusal sebagai kategori terpisah. Evaluasi ketiga opsi untuk dokumentasi:

| Kriteria | A. Pertahankan, refusal terpisah | B. Prompt berkonteks riset (kondisi baru) | C. Ganti model |
|---|---|---|---|
| Validitas eksperimen | Tinggi untuk pertanyaan "bagaimana perilaku model di bawah prompt yang sama"; rendah untuk akurasi llama3.1 (coverage 13–41%) | Mengukur model dengan instruksi berbeda; perlu dilabeli sebagai kondisi baru | Menghilangkan masalah, tetapi juga temuan refusal |
| Komparabilitas | Hanya pada respons yang menjawab (bias seleksi: refusal lebih sering pada hatespeech) | Tidak sebanding dengan kondisi utama | Sebanding bila prompt sama |
| Reproduksibilitas | Penuh (tanpa rerun) | Perlu dokumentasi prompt tambahan | Run baru |
| Kontribusi | Refusal sebagai temuan: 56–81%, terbanyak pada hatespeech, yaitu tepat pada kasus yang ingin dimoderasi | Menunjukkan apakah framing mengubah refusal | Kecil |
| Biaya | 0 | ≈ 2,5–3 jam (waktu run nyata llama3.1: 1 jam 23 menit + 1 jam 16 menit) | ≈ 3–7 jam per model |
| Ancaman | Akurasi bersyarat dihitung atas subset non-acak | Prompt yang berbeda dapat dikritik sebagai jailbreak | Kehilangan model populer |

Pernyataan untuk naskah: refusal adalah perilaku yang **teramati pada konfigurasi ini** (llama3.1:8b, digest 46e0c10c039e, Ollama 0.33.3, temperature 0, prompt kit) dan tidak boleh digeneralisasi sebagai karakteristik universal llama3.1. Opsi B **tidak dijalankan**; hanya diusulkan sebagai eksperimen tambahan yang menunggu persetujuan.

---

## 9. Threats to validity

- **Construct.**
  - "Pass" mencampur kepatuhan, kemampuan abstain, dan format.
  - R3 terkonfaund.
  - I1 hanya ~48% item valid, sehingga I1 lebih mengukur sensitivitas leksikal daripada bias sosial.
  - E1 dan E2 dibatasi oleh rationale anotator: penghapusan bisa meninggalkan serangan (16,5%), dan sisipan bisa tidak berbahaya di luar konteks (15%).
- **Internal.**
  - Kondisi inferensi tidak seragam (A8).
  - Hanya satu run per kondisi (tidak ada estimasi nondeterminisme, meski temperature 0).
  - Error pemanggilan tidak tercatat (A9).
  - Batas 256 token memotong 2 respons.
- **External.**
  - 3 model lokal 7–9B, kuantisasi bawaan Ollama, satu dataset (HateXplain, berbahasa Inggris, Twitter/Gab), dan 600 postingan dengan kelas seimbang (bukan prevalensi nyata).
- **Statistical conclusion.**
  - Unit sudah benar (postingan) dan Holm diterapkan per keluarga yang didefinisikan (F_I, F_P, F_B, F_R).
  - Tetapi banyak perbandingan deskriptif lain tidak dikoreksi.
  - n untuk validasi I1 (27) dan E2 (40) kecil.
  - OR dengan c = 1 sangat tidak presisi (CI sampai 671).
- **Oracle.**
  - Strata R2 hatespeech dan normal tidak divalidasi.
  - Hanya 20% item yang divalidasi; item yang belum divalidasi tidak dianggap valid, tetapi dianalisis dengan oracle asli disertai batas sensitivitas.
- **Konstruksi dataset (I3).** Pembuat parafrase dan judge adalah model yang dievaluasi; item yang hilang tidak acak.
- **Validasi manusia.** Identitas, keahlian, dan independensi penilai tidak terdokumentasi.
- **Reproduksibilitas.** Metadata per record tidak lengkap. Commit HateXplain tidak tercatat (hanya SHA-1 `dataset.json`).

---

## 10. Interpretasi ilmiah (dibatasi oleh data)

1. **Evidence responsiveness ≠ evidence grounding.**
   - E2 menunjukkan keduanya tinggi: verdict berubah ke "melanggar" dan kutipannya memuat kata sisipan (≥ 97% untuk qwen2.5 dan gemma2).
   - E1 menunjukkan responsivitas yang lemah tanpa kutipan palsu: model tidak mengutip kata yang sudah dihapus, tetapi 36–50% tetap memvonis "melanggar".
2. **Penghapusan dan penambahan bukti tidak simetris.** Menambah kata kasar hampir selalu mengubah verdict; menghapusnya tidak.
3. **Istilah identitas yang tersisa.** Pada LLM, keputusan "tetap melanggar" setelah penghapusan berasosiasi kuat dengan istilah identitas yang tersisa (OR 3–9). Pada LR asosiasi itu tidak ada. Uji kontrafaktual E1-CF (`results/e1_counterfactual/`, protokol dikunci sebelum data) **mendukung peran kausal istilah identitas** pada qwen2.5 dan gemma2: mengganti istilah identitas dengan "people/person" menurunkan tingkat penandaan 17–25 poin dibanding placebo (Holm p ≤ 0,012 di keempat kondisi; tidak ada efek pada LR). Yang ditunjukkan adalah **ketergantungan verdict pada istilah identitas**, bukan bahwa model "mengingat stereotip": penurunan juga diharapkan secara sah karena atribut terlindungi hilang dari teks. Klaim ketergantungan yang tidak sah memerlukan pemeriksaan manusia apakah sisa teks tanpa istilah identitas masih berisi serangan.
4. **Sensitivitas cakupan kebijakan.**
   - qwen2.5 merespons kebijakan sempit (26–56% switch pada offensive); gemma2 hampir tidak (0–15%).
   - Besarnya kegagalan bergantung kuat pada validitas oracle. Klaim harus memakai estimasi terkoreksi (offensive tertimbang: qwen2.5 0,74 vs gemma2 0,40–0,53).
5. **Sensitivitas kelompok.** Hanya gemma2 direct yang menunjukkan flip I1 > I2 setelah koreksi. Besaran yang serupa pada LR menandakan bahwa perubahan istilah leksikal saja sudah cukup mengubah keputusan. Ini bukan bukti diskriminasi sistematis, dan item I1 separuhnya tidak valid.
6. **Refusal pada konten sensitif.** Refusal llama3.1 paling sering terjadi pada hatespeech (78–92%), yaitu kasus yang paling perlu dimoderasi. Model yang sering menolak **tidak** lebih aman; ia tidak menjalankan tugas moderasi.
7. **LLM vs LR.** Tidak ada keunggulan akurasi LLM. LR lebih stabil terhadap kebijakan secara konstruksi (karena buta kebijakan) dan tidak menunjukkan efek istilah identitas residual, tetapi tidak bisa abstain dan tidak responsif kebijakan. Model yang paling akurat belum tentu paling dapat dipercaya, dan model yang tidak berubah responsnya belum tentu robust.
8. **Kualitas oracle** mengubah kesimpulan secara material (R2, E1, I1). Validitas oracle harus menjadi bagian utama naskah, bukan catatan kaki.

---

## 11. Tinjauan independen (standar Q1/Q2)

**Findings that remain valid**
- Refusal llama3.1 56% / 81% dalam konfigurasi ini, terkonsentrasi pada hatespeech.
- LLM tidak lebih akurat daripada word-LR; gemma2 evidence lebih buruk (Holm p = 0,017).
- Prompt evidence menurunkan akurasi gemma2 (−4,7 poin) dan tidak meningkatkan qwen2.5 secara signifikan.
- E2: responsivitas dan grounding tinggi untuk qwen2.5 dan gemma2.
- E1: asosiasi istilah identitas residual pada LLM (robust terhadap sensitivitas oracle dan koreksi Holm), tanpa efek pada LR; uji kontrafaktual E1-CF (n = 88 postingan) mendukung ketergantungan kausal verdict pada istilah identitas untuk qwen2.5 dan gemma2.
- Bias "melanggar" gemma2 pada postingan normal.

**Findings that require revision**
- E1 gemma2: sebagian besar "kegagalan" berupa abstensi, dan besarnya bergantung pada oracle.
- R2: gunakan nilai terkoreksi dan tertimbang; jangan memakai oracle asli pada kasus ambigu.
- I1 vs I2: hanya gemma2 direct yang signifikan; tafsirkan sebagai sensitivitas leksikal kelompok, dengan pembatasan validitas item.
- Akurasi llama3.1: laporkan coverage dan akurasi bersyarat.

**Findings that are no longer defensible**
- R1 llama3.1 94,5% dan invariansi I1/I2 llama3.1 80–90%.
- "Validitas oracle R2 = 44,8%" sebagai pernyataan untuk R2.
- Pass R3 sebagai ukuran kepatuhan kebijakan.
- Klaim bias atau diskriminasi sistematis berdasarkan flip I1.
- Skor komposit EV3 dan profil (Faithful/Policy-blind/…) dari `evaluate.py` yang memuat komponen dengan oracle tidak valid (R2, R3, I1, I3) dan belum diturunkan ulang.

**Findings requiring additional experiments**
- ~~Kausalitas efek istilah identitas residual (E1)~~ — dijalankan (E1-CF, SUPPORT menurut aturan keputusan); yang masih terbuka adalah apakah ketergantungan itu tidak sah (perlu pemeriksaan manusia atas sisa teks).
- Invariansi parafrase (I3) tanpa sirkularitas.
- Validitas R2 di strata hatespeech dan normal.
- Stabilitas antar-run.
- Generalisasi ke model lain (4–6 model).

**Kesiapan publikasi.** **Belum siap** untuk jurnal Q1. Dengan revisi besar, berpotensi untuk Q2. Kontribusinya (kerangka MR dua sumbu, evaluasi yang sadar refusal dan validitas oracle, dan asosiasi istilah identitas residual) bernilai. Penghambat utamanya:
1. Validitas oracle R2, I1, dan I3 rendah atau tidak teridentifikasi.
2. I3 sirkular.
3. Hanya tiga model kecil, masing-masing satu run.
4. Klaim inti E1 kini didukung kontrafaktual, tetapi tafsir "tidak sah" (stereotip) belum diuji; n = 88 postingan, 3 model kecil.
5. Dokumentasi penilai kosong.
6. Skor komposit belum diturunkan ulang.

Reviewer Q1 hampir pasti meminta setidaknya poin 1, 3, dan 4.

---

## 12. Rekomendasi eksperimen tambahan (urut prioritas; semua menunggu persetujuan)

1. **Kontrafaktual E1:** ganti atau hapus istilah identitas yang tersisa pada item E1 (misalnya diganti dengan kata benda netral), lalu bandingkan tingkat "tetap ditandai". Ini menguji kausalitas temuan inti. Biaya: hanya E1 (397 item × 6 kondisi), sekitar 2–3 jam.
   **Status:** disetujui peneliti pada 2026-11-10. Protokol (hipotesis, kondisi placebo, metrik utama, aturan keputusan) dikunci di `results/e1_counterfactual/PROTOCOL.md` **sebelum** pengumpulan data, dan dijalankan pada 88 postingan E1 yang masih memuat istilah identitas. Hasilnya ada di `results/e1_counterfactual/`. Klaim utama paper **ditunda** sampai hasil ini dievaluasi dengan aturan keputusan yang sudah ditetapkan.
2. **Validasi oracle tambahan:** sampel 20% strata R2 hatespeech dan normal (80 item) dan seluruh 134 item I1. Alternatifnya, bangun ulang I1 dengan pasangan tukar yang dikurasi manusia.
3. **I3 tanpa sirkularitas:** parafrase oleh keluarga model yang tidak dievaluasi (misalnya Mistral) atau oleh manusia; rerun hanya I3.
4. **Stabilitas:** ulangi satu kondisi (misalnya qwen2.5 direct) pada subset 600 item dengan konfigurasi server yang sama untuk mengukur nondeterminisme.
5. **Model tambahan** (target 4–6 model) dan pencatatan metadata per record (digest, waktu, `finish_reason`, error).
6. **llama3.1 dengan prompt berkonteks riset** sebagai kondisi terpisah dan berlabel (opsional, sekitar 2,5–3 jam).
7. **Dokumentasi penilai:** latar belakang, pelatihan, independensi, dan identitas pemutus.
