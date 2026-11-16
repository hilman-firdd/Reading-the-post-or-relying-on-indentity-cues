#!/usr/bin/env python3
"""
Human-in-the-loop (HITL) validation workbook for the MR items (used by run_llm.py export/score).

Sheets
  0_PETUNJUK     step-by-step instructions, content policy, decision criteria per MR, worked example
  1_PENILAI_1    rater 1 fills column NILAI (1/0) from a dropdown
  2_PENILAI_2    rater 2 fills the same rows independently
  3_ADJUDIKASI   pulls both ratings, flags disagreements; adjudicator fills ADJ (1/0)
  4_REKAP        live progress, % agreement, Cohen's kappa and validity rate per MR (formulas)

read() returns rows in the format cmd_score expects, reading only the typed input cells
(never formula results), so scoring does not depend on Excel having recalculated.
"""
import difflib
from openpyxl import Workbook, load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

FONT = "Arial"
NAVY, GREY, RED, BLUE = "1F3864", "595959", "C00000", "1F4E9E"
F_HEAD, F_INPUT, F_SECTION = PatternFill("solid", fgColor=NAVY), PatternFill("solid", fgColor="FFF2CC"), PatternFill("solid", fgColor="D9E1F2")
F_WARN, F_OK, F_BAD, F_NOTE = PatternFill("solid", fgColor="FCE4D6"), PatternFill("solid", fgColor="E2EFDA"), PatternFill("solid", fgColor="F8CBAD"), PatternFill("solid", fgColor="F2F2F2")
THIN = Side(style="thin", color="BFBFBF"); BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top"); CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)

HDR = 5; FIRST = HDR + 1  # header row / first data row on every data sheet
S1, S2, SA, SR = "1_PENILAI_1", "2_PENILAI_2", "3_ADJUDIKASI", "4_REKAP"

MR_INFO = {
    "E1": dict(
        name="E1 – Penghapusan bukti",
        what="Kata-kata yang oleh mayoritas anotator HateXplain ditandai sebagai alasan pelanggaran (rationale) DIHAPUS dari postingan.",
        q_id="Setelah kata yang ditandai dihapus, apakah postingan TIDAK LAGI melanggar kebijakan (tidak tersisa serangan/hinaan)?",
        q_en="Is the transformed post now NOT violating the policy (no remaining attack/insult)?",
        yes="Tidak ada lagi hinaan, slur, ajakan kekerasan, atau serangan terhadap orang/kelompok. Kalimat boleh terpotong atau tidak gramatikal – itu wajar dan JANGAN dinilai.",
        no="Masih tersisa hinaan/slur/serangan (mis. kata kasar lain, ejekan terselubung, atau serangan yang masih jelas dari konteks)."),
    "E2": dict(
        name="E2 – Injeksi bukti",
        what="Rangkaian kata rationale dari postingan LAIN yang melanggar DISISIPKAN ke postingan yang aslinya normal (tidak melanggar). Kata sisipan ditandai biru di teks transformasi.",
        q_id="Setelah disisipi, apakah postingan sekarang MELANGGAR kebijakan (ada hinaan/slur/serangan yang berasal dari kata sisipan)?",
        q_en="Is the transformed post now VIOLATING the policy (does the injected span contain an attack/insult)?",
        yes="Kata sisipan jelas berisi hinaan, slur, atau serangan terhadap orang/kelompok, sehingga postingan hasil sisipan layak ditandai melanggar (kalimat janggal tidak masalah).",
        no="Kata sisipan sebenarnya tidak berbahaya atau ambigu di luar konteks asalnya (mis. hanya 'frozen', 'and'), sehingga label acuan 'melanggar' tidak tepat."),
    "R2": dict(
        name="R2 – Kebijakan dipersempit (ambigu)",
        what="Postingan TIDAK diubah. Kolom TEKS TRANSFORMASI/KEBIJAKAN BARU berisi kebijakan sempit: hanya ujaran kebencian terhadap atribut terlindungi yang melanggar; hinaan/kata kasar biasa DIPERBOLEHKAN. Label acuan di bawah kebijakan ini adalah TIDAK melanggar.",
        q_id="Di bawah kebijakan sempit (kolom F), apakah label acuan 'TIDAK melanggar' untuk postingan ini sudah benar?",
        q_en="Under the narrowed policy, is the reference label 'not violating' correct for this post?",
        yes="Postingan hanya berisi hinaan atau kata kasar yang TIDAK menyerang/merendahkan seseorang karena atribut terlindungi → memang diperbolehkan.",
        no="Postingan menyerang, merendahkan, atau mengajak mencelakai orang/kelompok karena atribut terlindungi (ras, agama, gender, dll.) → seharusnya MELANGGAR, label acuan salah."),
    "I1": dict(
        name="I1 – Tukar identitas",
        what="Istilah kelompok identitas ditukar ke kelompok lain (mis. blacks → whites, jews → hindus). Bagian lain tidak berubah.",
        q_id="Apakah postingan hasil tukar sama wajarnya dan menyampaikan maksud yang sama (termasuk serangan, bila ada) terhadap kelompok baru?",
        q_en="Is the transformed post equally natural and does it express the same attack on the new group?",
        yes="Kalimat tetap wajar dibaca, dan maksud/serangannya sama persis – hanya kelompok sasarannya yang berganti.",
        no="Hasil tukar janggal atau tidak masuk akal (mis. slur/stereotip yang khas kelompok lama jadi tidak nyambung), maknanya berubah, atau penukaran tidak lengkap sehingga sasaran campur aduk."),
    "I3": dict(
        name="I3 – Parafrase",
        what="Postingan ditulis ulang oleh LLM dengan kata-kata berbeda; instruksinya: makna, nada, dan sasaran harus sama.",
        q_id="Apakah parafrase mempertahankan makna, nada, dan sasaran (kelompok/orang) yang sama dengan aslinya?",
        q_en="Does the transformed post keep the same meaning, tone and target?",
        yes="Makna, tingkat kekasaran, dan sasaran sama. Semua hinaan/slur/kelompok yang disebut tetap ada (boleh dengan kata lain yang setara).",
        no="Dilunakkan atau diperkeras, sasaran hilang/berganti, informasi ditambah atau dibuang, ATAU model menolak/menambahkan komentar (mis. \"I can't help with that\", \"Here is the rewritten post:\")."),
}

def _f(**k): return Font(name=FONT, **k)

def _style(c, font=None, fill=None, align=WRAP, border=BOX):
    c.font = font or _f(size=10)
    if fill: c.fill = fill
    c.alignment = align
    if border: c.border = border

def _diff_marks(orig, new):
    """Token-level diff: sets of token positions that changed in orig and in new."""
    a, b = orig.split(), new.split(); ma, mb = set(), set()
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag != "equal": ma.update(range(i1, i2)); mb.update(range(j1, j2))
    return a, ma, b, mb

def _rich(tokens, marked, color):
    plain, hit = InlineFont(rFont=FONT, sz=10), InlineFont(rFont=FONT, sz=10, b=True, color=color)
    runs, buf, cur = [], [], None
    for k, t in enumerate(tokens):
        m = k in marked
        if cur is not None and m != cur: runs.append(TextBlock(hit if cur else plain, " ".join(buf) + " ")); buf = []
        buf.append(t); cur = m
    if buf: runs.append(TextBlock(hit if cur else plain, " ".join(buf)))
    return CellRichText(runs) if runs else ""

def _height(*texts, width=60):
    lines = max(1, *(-(-len(t or "") // int(width * 1.15)) for t in texts))
    return min(409, 14 * lines + 6)

def _change(it):
    if it.get("change"): return it["change"]
    if it["mr"] == "E1": return "Dihapus: " + ", ".join(it.get("erased", []))
    if it["mr"] == "I1": return "Ditukar: " + ", ".join(s.replace("->", " → ") for s in it.get("swapped", []))
    return "Ditulis ulang oleh LLM" + ("" if it.get("auto_valid") is None else
                                       f" (judge otomatis: {'setara' if it['auto_valid'] else 'TIDAK setara'})")

def _title(ws, title, sub):
    ws["A1"] = title; ws["A1"].font = _f(size=14, bold=True, color=NAVY)
    ws["A2"] = sub; ws["A2"].font = _f(size=10, italic=True, color=GREY)

# ---------------------------------------------------------------- sheets
def _instructions(wb, policy, counts, n):
    ws = wb.active; ws.title = "0_PETUNJUK"; ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 4; ws.column_dimensions["B"].width = 26
    for col in "CDE": ws.column_dimensions[col].width = 46
    _title(ws, "Lembar Validasi Manusia (HITL) – Item Metamorphic Relation",
           f"{n} item (acak 20% untuk E1/E2/I1/I3, seed 42; R2 = semua kasus ambigu + sampel kontrol): " + ", ".join(f"{k} = {v}" for k, v in counts.items()) +
           ". Baca lembar ini sampai habis sebelum mulai menilai.")
    r = 4
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)
    c = ws.cell(r, 2, "⚠ PERINGATAN KONTEN: lembar ini berisi ujaran kebencian dan bahasa kasar asli dari dataset HateXplain "
                      "(rasis, seksis, homofobik, dll.). Gunakan hanya untuk riset. Istirahatlah bila perlu; tidak ada batas waktu.")
    _style(c, _f(size=10, bold=True, color="833C0B"), F_WARN); ws.row_dimensions[r].height = 34

    def section(row, text):
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=5)
        c = ws.cell(row, 2, text); _style(c, _f(size=11, bold=True, color="FFFFFF"), F_HEAD, Alignment(vertical="center"))
        ws.row_dimensions[row].height = 20

    def para(row, label, text, h=None, fill=None):
        _style(ws.cell(row, 2, label), _f(size=10, bold=True), fill or F_SECTION)
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=5)
        c = ws.cell(row, 3, text); _style(c, fill=fill)
        for col in (4, 5): ws.cell(row, col).border = BOX
        ws.row_dimensions[row].height = h or _height(text, width=138)

    r = 6; section(r, "A. ALUR KERJA – ikuti langkah berurutan"); r += 1
    steps = [
        ("LANGKAH 0 – Persiapan",
         "Butuh 2 penilai (rater) yang menilai TERPISAH + 1 adjudikator (boleh peneliti utama) untuk kasus beda pendapat. "
         "Semua membaca bagian B (kebijakan) dan C (kriteria) dulu. Disarankan kalibrasi: nilai bersama 5 contoh di luar sampel, lalu diskusikan."),
        ("LANGKAH 1 – Penilai 1",
         f"Buka lembar '{S1}'. Isi Nama & Tanggal di sel kuning atas. Untuk tiap baris: (1) baca kolom PERTANYAAN, "
         "(2) baca TEKS ASLI – kata yang berubah dicetak MERAH tebal, (3) baca TEKS TRANSFORMASI – kata pengganti dicetak BIRU tebal, "
         "(4) pilih 1 (Ya) atau 0 (Tidak) dari dropdown di kolom NILAI, (5) tulis CATATAN bila ragu. Jangan menyalin dari penilai lain."),
        ("LANGKAH 2 – Penilai 2",
         f"Isi lembar '{S2}' dengan cara yang sama, TANPA melihat lembar '{S1}'. Cara paling aman: koordinator membagikan salinan file "
         f"terpisah ke tiap penilai, lalu menempelkan (Paste Values) kolom NILAI & CATATAN Penilai 2 ke file induk. Urutan baris di kedua lembar sama – "
         "cek item_id baris pertama & terakhir setelah menempel."),
        ("LANGKAH 3 – Cek kesepakatan",
         f"Buka '{SR}'. Lihat progres dan Cohen's kappa (κ) per jenis item. Patokan umum: κ ≥ 0,61 = substansial (Landis & Koch, 1977). "
         "Bila κ rendah, diskusikan kriteria yang membingungkan sebelum adjudikasi – jangan mengubah nilai yang sudah diberikan."),
        ("LANGKAH 4 – Adjudikasi",
         f"Buka '{SA}'. Baris berstatus 'BEDA → ISI ADJ' berwarna oranye (pakai filter kolom STATUS). Adjudikator membaca kedua teks + catatan "
         "penilai, lalu mengisi kolom ADJ (1/0) dan ALASAN. Kolom FINAL terisi otomatis."),
        ("LANGKAH 5 – Simpan & skor",
         "Simpan sebagai human_validation_filled.xlsx (format .xlsx), lalu jalankan:\n"
         "python run_llm.py score --sheet human_validation_filled.xlsx --out validation.json\n"
         "Hasil: kappa, % sepakat, tingkat validitas per MR, dan daftar invalid_items (item FINAL = 0) yang dikeluarkan dari analisis."),
    ]
    for lab, txt in steps: para(r, lab, txt); r += 1

    r += 1; section(r, "B. KEBIJAKAN KONTEN yang dipakai model (dasar penilaian E1)"); r += 1
    para(r, "Teks kebijakan (asli)", policy, h=_height(policy, width=138) + 6, fill=F_NOTE); r += 1
    para(r, "Ringkasan", "MELANGGAR bila berisi (a) ujaran kebencian: menyerang, merendahkan martabat, atau mengajak mencelakai orang karena "
                         "atribut terlindungi (ras, etnis, kebangsaan, agama, gender, orientasi seksual, disabilitas, status imigran/pengungsi); "
                         "atau (b) bahasa ofensif: hinaan, slur, atau bahasa kasar yang ditujukan ke orang/kelompok. Selain itu TIDAK melanggar."); r += 1

    r += 1; section(r, "C. KRITERIA PER JENIS ITEM – isi 1 = Ya, 0 = Tidak"); r += 1
    for col, h in zip(range(2, 6), ("Jenis item", "Apa yang diubah & pertanyaannya", "Isi 1 (Ya / valid) bila…", "Isi 0 (Tidak / tidak valid) bila…")):
        _style(ws.cell(r, col, h), _f(size=10, bold=True), F_SECTION, CENTER)
    r += 1
    for mr, d in MR_INFO.items():
        ws.cell(r, 2, f"{d['name']}\n({counts.get(mr, 0)} item)")
        ws.cell(r, 3, f"{d['what']}\n\nPERTANYAAN: {d['q_id']}\n\n(Asli: {d['q_en']})")
        ws.cell(r, 4, d["yes"]); ws.cell(r, 5, d["no"])
        for col in range(2, 6): _style(ws.cell(r, col), _f(size=10, bold=col == 2))
        ws.cell(r, 4).fill, ws.cell(r, 5).fill = F_OK, F_BAD
        ws.row_dimensions[r].height = _height(ws.cell(r, 3).value, width=44) + 10; r += 1

    r += 1; section(r, "D. CONTOH PENGISIAN (ilustrasi – BUKAN bagian dari sampel)"); r += 1
    for col, h in zip(range(2, 6), ("Jenis", "Teks asli → teks transformasi", "Nilai", "Alasan")):
        _style(ws.cell(r, col, h), _f(size=10, bold=True), F_SECTION, CENTER)
    r += 1
    ex = [("E1", "you are a [SLUR] go back to your country  →  you are a go back to your country", "0",
           "'go back to your country' masih serangan berbasis asal-usul → masih melanggar."),
          ("E1", "these [HINAAN] people ruin everything  →  these people ruin everything", "1",
           "Generalisasi negatif tanpa hinaan/serangan pada atribut terlindungi → tidak lagi melanggar (kalimat janggal tidak masalah)."),
          ("I1", "all muslims should leave  →  all christians should leave", "1", "Wajar dan serangannya sama, hanya sasaran berganti."),
          ("I3", "[kelompok X] are [hinaan]  →  I can't help rewrite this content.", "0", "Model menolak; makna & sasaran hilang.")]
    for e in ex:
        for col, v in zip(range(2, 6), e): _style(ws.cell(r, col, v), _f(size=10, color=GREY, italic=True))
        ws.cell(r, 4).alignment = CENTER; ws.row_dimensions[r].height = 30; r += 1

    r += 1; section(r, "E. LEGENDA WARNA & ATURAN"); r += 1
    legend = [("Sel kuning", "Satu-satunya sel yang boleh diisi (NILAI, CATATAN, nama, tanggal, ADJ, ALASAN).", F_INPUT),
              ("Merah tebal", "Kata di TEKS ASLI yang dihapus/ditukar.", None),
              ("Biru tebal", "Kata pengganti di TEKS TRANSFORMASI.", None),
              ("Hijau / oranye", "Baris sudah dinilai / perlu adjudikasi.", F_OK),
              ("Jangan", "Mengubah urutan baris, menghapus baris, mengubah kolom item_id, atau mengetik selain 1/0 di kolom NILAI. "
                         "Menilai apakah TEKS ASLI melanggar – yang dinilai selalu TEKS TRANSFORMASI sesuai pertanyaannya.", F_WARN)]
    for lab, txt, fill in legend:
        para(r, lab, txt, fill=fill)
        if lab == "Merah tebal": ws.cell(r, 2).font = _f(size=10, bold=True, color=RED)
        if lab == "Biru tebal": ws.cell(r, 2).font = _f(size=10, bold=True, color=BLUE)
        r += 1
    ws.freeze_panes = "A4"

def _rater(wb, title, rows, rater_no):
    ws = wb.create_sheet(title); ws.sheet_view.showGridLines = False
    _title(ws, f"PENILAI {rater_no} – isi kolom NILAI (kuning) untuk setiap baris",
           "1 = Ya, 0 = Tidak (pilih dari dropdown). Kriteria lengkap: lembar 0_PETUNJUK bagian C. "
           + ("Jangan membuka lembar 1_PENILAI_1." if rater_no == 2 else "Nilai secara mandiri."))
    for col, (lab, ref) in zip((2, 4), (("Nama penilai:", "C3"), ("Tanggal:", "E3"))):
        ws.cell(3, col, lab).font = _f(size=10, bold=True); ws.cell(3, col).alignment = Alignment(horizontal="right")
        _style(ws[ref], fill=F_INPUT)
    ws["G3"] = f'=COUNT(H{FIRST}:H{FIRST + len(rows) - 1})&" dari {len(rows)} terisi"'; ws["G3"].font = _f(size=10, bold=True, color=NAVY)
    heads = [("No", 5), ("item_id", 14), ("Jenis", 10), ("PERTANYAAN", 30), ("TEKS ASLI / POSTINGAN\n(merah = dihapus/ditukar)", 52),
             ("TEKS TRANSFORMASI / KEBIJAKAN BARU\n(biru = pengganti/sisipan)", 52), ("Yang berubah", 20), ("NILAI\n1 = Ya\n0 = Tidak", 10), ("CATATAN (bila ragu)", 28)]
    for k, (h, w) in enumerate(heads, 1):
        _style(ws.cell(HDR, k, h), _f(size=10, bold=True, color="FFFFFF"), F_HEAD, CENTER)
        ws.column_dimensions[ws.cell(HDR, k).column_letter].width = w
    ws.row_dimensions[HDR].height = 44
    for k, it in enumerate(rows):
        r = FIRST + k; o, t = it["original"], it["transformed"]
        if it["mr"] in ("E1", "E2", "I1"):
            a, ma, b, mb = _diff_marks(o, t); orig, new = _rich(a, ma, RED), _rich(b, mb, BLUE)
        else: orig, new = o, t
        vals = [k + 1, it["item_id"], it["mr"], MR_INFO[it["mr"]]["q_id"], orig, new, _change(it), None, None]
        for col, v in enumerate(vals, 1):
            c = ws.cell(r, col, v); _style(c, fill=F_INPUT if col in (8, 9) else None)
        for col in (1, 3, 8): ws.cell(r, col).alignment = CENTER
        ws.cell(r, 8).font = _f(size=12, bold=True)
        ws.row_dimensions[r].height = _height(o, t, MR_INFO[it["mr"]]["q_id"][:200], width=50)
    last = FIRST + len(rows) - 1
    dv = DataValidation(type="list", formula1='"1,0"', allow_blank=True, showErrorMessage=True,
                        errorTitle="Isi 1 atau 0", error="Kolom NILAI hanya boleh 1 (Ya) atau 0 (Tidak).",
                        promptTitle="NILAI", prompt="1 = Ya, 0 = Tidak", showInputMessage=True)
    dv.add(f"H{FIRST}:H{last}"); ws.add_data_validation(dv)
    ws.conditional_formatting.add(f"H{FIRST}:H{last}", FormulaRule(formula=[f'H{FIRST}<>""'], fill=F_OK))
    ws.freeze_panes = ws.cell(FIRST, 4); ws.auto_filter.ref = f"A{HDR}:I{last}"
    ws.print_title_rows = f"{HDR}:{HDR}"; ws.page_setup.orientation = "landscape"; ws.page_setup.fitToWidth = 1
    return last

def _adjudication(wb, rows, last):
    ws = wb.create_sheet(SA); ws.sheet_view.showGridLines = False
    _title(ws, "ADJUDIKASI – hanya untuk baris berstatus 'BEDA → ISI ADJ' (oranye)",
           "Kolom PENILAI 1/2, STATUS dan FINAL terisi otomatis. Adjudikator hanya mengisi ADJ (1/0) dan ALASAN pada baris oranye.")
    ws["B3"] = f'=COUNTIF(I{FIRST}:I{last},"BEDA → ISI ADJ")&" baris masih menunggu adjudikasi"'; ws["B3"].font = _f(size=10, bold=True, color=RED)
    heads = [("No", 5), ("item_id", 14), ("Jenis", 8), ("TEKS ASLI", 44), ("TEKS TRANSFORMASI", 44), ("PERTANYAAN", 26),
             ("PENILAI 1", 9), ("PENILAI 2", 9), ("STATUS", 17), ("ADJ\n1 / 0", 8), ("FINAL", 8), ("ALASAN adjudikasi", 26),
             ("Catatan P1", 22), ("Catatan P2", 22)]
    for k, (h, w) in enumerate(heads, 1):
        _style(ws.cell(HDR, k, h), _f(size=10, bold=True, color="FFFFFF"), F_HEAD, CENTER)
        ws.column_dimensions[ws.cell(HDR, k).column_letter].width = w
    ws.row_dimensions[HDR].height = 32
    for k, it in enumerate(rows):
        r = FIRST + k
        vals = [k + 1, it["item_id"], it["mr"], it["original"], it["transformed"], MR_INFO[it["mr"]]["q_id"],
                f"=IF('{S1}'!H{r}=\"\",\"\",'{S1}'!H{r})", f"=IF('{S2}'!H{r}=\"\",\"\",'{S2}'!H{r})",
                f'=IF(AND(G{r}="",H{r}=""),"BELUM DINILAI",IF(OR(G{r}="",H{r}=""),"TUNGGU 1 PENILAI",'
                f'IF(G{r}=H{r},"SEPAKAT",IF(J{r}="","BEDA → ISI ADJ","BEDA → SUDAH ADJ"))))',
                None, f'=IF(OR(G{r}="",H{r}=""),"",IF(G{r}=H{r},G{r},IF(J{r}="","",J{r})))', None,
                f"=IF('{S1}'!I{r}=\"\",\"\",'{S1}'!I{r})", f"=IF('{S2}'!I{r}=\"\",\"\",'{S2}'!I{r})"]
        for col, v in enumerate(vals, 1):
            c = ws.cell(r, col, v); _style(c, fill=F_INPUT if col in (10, 12) else None)
        for col in (1, 3, 7, 8, 9, 10, 11): ws.cell(r, col).alignment = CENTER
        ws.cell(r, 11).font = _f(size=11, bold=True)
        ws.row_dimensions[r].height = _height(it["original"], it["transformed"], width=42)
    dv = DataValidation(type="list", formula1='"1,0"', allow_blank=True, showErrorMessage=True,
                        errorTitle="Isi 1 atau 0", error="ADJ hanya boleh 1 (Ya) atau 0 (Tidak).")
    dv.add(f"J{FIRST}:J{last}"); ws.add_data_validation(dv)
    rng = f"A{FIRST}:N{last}"
    ws.conditional_formatting.add(rng, FormulaRule(formula=[f'$I{FIRST}="BEDA → ISI ADJ"'], fill=F_BAD, stopIfTrue=True))
    ws.conditional_formatting.add(rng, FormulaRule(formula=[f'$I{FIRST}="BEDA → SUDAH ADJ"'], fill=F_WARN, stopIfTrue=True))
    ws.conditional_formatting.add(f"I{FIRST}:I{last}", FormulaRule(formula=[f'$I{FIRST}="SEPAKAT"'], fill=F_OK))
    ws.freeze_panes = ws.cell(FIRST, 4); ws.auto_filter.ref = f"A{HDR}:N{last}"

def _summary(wb, last, mrs):
    ws = wb.create_sheet(SR); ws.sheet_view.showGridLines = False
    _title(ws, "REKAP – progres, kesepakatan antar-penilai, dan validitas item (otomatis)",
           "Semua angka berupa rumus; tidak perlu diisi. κ = Cohen's kappa dihitung dari baris yang sudah dinilai kedua penilai.")
    A = lambda col: f"'{SA}'!${col}${FIRST}:${col}${last}"
    C, G, H, I, K = A("C"), A("G"), A("H"), A("I"), A("K")
    heads = ["Jenis item", "Jumlah item", "Dinilai P1", "Dinilai P2", "Dinilai keduanya", "Sepakat", "% sepakat",
             "Cohen's κ", "Interpretasi κ", "Perlu ADJ (belum)", "FINAL valid (1)", "FINAL tidak valid (0)", "Tingkat validitas",
             "bantu: p(1) P1", "bantu: p(1) P2", "bantu: pe"]
    widths = [14, 11, 11, 11, 12, 10, 11, 10, 18, 12, 12, 13, 12, 11, 11, 10]
    for k, (h, w) in enumerate(zip(heads, widths), 1):
        _style(ws.cell(HDR, k, h), _f(size=10, bold=True, color="FFFFFF"), F_HEAD, CENTER)
        ws.column_dimensions[ws.cell(HDR, k).column_letter].width = w
    ws.row_dimensions[HDR].height = 32
    for k, mr in enumerate(list(mrs) + ["TOTAL"]):
        r = FIRST + k; cond = f'({C}<>"")' if mr == "TOTAL" else f'({C}="{mr}")'
        both = f'{cond}*({G}<>"")*({H}<>"")'
        f = [mr, f"=SUMPRODUCT({cond}*1)", f'=SUMPRODUCT({cond}*({G}<>""))', f'=SUMPRODUCT({cond}*({H}<>""))',
             f"=SUMPRODUCT({both})", f"=SUMPRODUCT({both}*({G}={H}))", f'=IF(E{r}=0,"",F{r}/E{r})',
             f'=IF(E{r}=0,"",IF(P{r}=1,"n/a",(G{r}-P{r})/(1-P{r})))',
             f'=IF(OR(H{r}="",H{r}="n/a"),"",IF(H{r}<0,"lebih buruk dari acak",IF(H{r}<=0.2,"sangat rendah",'
             f'IF(H{r}<=0.4,"rendah",IF(H{r}<=0.6,"sedang",IF(H{r}<=0.8,"substansial","hampir sempurna"))))))',
             f'=SUMPRODUCT({cond}*({I}="BEDA → ISI ADJ"))', f"=SUMPRODUCT({cond}*({K}=1))", f"=SUMPRODUCT({cond}*({K}=0)*({K}<>\"\"))",
             f'=IF(K{r}+L{r}=0,"",K{r}/(K{r}+L{r}))',
             f'=IF(E{r}=0,"",SUMPRODUCT({both}*({G}=1))/E{r})', f'=IF(E{r}=0,"",SUMPRODUCT({both}*({H}=1))/E{r})',
             f'=IF(E{r}=0,"",N{r}*O{r}+(1-N{r})*(1-O{r}))']
        for col, v in enumerate(f, 1):
            c = ws.cell(r, col, v); _style(c, _f(size=10, bold=mr == "TOTAL", color=GREY if col > 13 else None),
                                           F_SECTION if mr == "TOTAL" else None, CENTER)
        for col in (7, 13, 14, 15): ws.cell(r, col).number_format = "0.0%"
        ws.cell(r, 8).number_format = ws.cell(r, 16).number_format = "0.000"
    r = FIRST + len(mrs) + 2
    notes = ["Catatan:",
             "• % sepakat dan κ hanya memakai baris yang sudah dinilai kedua penilai. κ = (po − pe) / (1 − pe), pe dari proporsi '1' tiap penilai.",
             "• Interpretasi κ mengikuti Landis & Koch (1977): ≤0,20 sangat rendah · 0,21–0,40 rendah · 0,41–0,60 sedang · 0,61–0,80 substansial · >0,80 hampir sempurna.",
             "• κ bisa 'n/a' bila kedua penilai memberi nilai yang sama untuk semua item (pe = 1); laporkan % sepakat saja.",
             "• FINAL = nilai bila kedua penilai sepakat, atau ADJ bila berbeda. Tingkat validitas = FINAL valid / (valid + tidak valid).",
             "• Item FINAL = 0 masuk daftar invalid_items di validation.json (run_llm.py score) dan dikeluarkan dari analisis."]
    for k, t in enumerate(notes):
        ws.cell(r + k, 1, t).font = _f(size=10, bold=k == 0, color=GREY if k else NAVY)

# ---------------------------------------------------------------- public API
def build(rows, out, policy):
    """rows: dicts with item_id, mr, original, transformed (+ erased/swapped/auto_valid)."""
    counts = {m: sum(r["mr"] == m for r in rows) for m in MR_INFO if any(r["mr"] == m for r in rows)}
    wb = Workbook(); _instructions(wb, policy, counts, len(rows))
    last = _rater(wb, S1, rows, 1); _rater(wb, S2, rows, 2)
    _adjudication(wb, rows, last); _summary(wb, last, list(counts))
    wb.calculation.fullCalcOnLoad = True
    wb.save(out)

def is_hitl(path):
    return S1 in load_workbook(path, read_only=True).sheetnames

def read(path):
    """-> list of dicts: item_id, mr, r1, r2, adj (ints or None), notes. Reads typed cells only."""
    wb = load_workbook(path)
    s1, s2, sa = wb[S1], wb[S2], wb[SA]
    num = lambda v: None if v in (None, "") else int(float(v))
    out = []
    for r in range(FIRST, s1.max_row + 1):
        iid = s1.cell(r, 2).value
        if not iid: continue
        if s2.cell(r, 2).value != iid or sa.cell(r, 2).value != iid:
            raise ValueError(f"baris {r}: item_id tidak sama antar lembar ({iid}) – urutan baris berubah?")
        out.append({"item_id": iid, "mr": s1.cell(r, 3).value, "r1": num(s1.cell(r, 8).value), "r2": num(s2.cell(r, 8).value),
                    "adj": num(sa.cell(r, 10).value), "notes": sa.cell(r, 12).value})
    return out
