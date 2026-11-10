#!/usr/bin/env python3
"""
Human-in-the-loop (HITL) validation workbook for the MR items (used by run_llm.py export/score).

Every answer is a Ya/Tidak dropdown; all other cells are locked, so there is no free text.
  Petunjuk   short instructions       Penilai 1 / Penilai 2   one dropdown per row
  Keputusan  settles disagreements    Rekap                   progress, agreement, kappa, validity (formulas)

read() uses only the dropdown cells (never formula results), so scoring does not depend on Excel recalculation.
"""
import difflib
from openpyxl import Workbook, load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.worksheet.datavalidation import DataValidation

FONT, NAVY, GREY, RED, BLUE = "Arial", "1F3864", "595959", "C00000", "1F4E9E"
fill = lambda c: PatternFill("solid", fgColor=c)
F_HEAD, F_INPUT, F_SUB, F_WARN, F_OK, F_BAD = fill(NAVY), fill("FFF2CC"), fill("D9E1F2"), fill("FCE4D6"), fill("E2EFDA"), fill("F8CBAD")
THIN = Side(style="thin", color="BFBFBF"); BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top"); CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
HDR, FIRST = 4, 5  # header row / first data row on the rater and decision sheets
S1, S2, SK, SR = "Penilai 1", "Penilai 2", "Keputusan", "Rekap"
YES, NO = "Ya", "Tidak"; TODO = "PERLU DIPUTUSKAN"
NARROW = ("Kebijakan sempit: hanya serangan terhadap ras, etnis, kebangsaan, agama, gender, orientasi seksual, "
          "disabilitas, atau status imigran/pengungsi yang melanggar. Hinaan atau kata kasar lainnya DIPERBOLEHKAN.")

MR_INFO = {
    "E1": dict(q="Setelah kata merah dihapus, apakah teks hasil sudah TIDAK melanggar?",
               what="Kata bukti dihapus",
               yes="Tidak tersisa hinaan, slur, atau serangan. Kalimat yang terpotong tidak masalah.",
               no="Masih ada hinaan, slur, atau serangan."),
    "E2": dict(q="Setelah kata biru disisipkan, apakah teks hasil sekarang MELANGGAR?",
               what="Kata bukti disisipkan",
               yes="Kata sisipan jelas berisi hinaan, slur, atau serangan.",
               no="Kata sisipan tidak berbahaya atau ambigu."),
    "R2": dict(q="Menurut kebijakan sempit di kolom Teks hasil, apakah postingan ini memang TIDAK melanggar?",
               what="Kebijakan dipersempit",
               yes="Hanya hinaan/kata kasar, tidak menyerang atribut terlindungi.",
               no="Menyerang orang/kelompok karena atribut terlindungi."),
    "I1": dict(q="Apakah teks hasil tetap wajar dan maksudnya sama, hanya kelompoknya yang berganti?",
               what="Kelompok ditukar",
               yes="Wajar dibaca dan maksudnya sama.",
               no="Janggal, maknanya berubah, atau sasarannya campur aduk."),
    "I3": dict(q="Apakah teks hasil punya makna, nada, dan sasaran yang sama dengan teks asli?",
               what="Ditulis ulang oleh AI",
               yes="Makna, tingkat kekasaran, dan sasaran sama.",
               no="Dilunakkan/diperkeras, sasaran berubah, atau isi ditambah/dibuang."),
}

def _f(**k): return Font(name=FONT, **{"size": 11, **k})

def _style(c, font=None, bg=None, align=WRAP):
    c.font = font or _f(); c.alignment = align; c.border = BOX
    if bg: c.fill = bg

def _height(*texts, width=50):
    lines = max(1, *(-(-len(t or "") // int(width * 1.05)) for t in texts))
    return min(409, 15 * lines + 8)

def _rich(tokens, marked, color):
    plain, hit = InlineFont(rFont=FONT, sz=11), InlineFont(rFont=FONT, sz=11, b=True, color=color)
    runs, buf, cur = [], [], None
    for k, t in enumerate(tokens):
        m = k in marked
        if cur is not None and m != cur: runs.append(TextBlock(hit if cur else plain, " ".join(buf) + " ")); buf = []
        buf.append(t); cur = m
    if buf: runs.append(TextBlock(hit if cur else plain, " ".join(buf)))
    return CellRichText(runs) if runs else ""

def _marked(it):
    """Display values for the two text columns: changed words in colour (E1/E2/I1), R2 shows the narrowed rule."""
    o, t = it["original"], it["transformed"]
    if it["mr"] == "R2": return o, NARROW
    if it["mr"] == "I3": return o, t
    a, b = o.split(), t.split(); ma, mb = set(), set()
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag != "equal": ma.update(range(i1, i2)); mb.update(range(j1, j2))
    return _rich(a, ma, RED), _rich(b, mb, BLUE)

def _lock(ws):
    ws.protection.sheet = True; ws.protection.autoFilter = False; ws.protection.formatRows = False

def _dropdown(ws, rng):
    dv = DataValidation(type="list", formula1=f'"{YES},{NO}"', allow_blank=True, errorStyle="stop", showErrorMessage=True,
                        errorTitle="Pilih dari daftar", error="Pilih Ya atau Tidak dari dropdown.")
    dv.add(rng); ws.add_data_validation(dv)

def _head(ws, heads, height=34):
    for k, (h, w) in enumerate(heads, 1):
        _style(ws.cell(HDR, k, h), _f(bold=True, color="FFFFFF"), F_HEAD, CENTER)
        ws.column_dimensions[ws.cell(HDR, k).column_letter].width = w
    ws.row_dimensions[HDR].height = height

def _instructions(wb, counts, n):
    ws = wb.active; ws.title = "Petunjuk"; ws.sheet_view.showGridLines = False
    for col, w in zip("ABCDE", (3, 24, 50, 42, 42)): ws.column_dimensions[col].width = w
    ws["B1"] = "Validasi Manusia"; ws["B1"].font = _f(size=16, bold=True, color=NAVY)
    ws["B2"] = f"{n} baris. Tugas Anda hanya memilih Ya atau Tidak di setiap baris."; ws["B2"].font = _f(color=GREY)
    def band(r, text, bg, font, h):
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)
        _style(ws.cell(r, 2, text), font, bg, Alignment(wrap_text=True, vertical="center")); ws.row_dimensions[r].height = h
    band(4, "Peringatan: berisi ujaran kebencian dan kata kasar asli. Hanya untuk riset. Boleh berhenti dan istirahat kapan saja.",
         F_WARN, _f(bold=True, color="833C0B"), 24)
    band(6, "Cara mengisi", F_HEAD, _f(bold=True, color="FFFFFF"), 22)
    steps = [("1. Penilai 1", f"Buka lembar '{S1}'. Baca teks, lalu pilih Ya atau Tidak di kolom kuning sampai habis."),
             ("2. Penilai 2", f"Buka lembar '{S2}' dan lakukan hal yang sama. Jangan melihat jawaban Penilai 1."),
             ("3. Pemutus", f"Buka lembar '{SK}'. Pilih Ya atau Tidak hanya pada baris oranye (dua penilai berbeda)."),
             ("4. Selesai", f"Lihat hasilnya di lembar '{SR}', lalu simpan file sebagai human_validation_filled.xlsx.")]
    r = 7
    for lab, txt in steps:
        _style(ws.cell(r, 2, lab), _f(bold=True), F_SUB)
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=5)
        _style(ws.cell(r, 3, txt))
        for c in (4, 5): ws.cell(r, c).border = BOX
        ws.row_dimensions[r].height = 22; r += 1
    r += 1; band(r, "Arti jawaban. Yang dinilai selalu pertanyaan di barisnya, dan tata bahasa yang janggal diabaikan kecuali ditanyakan.",
                 F_HEAD, _f(bold=True, color="FFFFFF"), 22); r += 1
    for col, h in zip(range(2, 6), ("Yang dilakukan", "Pertanyaan", "Pilih Ya bila", "Pilih Tidak bila")):
        _style(ws.cell(r, col, h), _f(bold=True), F_SUB, CENTER)
    r += 1
    for mr, d in MR_INFO.items():
        if mr not in counts: continue
        for col, v in zip(range(2, 6), (f"{d['what']} ({counts[mr]} baris)", d["q"], d["yes"], d["no"])): _style(ws.cell(r, col, v))
        ws.cell(r, 4).fill, ws.cell(r, 5).fill = F_OK, F_BAD
        ws.row_dimensions[r].height = _height(d["q"], width=48); r += 1
    r += 1; band(r, "Melanggar = menyerang atau mengajak mencelakai orang karena ras, etnis, kebangsaan, agama, gender, orientasi seksual, "
                    "disabilitas, atau status imigran; atau berisi hinaan/slur yang ditujukan ke orang atau kelompok.", None, _f(), 38); r += 1
    band(r, "Contoh: teks hasil 'all christians should leave' dari 'all muslims should leave' → pertanyaan tukar kelompok → pilih Ya.", None, _f(color=GREY, italic=True), 22); r += 1
    band(r, "Warna: kuning = pilih di sini · merah = kata yang dihapus/ditukar · biru = kata pengganti/sisipan. Sel lain terkunci.", None, _f(color=GREY), 22)

def _rater(wb, title, rows):
    ws = wb.create_sheet(title); ws.sheet_view.showGridLines = False; last = FIRST + len(rows) - 1
    ws["A1"] = f"{title}: pilih Ya atau Tidak di kolom kuning"; ws["A1"].font = _f(size=14, bold=True, color=NAVY)
    ws["A2"] = f'=COUNTA(E{FIRST}:E{last})&" dari {len(rows)} terisi"'; ws["A2"].font = _f(bold=True, color=GREY)
    _head(ws, [("No", 6), ("Teks asli", 52), ("Teks hasil", 52), ("Pertanyaan", 36), ("Jawaban", 12), ("item_id", 14), ("jenis", 6)])
    for k, it in enumerate(rows):
        r = FIRST + k; orig, new = _marked(it); q = MR_INFO[it["mr"]]["q"]
        for col, v in enumerate((k + 1, orig, new, q, None, it["item_id"], it["mr"]), 1): _style(ws.cell(r, col, v))
        ws.cell(r, 1).alignment = CENTER
        e = ws.cell(r, 5); _style(e, _f(bold=True), F_INPUT, CENTER); e.protection = Protection(locked=False)
        ws.row_dimensions[r].height = _height(it["original"], NARROW if it["mr"] == "R2" else it["transformed"], q[:90])
    ws.column_dimensions["F"].hidden = ws.column_dimensions["G"].hidden = True
    _dropdown(ws, f"E{FIRST}:E{last}")
    ws.conditional_formatting.add(f"E{FIRST}:E{last}", FormulaRule(formula=[f'E{FIRST}<>""'], fill=F_OK))
    ws.freeze_panes = ws.cell(FIRST, 1); _lock(ws)
    return last

def _decision(wb, rows, last):
    ws = wb.create_sheet(SK); ws.sheet_view.showGridLines = False
    ws["A1"] = "Keputusan: pilih Ya atau Tidak hanya pada baris oranye"; ws["A1"].font = _f(size=14, bold=True, color=NAVY)
    ws["A2"] = f'=COUNTIF(G{FIRST}:G{last},"{TODO}")&" baris perlu diputuskan"'; ws["A2"].font = _f(bold=True, color=RED)
    _head(ws, [("No", 6), ("Teks asli", 46), ("Teks hasil", 46), ("Pertanyaan", 30), ("Penilai 1", 10), ("Penilai 2", 10),
               ("Status", 19), ("Keputusan", 12), ("Final", 9), ("item_id", 14), ("jenis", 6)])
    for k, it in enumerate(rows):
        r = FIRST + k; orig, new = _marked(it); q = MR_INFO[it["mr"]]["q"]
        vals = (k + 1, orig, new, q, f"=IF('{S1}'!E{r}=\"\",\"\",'{S1}'!E{r})", f"=IF('{S2}'!E{r}=\"\",\"\",'{S2}'!E{r})",
                f'=IF(OR(E{r}="",F{r}=""),"BELUM LENGKAP",IF(E{r}=F{r},"SEPAKAT",IF(H{r}="","{TODO}","SUDAH DIPUTUSKAN")))',
                None, f'=IF(OR(E{r}="",F{r}=""),"",IF(E{r}=F{r},E{r},IF(H{r}="","",H{r})))', it["item_id"], it["mr"])
        for col, v in enumerate(vals, 1): _style(ws.cell(r, col, v))
        for col in (1, 5, 6, 7, 9): ws.cell(r, col).alignment = CENTER
        h = ws.cell(r, 8); _style(h, _f(bold=True), F_INPUT, CENTER); h.protection = Protection(locked=False)
        ws.row_dimensions[r].height = _height(it["original"], NARROW if it["mr"] == "R2" else it["transformed"], width=44)
    ws.column_dimensions["J"].hidden = ws.column_dimensions["K"].hidden = True
    _dropdown(ws, f"H{FIRST}:H{last}")
    ws.conditional_formatting.add(f"A{FIRST}:I{last}", FormulaRule(formula=[f'$G{FIRST}="{TODO}"'], fill=F_BAD))
    ws.conditional_formatting.add(f"G{FIRST}:G{last}", FormulaRule(formula=[f'$G{FIRST}="SEPAKAT"'], fill=F_OK))
    ws.freeze_panes = ws.cell(FIRST, 1); ws.auto_filter.ref = f"A{HDR}:I{last}"; _lock(ws)

def _summary(wb, last, mrs):
    ws = wb.create_sheet(SR); ws.sheet_view.showGridLines = False
    ws["A1"] = "Rekap (otomatis, tidak perlu diisi)"; ws["A1"].font = _f(size=14, bold=True, color=NAVY)
    ws["A2"] = "Kappa dihitung dari baris yang sudah dijawab kedua penilai. Patokan umum: 0,61 ke atas = substansial (Landis & Koch, 1977)."; ws["A2"].font = _f(color=GREY)
    A = lambda col: f"'{SK}'!${col}${FIRST}:${col}${last}"
    M, E, F, G, I = A("K"), A("E"), A("F"), A("G"), A("I")
    _head(ws, [("Yang dilakukan", 24), ("Jumlah baris", 10), ("Dijawab kedua penilai", 12), ("Sepakat", 10), ("Kappa", 9), ("Perlu diputuskan", 12),
               ("Final Ya", 9), ("Final Tidak", 9), ("Validitas", 10), ("p1", 8), ("p2", 8), ("pe", 8)], height=48)
    for k, mr in enumerate(list(mrs) + ["TOTAL"]):
        r = FIRST + k; cond = f'({M}<>"")' if mr == "TOTAL" else f'({M}="{mr}")'; both = f'{cond}*({E}<>"")*({F}<>"")'
        vals = (mr if mr == "TOTAL" else MR_INFO[mr]["what"], f"=SUMPRODUCT({cond}*1)", f"=SUMPRODUCT({both})",
                f'=IF(C{r}=0,"",SUMPRODUCT({both}*({E}={F}))/C{r})', f'=IF(C{r}=0,"",IF(L{r}=1,"n/a",(D{r}-L{r})/(1-L{r})))',
                f'=SUMPRODUCT({cond}*({G}="{TODO}"))', f'=SUMPRODUCT({cond}*({I}="{YES}"))', f'=SUMPRODUCT({cond}*({I}="{NO}"))',
                f'=IF(G{r}+H{r}=0,"",G{r}/(G{r}+H{r}))', f'=IF(C{r}=0,"",SUMPRODUCT({both}*({E}="{YES}"))/C{r})',
                f'=IF(C{r}=0,"",SUMPRODUCT({both}*({F}="{YES}"))/C{r})', f'=IF(C{r}=0,"",J{r}*K{r}+(1-J{r})*(1-K{r}))')
        for col, v in enumerate(vals, 1): _style(ws.cell(r, col, v), _f(bold=mr == "TOTAL"), F_SUB if mr == "TOTAL" else None, CENTER)
        ws.cell(r, 1).alignment = Alignment(vertical="center")
        ws.cell(r, 4).number_format = ws.cell(r, 9).number_format = "0.0%"; ws.cell(r, 5).number_format = "0.000"
    for col in "JKL": ws.column_dimensions[col].hidden = True
    _lock(ws)

def build(rows, out, policy=None):
    """rows: dicts with item_id, mr, original, transformed."""
    counts = {m: sum(r["mr"] == m for r in rows) for m in MR_INFO if any(r["mr"] == m for r in rows)}
    wb = Workbook(); _instructions(wb, counts, len(rows))
    last = _rater(wb, S1, rows); _rater(wb, S2, rows)
    _decision(wb, rows, last); _summary(wb, last, list(counts))
    wb.calculation.fullCalcOnLoad = True; wb.save(out)

def is_hitl(path):
    return S1 in load_workbook(path, read_only=True).sheetnames

def read(path):
    """-> list of dicts: item_id, mr, r1, r2, adj (1/0 or None). Only the dropdown cells are read."""
    wb = load_workbook(path); s1, s2, sk = wb[S1], wb[S2], wb[SK]
    def num(v, where):
        if v in (None, ""): return None
        if v not in (YES, NO): raise ValueError(f"{where}: jawaban '{v}' bukan Ya/Tidak")
        return int(v == YES)
    out = []
    for r in range(FIRST, s1.max_row + 1):
        iid = s1.cell(r, 6).value
        if not iid: continue
        if s2.cell(r, 6).value != iid or sk.cell(r, 10).value != iid:
            raise ValueError(f"baris {r}: item_id tidak sama antar lembar ({iid})")
        out.append({"item_id": iid, "mr": s1.cell(r, 7).value, "r1": num(s1.cell(r, 5).value, f"{S1} baris {r}"),
                    "r2": num(s2.cell(r, 5).value, f"{S2} baris {r}"), "adj": num(sk.cell(r, 8).value, f"{SK} baris {r}")})
    return out
