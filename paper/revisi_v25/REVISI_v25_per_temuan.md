# JSC v24 → v25: perbaikan per temuan audit #9, konsistensi aim, dan kelayakan

Disusun 19 Nov 2026 dari: PDF v24 (12 halaman), repositori `Moderation_Study_Kit` (HEAD `654c666`), template LaTeX JSC, dan halaman *Aims and Scope* serta *Submission Guidelines* JSC di SciOpen.

**Batas pekerjaan ini.** Sumber `.tex` v24 tidak ada di repositori (di-*gitignore*) dan folder induknya tidak dapat saya akses. Karena itu dokumen ini memberi **teks pengganti LaTeX per lokasi** (cari → ganti), sedangkan **badan tabel diregenerasi dari data** (`tab_*_body.tex` di folder ini). Semua angka baru diperiksa ulang oleh `verify_v25_revisions.py` (41 cek, `FAILS: []`). Saya tidak mengisi apa pun yang tidak ada di repo/dokumen: etik, persetujuan penilai, pendanaan, dan nama penilai tetap berupa placeholder untuk penulis.

---

## 0. Putusan kelayakan (jujur)

| Aspek | Status setelah v25 | Catatan |
|---|---|---|
| Konsistensi angka & denominator | **Siap**, bila semua penggantian di bawah diterapkan | Semua angka baru dihitung ulang dari `results/`; tidak ada angka yang dikarang. |
| Konsistensi aim ↔ klaim | **Siap**, setelah pertanyaan riset di Intro diubah (§2) | Versi v24 bertanya soal cue yang “*should not need*”, padahal kesimpulan menyatakan tidak bisa menunjukkan *unjustified*. |
| Pedoman JSC (format) | **Hampir**: halaman 12 (batas 10–12), abstrak 150 kata, 6 kata kunci, ≥10 referensi, ada Intro/Methods/Results/Discussion/Conclusions | Kurang: **Acknowledgment** (wajib menurut pedoman bila ada pihak non-penulis yang berkontribusi, yaitu penilai, dan untuk pendanaan); **Tabel 5 vs Gambar 3 berduplikasi** setelah 2×2 ditambahkan (dilarang pedoman) → hapus Gambar 3; **judul berbentuk pertanyaan** (pedoman: “descriptive, not full sentences”); singkatan **word-LR** tak terdefinisi di abstrak. |
| Kesesuaian *Aims and Scope* | **Cukup, belum kuat** | JSC mencari riset di antarmuka interaksi sosial dan komputasi (computational social science, complex social systems, HCI). Naskah ini terutama metodologi pengujian. Bingkai sosial (siapa yang dilindungi kebijakan moderasi) hanya ada di satu paragraf §5; perlu dinaikkan ke Intro (§2.3). |
| **Gerbang yang tidak bisa saya selesaikan** | **Belum siap submit** | (1) pernyataan etik dan bentuk persetujuan penilai, (2) Acknowledgment: nama penilai (dengan izin mereka) dan pendanaan, (3) hash commit rilis akhir. Tanpa (1), naskah **tidak layak dikirim**. |

**Kesimpulan:** secara ilmiah naskah layak diajukan ke JSC **sebagai studi kasus diagnostik dengan klaim sempit**, setelah revisi ini dan setelah etik diisi berdasarkan dokumen resmi. Risiko utama di review: kecocokan scope (mitigasi §2.3) dan permintaan reviewer untuk E1-CF v2 (rating makna/relevansi kebijakan pada 88 pasangan), yang memang sudah dinyatakan sebagai keterbatasan.

---

## 1. Rekonsiliasi angka (diverifikasi dari data)

| Temuan audit | Hasil cek di repo | Sumber |
|---|---|---|
| Tabel 7 R2: 76,3/67,8 (Gemma 2) dan 72,9/70,2 (Qwen2.5) | **Benar: kolom R2 corr. = 59 post ambigu**, bukan estimasi berbobot. Kolom berbobot (200 post ofensif): Gemma 2 **52,7/40,1**, Qwen2.5 **74,4/73,6**. Selisih berasal dari 141 post ofensif lain (28 dinilai): Gemma 2 **42,9/28,6**, Qwen2.5 **75,0/75,0**. Bobot 59/200 dan 141/200 mereproduksi nilai berbobot. | `oracle_validity_analysis.csv` |
| Tabel 6: n H1 vs n S1 Llama direct | **Benar: n H1 = 52, n S1 = 47.** Llama evidence 12/12; sistem lain 88/88. S1 punya keluarga Holm sendiri (`F_CF2`). | `e1_counterfactual/analysis.json` |
| Penanganan non-jawaban E1-CF | Pasangan = kedua teks dijawab (verdict valid atau abstensi); abstensi = tidak di-flag. Di E1-CF **tidak ada** output unparseable, error, atau kosong; satu-satunya non-jawaban adalah **refusal Llama 3.1** (466 respons). | `PROTOCOL.md` §4; klasifikasi ulang `runs/` |
| Pembulatan RD | RD dari nilai tersimpan 4 desimal → dobel pembulatan. Dari hitungan mentah: Qwen2.5 evidence **(20−5)/88 = 17,0** (v24: 17,1); Llama direct **(13−2)/52 = 21,2** (v24: 21,1). `gen_tables.py` sekarang mencetak RD = (b−c)/n. | — |
| Akurasi Llama 3.1 | **Llama masuk uji overall accuracy (F_B, 6 uji)**: RD −50,2 dan −68,3 poin terhadap word-LR, Holm p < 0,001. Yang tidak dibandingkan hanyalah *conditional accuracy* (246 dan 76 verdict valid). | `statistical_analysis.json` → `llm_vs_wordLR_ORIG` |
| Tabel 5: dua populasi | n/Kept/To not/To ins. = post ORIG violating dan E1 dijawab; OR = semua E1 dijawab. 2×2 OR sekarang dicetak di tabel. Analisis retensi (post hoc, populasi kiri): OR **6,1–10,6** untuk Qwen2.5/Gemma 2 (Holm p < 0,001), Llama direct **7,2** (Holm 0,004); **word-LR 2,1, char-LR 1,8** (Holm 0,076 dan 0,100). | `posthoc_e1_retention.json` (baru) |
| I1–I2 dan Llama evidence | `F_I` = 8 sistem **termasuk** Llama evidence (6 triple, tidak ada pasangan discordant, McNemar p = 1, Holm p = 1). | `I1_vs_I2.main` |
| Valid-only | File hanya berisi **H1**; **S1 tidak pernah dihitung** pada subset ini → aturan keputusan tidak bisa “still holds”. Pasangan 84/73/64/51; Holm signifikan 3 dari 4. | `posthoc_valid_only.json` |
| Protokol pre-specified | `PROTOCOL.md` menyatakan “fixed before any model call (2026-11-10)”; `run.log` mencatat panggilan LLM E1-CF pertama **10 Nov 05:18:30**; tetapi file **pertama kali di-commit 16 Nov (`c60d6c4`)**, setelah run. Urutan waktu hanya bertumpu pada tanggal di file dan log, **tidak bisa dibuktikan dari riwayat git**. | `git log`, `run.log` |

**Implikasi penting dari analisis retensi** (harus ditulis, bukan disembunyikan): pada populasi retensi, classifier menunjukkan asosiasi lemah (OR ~2, tidak signifikan setelah Holm). Kalimat Diskusi v24 “*tied to a remaining identity term in LLMs but not in the classifiers*” terlalu kuat; diganti “*far more strongly in LLMs than in the classifiers*”.

---

## 2. Konsistensi fokus dan aim

### 2.1 Pertanyaan riset (Intro) — inkonsistensi utama

v24 bertanya “*does it depend on a cue it should not need?*”. Frasa *should not need* mengandaikan ketergantungan itu tidak beralasan, padahal Diskusi, Threats, dan Kesimpulan menyatakan hal itu **tidak** ditunjukkan. Aim harus sejajar dengan apa yang bisa dijawab.

**Cari (Intro, par. 3):**
```
We ask: does an LLM moderator read the post and follow the policy, or does it depend on a cue it should not need?
```
**Ganti:**
```latex
We ask what an LLM moderator's verdict depends on: the words annotators marked as evidence, the policy it is given, or the identity terms the post names; and whether tests with explicit expected outcomes can tell these apart.
```

### 2.2 Judul

Pedoman JSC: “*The title should be descriptive, not full sentences.*” Judul v24 diawali kalimat tanya, dan “*Relying on Identity Cues?*” lebih kuat daripada klaim akhir (dependence, bukan reliance). Pada audit #8 judul ditunda sampai E1-CF v2; pedoman jurnal membuat keputusan ini perlu diambil sebelum submit. **Usulan (keputusan penulis):**
```latex
Dual-Axis Metamorphic Testing of Evidence Grounding and Policy Sensitivity in LLM-Based Content Moderation
```
Jika judul diubah, ubah juga `\headoddname{...}` (running head).

### 2.3 Bingkai sosial untuk *Aims and Scope* JSC

Tambahkan satu kalimat di akhir paragraf pertama Intro (isi diambil dari §5 v24, tanpa klaim baru):
```latex
Because moderation decides whose speech stays visible and which groups a policy protects in practice, what such a verdict depends on is a question about the governance of online social life, not only about model accuracy.
```

### 2.4 Kontribusi (2) dan Related Work: samakan istilah

**Cari (Contribution 2):** `violating verdicts that survive erasure of the rationale are associated with a remaining identity term; a pre-specified counterfactual shows that replacing these terms lowers the flag rate more than a placebo replacement (Section 4.4).`
**Ganti:**
```latex
violating verdicts after erasure of the rationale are associated with a remaining identity term; a pre-specified counterfactual shows that replacing these terms lowers the flag rate more than an edit-count placebo, in one condition mostly through abstention (Section 4.4).
```
**Cari (Related Work, akhir):** `linking the retention of violating verdicts after erasure to a remaining identity term (Section 4.3)`
**Ganti:** `linking violating verdicts after erasure to a remaining identity term (Section 4.3)`

---

## 3. Perbaikan per temuan audit

### [Kritis] §5 Social computing and ethics

Saya **tidak** dapat mengisi status etik: tidak ada surat persetujuan/pengecualian atau formulir persetujuan di repo. Ganti paragraf dengan versi di bawah. Isi bagian merah **hanya dari dokumen resmi**; jika belum ada, minta klarifikasi komite etik UNIMUS sebelum submit. Jangan mengirim naskah dengan placeholder.
```latex
\textbf{Social computing and ethics.} Moderation decides whose speech stays visible: if a verdict changes with the group named and nothing else, two communities get different protection from the same policy. We use a public dataset and create no new data about people. The items contain hateful language and are released for research use only; examples are masked. Two raters, colleagues or students who are not authors, read items that contain real hate speech. The rating sheet warned them that it held real hate speech and offensive words, that it was for research only, and that they could stop and rest at any time.
\textcolor{red}{[PENULIS, pilih satu sesuai dokumen: (a) The study was approved by the [nama komite], Universitas Muhammadiyah Semarang (ref.~[nomor], [tanggal]). (b) The [nama komite] exempted the study from review (ref.~[nomor], [tanggal]).]
[Hanya jika ada buktinya: The raters gave [written/oral] informed consent before rating.]}
```

### [Tinggi] §4.5 dan Tabel 7 — R2

**Cari (§4.5, paragraf “Policy narrowing (R2)”), seluruh paragraf. Ganti:**
```latex
\textbf{Policy narrowing (R2).} Under the original oracle, Gemma~2 appears to ignore the narrowed policy on the 59 ambiguous offensive posts (pass 8.5\% direct and 0.0\% evidence, against 35.6\% and 22.8\% for Qwen2.5). On the same 59 posts, the human-corrected oracle gives 76.3\% and 67.8\% for Gemma~2 and 72.9\% and 70.2\% for Qwen2.5 (Table~7, R2 amb.\ corr.), so the apparent failure on these posts is mainly an oracle error. Over all 200 offensive posts, the stratum-weighted corrected estimate (R2 off.\ wtd.) is 52.7\% and 40.1\% for Gemma~2 against 74.4\% and 73.6\% for Qwen2.5. The gap comes from the other offensive posts, where Gemma~2 passes 42.9\% and 28.6\% of the 28 rated items against 75.0\% for Qwen2.5 under both prompts. A measure that needs no oracle points the same way: the share of originally violating offensive posts that move to not violating is 26\% (ambiguous) and 56\% (other offensive) for Qwen2.5 direct, but only 5\% and 15\% for Gemma~2 direct and 0\% and 5\% for Gemma~2 evidence. Gemma~2 thus reacts little to the narrowed policy on offensive posts without a protected-attribute attack, but this rests on 28 rated items in that stratum and on an oracle valid for only 32.2\% of the ambiguous items (59.9\% weighted), so R2 cannot be read without the oracle audit. We make no claim for the unvalidated hate-speech and normal strata.
```
**Tabel 7: header dan caption baru** (badan: `tab_pol_body.tex`):
```latex
\caption{Policy axis, identity swap, and controls (600 posts). R1: abstention among answered responses. R2 amb.\ orig.\ and amb.\ corr.: pass on the 59 ambiguous offensive posts (answered ones) under the original and the human-corrected oracle. R2 off.\ wtd.: stratum-weighted corrected pass over all 200 offensive posts (59 ambiguous, all rated; 141 other, 28 rated; weights 59/200 and 141/200). R3: share of verdicts that change. I1/I2: share of verdicts that differ from ORIG after an identity swap or a neutral sentence, on complete triples; RD $=$ I1$-$I2 in points with post-bootstrap 95\% CI; Holm $p$ over eight systems (family $F_I$). Llama~3.1 values use the posts it answered (Table~3). Llama~3.1/evidence has only 6 complete triples and no discordant pair: its rates and RD are not shown, but it stays in $F_I$ (Holm $p=1$).}
% header
System & R1 & \multicolumn{2}{c}{R2 amb.} & R2 off. & R3 & Triples & I1 & I2 & I1$-$I2 [CI] & Holm $p$ \\
       &    & orig. & corr. & wtd. & & & & & & \\
```

### [Tinggi] §3.7 dan Tabel 6 — denominator H1/S1 dan definisi non-jawaban

**Cari (§3.7), dari** `The primary hypothesis H1 is that ...` **sampai** `... for every answered pair.` **Ganti seluruhnya:**
```latex
The primary hypothesis H1 is that the flag rate under PLC exceeds that under NEU, paired by post, tested with exact McNemar and Holm correction over the six LLM conditions ($F_{\mathrm{CF}}$). The deletion contrast PLCDEL$-$DEL is the secondary analysis (S1), with its own Holm family over the same six conditions ($F_{\mathrm{CF2}}$). A post enters a contrast only when both of its texts are answered, that is, return a valid verdict or an abstention; an abstention counts as not flagged, and a refusal, unparseable output, generation error, or empty response removes the post from that contrast only. In the counterfactual run no response was unparseable, an error, or empty, and only Llama~3.1 refused, so only its H1 and S1 denominators differ (Table~6). The decision rule: the result supports a dependence of the verdict on the identity terms (label SUPPORT in the protocol) if H1 is Holm-significant with RD$>0$ in at least two of the four Qwen2.5 and Gemma~2 conditions and S1 has the same sign in those conditions. Llama~3.1 is reported but not counted because of its low coverage. The protocol file (\texttt{results/e1\_counterfactual/PROTOCOL.md}) is dated 10 November 2026 and states that it was fixed before any model call; the run log records the first counterfactual LLM call at 05:18 that day. The file entered version control only with the first commit of the repository (c60d6c4, 16 November), after the runs, so this order rests on the file's date and the log rather than on the commit history, and the protocol is not an external registration. Because abstention counts as not flagged, a post hoc analysis uses valid verdicts only, and a second drops the posts whose matched tokens are all ordinary words (``black'', ``white'', ``man''). The run used the same configuration as the main runs, and the REPLAY texts reproduced the main-run flags for every answered pair.
```
**Tabel 6: header dan caption baru** (badan: `tab_cf_body.tex`, kini dengan kolom n S1 dan RD dari hitungan mentah):
```latex
\caption{E1-CF on 88 posts: flag rates (\%) under placebo (PLC) and identity replacement (NEU), the risk difference PLC$-$NEU with post-bootstrap 95\% CI, discordant pairs $b/c$ (flag only under PLC / only under NEU), and the deletion contrast PLCDEL$-$DEL (S1) with its own $b/c$ after the semicolon. $n$ H1, $n$ S1: posts entering each contrast, i.e.\ with both texts answered (valid verdict or abstention; abstention $=$ not flagged; refusals removed). They are 88 except for Llama~3.1, the only system that refused, so its rates are not comparable. RD $=(b-c)/n$ from raw counts. Holm $p$ over the six LLM conditions, separately for H1 ($F_{\mathrm{CF}}$) and S1 ($F_{\mathrm{CF2}}$); Llama~3.1 and the classifiers are outside the decision rule.}
% header
System & $n$ H1 & $n$ S1 & PLC & NEU & H1: RD [CI] & $b/c$ & Holm $p$ & S1: RD [CI]; $b/c$ & Holm $p$ \\
```

### [Tinggi] §4.1 dan Tabel 3 — akurasi Llama 3.1

**Cari:** `Its answers come from a self-selected subset, so Llama 3.1 is not compared on accuracy.`
**Ganti:**
```latex
Its answers come from a self-selected subset (246 and 76 valid verdicts on the 600 original posts), so we do not compare its conditional accuracy with that of the other systems.
```
**Cari:** `No LLM condition significantly outperformed word-LR on the original posts (paired comparisons with Holm correction over six conditions).`
**Ganti:**
```latex
No LLM condition significantly outperformed word-LR in overall accuracy on the original posts, where every non-answer counts as wrong (exact McNemar, Holm over the six LLM conditions, family $F_B$); the two Llama~3.1 conditions are included and fall far below word-LR (RD $-50.2$ and $-68.3$ points; Holm $p<0.001$).
```
**Caption Tabel 3, ganti seluruhnya:**
```latex
\caption{Original posts (600): coverage, accuracy, refusal, and abstention in \%. Coverage, overall accuracy, refusal, and abstention use the 600 original posts as denominator, so coverage, refusal, and abstention sum to 100 (up to unparseable output). Conditional accuracy uses each system's valid verdicts as denominator ($600\times$Cov.; 246 and 76 for Llama~3.1), with Wilson 95\% CI, and is not comparable across systems with different coverage. Overall accuracy counts every non-answer as wrong and is the measure tested against word-LR ($F_B$). Rates over all 4,233 items are in Fig.~2.}
```

### [Tinggi] §4.3, Tabel 5, Gambar 3 — dua populasi E1

1. **Hapus Gambar 3.** Setelah 2×2 masuk Tabel 5, Gambar 3 menduplikasi isinya, dan pedoman JSC melarang tabel menduplikasi gambar. Penghapusan ini juga memberi ruang untuk teks tambahan (batas 12 halaman).
2. **Tabel 5 menjadi `table*`** (badan: `tab_e1_body.tex`):
```latex
\begin{table*}[t]
\caption{E1 after erasure. Left (retention): among posts judged violating at ORIG and answered after erasure ($n$), share still violating (Kept), moved to not violating (To not), and moved to insufficient (To ins.), in \%. Right (association): over all answered E1 posts, whatever the ORIG verdict, posts flagged / answered with a residual identity term (Id.) and without one (No id.), the odds ratio of being flagged with its exact conditional 95\% CI, and the Fisher test with Holm correction over eight systems ($F_R$). The two blocks have different denominators.}
\centering\small
\begin{tabular}{lrrrrrrll}
\toprule
 & \multicolumn{4}{c}{Retention (ORIG violating)} & \multicolumn{4}{c}{Association (all answered E1)} \\
\cmidrule(lr){2-5}\cmidrule(lr){6-9}
System & $n$ & Kept & To not & To ins. & Id. & No id. & OR [95\% CI] & Holm $p$ \\
\midrule
\input{tab_e1_body}
\bottomrule
\end{tabular}
\end{table*}
```
3. **Cari (§4.3, paragraf “Residual identity terms”) seluruh paragraf. Ganti:**
```latex
\textbf{Residual identity terms.} We then asked which erased posts are flagged. After erasure, 88 of the 397 posts still contain an identity term. Table~5 reports two populations. Its left block is retention: among the posts a system flagged at ORIG and answered after erasure ($n$), the share still violating. Its right block is the association over all answered E1 posts, whatever the ORIG verdict, with the counts behind each odds ratio. For every LLM condition with enough answers, posts with an identity term are flagged after erasure far more often than the others. For example, Gemma~2 direct flags 84.1\% (74 of 88) of the posts with an identity term and 37.5\% (116 of 309) of the others (OR 8.8, Holm $p<0.001$). The odds ratios are 3.1--8.8 across the five conditions with Holm $p<0.001$; the sixth, Llama~3.1 with the evidence prompt, gives 3.5 (95\% CI [1.1, 11.6]; Holm $p=0.083$) on 175 answered posts and answers only 12.7\% of the original posts (Table~3). Neither classifier shows a statistically detectable association (OR 1.2; Holm $p=1$); with 88 posts that carry an identity term, a moderate association cannot be excluded. Post hoc, the retention population shows the same pattern: the flag is kept for 70.5--87.1\% of the posts with an identity term against 25.5--38.8\% of the others in the four Qwen2.5 and Gemma~2 conditions (OR 6.1--10.6; Holm $p<0.001$ over eight systems; Llama~3.1 direct 7.2, Holm $p=0.004$), whereas the classifiers give 2.1 and 1.8 (Holm $p=0.076$ and $0.100$). Removing the 13 E1 items that raters judged invalid (of 79 rated; the other 318 were not rated) changes the association odds ratios by less than 0.1. This is an association; the next section tests it.
```
4. Paragraf “Erased evidence (E1)” sebelumnya: kalimat `Yet after erasure 36–50% of the posts that were judged violating remain violating ... (Table 5)` **tetap** (itu memang populasi retensi).

### [Tinggi] §3.6 dan §4.5 — status I1–I2

**Cari (§3.6), dari** `We correct for multiplicity with Holm's method` **sampai akhir subbab. Ganti:**
```latex
We correct for multiplicity with Holm's method [28] within each named family: the paired contrast of identity swap vs.\ neutral sentence ($F_I$, I1$-$I2 flip rates, 8 systems: six LLM conditions, including Llama~3.1 evidence with only six complete triples, and two classifiers), evidence vs.\ direct prompt ($F_P$, 3 models), overall accuracy of each LLM condition vs.\ word-LR ($F_B$, 6 tests), residual identity term after erasure ($F_R$, 8 systems), and the counterfactual ($F_{\mathrm{CF}}$ for H1 and $F_{\mathrm{CF2}}$ for S1, 6 LLM conditions each). Only H1, S1, and the decision rule were fixed in a protocol before the counterfactual calls (Section~3.7). Confidence intervals are not adjusted for multiplicity; only the $p$ values marked Holm are. Comparisons inside the named families are secondary. Post hoc analyses are labelled and corrected only within the family they name. Everything else is exploratory and uncorrected, including the I1 and I2 flip rates read on their own and all I3 results; the I1$-$I2 contrast itself belongs to $F_I$.
```
§4.5 paragraf I1 vs I2 tidak perlu diubah (“The other seven systems show no significant difference (Holm p ≥ 0.065)” sudah mencakup Llama evidence, Holm p = 1).

### [Tinggi] §4.4 — analisis *valid verdicts only*

**Cari (§4.4, par. 2), dari** `In a post hoc analysis on valid verdicts only` **sampai** `It does not hold for Gemma 2 with the evidence prompt (+2.0; Holm p = 1.0):` **Ganti:**
```latex
In a post hoc sensitivity analysis of H1 restricted to pairs in which both responses are valid verdicts (84, 73, 64, and 51 pairs; Holm over these four conditions, not the primary six), H1 stays significant for Qwen2.5 direct (RD $+22.6$ points; Holm $p<0.001$), Qwen2.5 evidence ($+16.4$; Holm $p=0.034$), and Gemma~2 direct ($+18.8$; Holm $p=0.001$), but not for Gemma~2 with the evidence prompt ($+2.0$; Holm $p=1.0$). S1 was not recomputed on this subset, so the decision rule is not re-applied to it. The subset is selected on the responses to the edited texts, so it answers a narrower question than the primary analysis: whether the verdict changes when the model commits to a verdict under both edits. Among the posts flagged under PLC but not under NEU,
```
(kalimat lanjutan `the share that moves to insufficient rather than not violating is 1 of 21 ...` tetap.)

**Cari (§4.4, par. 1):** `lowers the flag rate by 17.1 to 25.0 points` → **Ganti:** `lowers the flag rate by 17.0 to 25.0 points`
**Cari:** `Excluding the four posts that raters judged to still contain an attack gives the same conclusion (84 posts;` → **Ganti:** `Excluding the four posts that raters judged to still contain an attack, H1 stays positive and Holm-significant in all four conditions (84 posts;`

### [Menengah] Protokol dan run — *Data and code availability*

**Ganti paragraf kedua *Data and code availability*:**
```latex
Items, prompts, raw responses, and analysis code are at \url{https://github.com/hilman-firdd/reading-the-post-or-relying-on-indentity-cues} (commit \textcolor{red}{[HASH RILIS AKHIR]}). Run~1, which all tables and figures report, is in \texttt{runs/} (main items) and \texttt{results/e1\_counterfactual/runs/} (counterfactual items). The uniform rerun of the first 822 Qwen2.5 direct items is \texttt{runs\_uniform/qwen2.5\_7b\_direct\_first822.jsonl}; repetitions 2 and 3, used only for the stability analysis, are in \texttt{runs\_repeat/} and \texttt{results/repeats/}. The counterfactual protocol is \texttt{results/e1\_counterfactual/PROTOCOL.md}, first committed in c60d6c4 (Section~3.7); its post hoc additions are listed in its Section~8.
```
Catatan: URL repo berisi “*indentity*”. Jika itu nama repo yang sebenarnya, biarkan; jika salah ketik, perbaiki di GitHub dan di naskah.

---

## 4. Perubahan turunan agar seluruh naskah konsisten

**Abstrak (150 kata; mendefinisikan LLM dan classifier; tanpa “oracle” dan “word-LR” yang tak terdefinisi):**
```latex
Large language models (LLMs) moderate online posts, but accuracy hides what a verdict depends on. We apply dual-axis metamorphic testing: we change the post's annotated rationale or the policy, with identity terms as a diagnostic, and check verdicts against partly validated expected outcomes. On 4,233 items from 600 HateXplain posts we test three local LLMs under two prompts and two logistic-regression classifiers. No LLM condition significantly outperforms the word-level classifier on accuracy, and one model refuses most items. After rationale erasure, LLM verdicts are violating far more often when an identity term remains (odds ratio 3.1 to 8.8). In a pre-specified 88-post counterfactual, replacing identity terms lowers the flag rate more than an edit-count placebo for Qwen2.5 and Gemma 2, for Gemma 2 with the evidence prompt mostly through abstention. Policy-axis results change with human-corrected expected outcomes and stay exploratory. This shows dependence on the replaced terms, not unjustified reliance.
```

**Fig. 3** dihapus → ganti rujukan `(Fig. 3, Table 5)` menjadi `(Table 5)`; tidak ada gambar sesudahnya yang perlu dinomori ulang.

**Diskusi, “What the results establish”:**
- Cari `tied to a remaining identity term in LLMs but not in the classifiers` → ganti `tied to a remaining identity term, far more strongly in LLMs than in the classifiers`.
- Cari `by a rule fixed in advance` → ganti `by the decision rule stated in the protocol`.

**Diskusi, “The most specific finding”:**
Cari `The link between a residual identity term after erasure and the retention of a violating verdict is the main diagnostic result.` → ganti:
```latex
The link between a residual identity term and a violating verdict after erasure is the main diagnostic result; it holds over all answered posts and, post hoc, among the posts each model first flagged.
```

**Kesimpulan:** Cari `A pre-specified counterfactual supports dependence on the tested replacement for Qwen2.5 and Gemma 2; it does not show that the dependence is unjustified.` → ganti:
```latex
A pre-specified counterfactual shows that replacing the tested identity terms lowers the flag rate more than an edit-count placebo for Qwen2.5 and Gemma~2, for Gemma~2 with the evidence prompt mostly through abstention; it does not show that the dependence is unjustified or that groups are treated unequally. On the policy axis, human correction of the oracles changed how R2 reads, which is why those tests stay exploratory.
```

**Acknowledgment (baru; wajib menurut pedoman JSC; letakkan tepat sebelum References):**
```latex
\section*{Acknowledgment}
\textcolor{red}{[PENULIS: We thank [nama penilai, hanya dengan izin mereka] for rating the validation items. This work was supported by [sumber dana dan nomor hibah] / received no external funding.]}
```

---

## 5. Hal yang hanya bisa diisi penulis (jangan dikarang)

1. Status etik (persetujuan atau pengecualian; nama komite, nomor, tanggal) dan bentuk persetujuan penilai.
2. Nama penilai untuk Acknowledgment (dengan izin) dan status pendanaan.
3. Hash commit rilis akhir. Naskah v24 mengutip `8cb6b59`; HEAD sekarang `654c666`, ditambah perubahan v25 yang belum di-commit (`paper/gen_tables.py`, `paper/posthoc_e1_retention.py`, `paper/revisi_v25/`). Commit dulu, lalu bekukan hash itu di naskah.
4. Keputusan judul (§2.2).
5. Opsional: tanggal “Manuscript received/accepted” di footnote halaman 1 diisi redaksi, bukan penulis.

## 6. Verifikasi

```bash
PY=~/.venvs/modkit/bin/python
$PY paper/gen_tables.py . /tmp/tabs                      # badan Tabel 3-7 v25
$PY paper/posthoc_e1_retention.py . paper/revisi_v25     # analisis retensi (post hoc)
$PY paper/revisi_v25/verify_v25_revisions.py .           # Part A: angka dari data (41 cek)
$PY paper/revisi_v25/verify_v25_revisions.py . body.tex  # Part A + B: string baru ada, frasa lama hilang, placeholder etik sudah terisi
```
Part B sengaja **gagal** selama placeholder etik masih ada. Jalankan juga `verify_numbers.py` milik kit v24 (yang memberi `FAILS = []`) untuk memastikan cek lama tetap lulus. Cek jumlah kata abstraknya mengikuti `assemble.py`.

## 7. Anggaran halaman (batas 10–12)

Tambahan teks sekitar 230 kata ditambah Tabel 5 menjadi lebar penuh. Penyeimbang: hapus Gambar 3 (sekitar sepertiga kolom). Jika masih melebihi 12 halaman, kandidat pangkas tanpa mengubah klaim: (a) paragraf *Prompt ablation* diringkas menjadi satu kalimat beserta rujukan ke repo; (b) kalimat macro-F1 post hoc di §4.1; (c) kalimat terakhir Related Work tentang metode pencarian OpenAlex dipindah ke Data availability.
