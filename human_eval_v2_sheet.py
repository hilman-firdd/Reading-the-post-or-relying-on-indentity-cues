#!/usr/bin/env python3
"""
Rater workbooks for the E1-CF v2 human validation (protocol: results/e1_counterfactual_v2/PROTOCOL.md, sections 0b and 3).
Every answer is a dropdown (no free text); every other cell is locked.

  python human_eval_v2_sheet.py build   -> results/e1_counterfactual_v2/materials/rater{1,2}.xlsx   (git-ignored)
                                           results/e1_counterfactual_v2/private/{secret.txt,key.csv}  (git-ignored; do not share, do not open)
  python human_eval_v2_sheet.py read --sheet FILE [--out FILE.json]   validates answers and reports unanswered rows

Rows per rater: 88 base rows (unchanged text, Q5 only) + NEU, SWAP and PLC pairs (88 + 80 + 88). Raters see "original" and "changed"
text only, never condition names; the order is randomised per rater with a secret seed.
"""
import argparse, csv, difflib, hashlib, json, os, secrets, sys

from openpyxl import Workbook, load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.worksheet.datavalidation import DataValidation

D = "results/e1_counterfactual_v2"
ITEMS = f"{D}/items_e1cf_v2.jsonl"
YN = ["Ya", "Tidak", "Tidak bisa dinilai"]
Q5 = ["Tidak melanggar", "Melanggar (a)", "Melanggar (b)", "Melanggar (a) dan (b)", "Tidak bisa dinilai"]
Q4 = ["Ya", "Tidak", "Tidak relevan", "Tidak bisa dinilai"]
QUESTIONS = [  # key, column header, question, options, asked on base rows?
    ("q1", "Q1 Makna", "Apakah makna inti kedua teks sama, selain perubahan yang terlihat?", YN, False),
    ("q2", "Q2 Serangan", "Apakah TEKS DIUBAH masih menghina, menyerang, merendahkan, atau mengajak mencelakai?", YN, False),
    ("q3", "Q3 Sasaran", "Apakah sasaran serangan di TEKS DIUBAH masih jelas?", YN, False),
    ("q4", "Q4 Terlindungi", "Jika kata kelompok diganti dengan kata kelompok lain, apakah keduanya sama-sama atribut terlindungi pada klausul (a)?", Q4, False),
    ("q5", "Q5 Kebijakan", "Apakah teks (pada baris dasar: teks asli; pada baris pasangan: TEKS DIUBAH) melanggar kebijakan, dan pada klausul mana?", Q5, True),
    ("q6", "Q6 Wajar", "Apakah TEKS DIUBAH cukup wajar dan gramatikal untuk dibaca seperti maksudnya?", YN, False),
    ("q7", "Q7 Hanya kata", "Apakah perbedaan kedua teks hanya penggantian kata (tanpa perubahan urutan, kata tambahan, atau tanda baca)?", YN, False),
]
NAVY, GREY, RED, BLUE = "1F3864", "595959", "C00000", "1F4E9E"
FONT = "Arial"
fill = lambda c: PatternFill("solid", fgColor=c)
THIN = Side(style="thin", color="BFBFBF"); BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top"); CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
HDR, FIRST = 4, 5
FIRST_Q = 4          # column of Q1
ROWID_COL = FIRST_Q + len(QUESTIONS)

def _f(**k): return Font(name=FONT, **{"size": 11, **k})
def toks(r): return r["tokens"] if isinstance(r["tokens"], list) else json.loads(r["tokens"])

def _rich(tokens, marked, color):
    plain, hit = InlineFont(rFont=FONT, sz=11), InlineFont(rFont=FONT, sz=11, b=True, color=color)
    runs, buf, cur = [], [], None
    for k, t in enumerate(tokens):
        m = k in marked
        if cur is not None and m != cur: runs.append(TextBlock(hit if cur else plain, " ".join(buf) + " ")); buf = []
        buf.append(t); cur = m
    if buf: runs.append(TextBlock(hit if cur else plain, " ".join(buf)))
    return CellRichText(runs) if runs else ""

def _marked(a, b):
    ma, mb = set(), set()
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag != "equal": ma.update(range(i1, i2)); mb.update(range(j1, j2))
    return _rich(a, ma, RED), _rich(b, mb, BLUE)

def rows_from_items(secret):
    items = [json.loads(l) for l in open(ITEMS)]
    by = {}
    for r in items: by.setdefault(r["e1_item_id"], {})[r["cf_condition"]] = r
    out, policy = [], None
    for p in sorted(by):
        c = by[p]; base = toks(c["REPLAY"]); policy = policy or c["REPLAY"]["policy_text"]
        rid = lambda cond: hashlib.sha1((secret + "|row|" + p + "|" + cond).encode()).hexdigest()[:10]
        out.append({"row_id": rid("BASE"), "e1_item_id": p, "condition": "BASE", "a": base, "b": None})
        for cond in ("NEU", "SWAP", "PLC"):
            if cond in c: out.append({"row_id": rid(cond), "e1_item_id": p, "condition": cond, "a": base, "b": toks(c[cond])})
    return out, policy

def _petunjuk(wb, policy, n):
    ws = wb.active; ws.title = "Petunjuk"; ws.sheet_view.showGridLines = False; ws.column_dimensions["A"].width = 3; ws.column_dimensions["B"].width = 120
    ws["B1"] = "Penilaian manusia: pasangan teks"; ws["B1"].font = _f(size=16, bold=True, color=NAVY)
    lines = [f"{n} baris. Tugas Anda hanya memilih jawaban dari dropdown (kolom kuning). Jangan melihat jawaban penilai lain.",
             "Peringatan: berisi ujaran kebencian dan kata kasar asli. Hanya untuk riset. Boleh berhenti dan istirahat kapan saja.",
             "Baris dengan teks diubah '—': hanya jawab Q5 untuk teks asli. Baris pasangan: bandingkan TEKS ASLI dengan TEKS DIUBAH (kata yang berbeda ditandai merah di asli dan biru di diubah).",
             "Pilih 'Tidak bisa dinilai' bila memang tidak bisa memutuskan; jangan memaksa. Tata bahasa yang janggal hanya dinilai pada Q6.",
             "Kebijakan yang dipakai:"]
    for i, t in enumerate(lines, 3): ws.cell(i, 2, t).alignment = WRAP; ws.cell(i, 2).font = _f(bold=(i == 7))
    ws.cell(8, 2, policy).alignment = WRAP; ws.row_dimensions[8].height = 120
    ws.cell(10, 2, "Pertanyaan:").font = _f(bold=True)
    for k, (key, head, q, opts, _) in enumerate(QUESTIONS, 11):
        ws.cell(k, 2, f"{head}: {q}  [{' / '.join(opts)}]").alignment = WRAP; ws.row_dimensions[k].height = 34

def _sheet(wb, rows, order):
    ws = wb.create_sheet("Penilaian"); ws.sheet_view.showGridLines = False; last = FIRST + len(rows) - 1
    ws["A1"] = "Penilaian: pilih jawaban di kolom kuning"; ws["A1"].font = _f(size=14, bold=True, color=NAVY)
    ws["A2"] = f'=COUNTA(D{FIRST}:J{last})&" jawaban terisi"'; ws["A2"].font = _f(bold=True, color=GREY)
    heads = [("No", 6), ("Teks asli", 50), ("Teks diubah", 50)] + [(h, 15) for _, h, _, _, _ in QUESTIONS] + [("row_id", 12)]
    for k, (h, w) in enumerate(heads, 1):
        c = ws.cell(HDR, k, h); c.font = _f(bold=True, color="FFFFFF"); c.fill = fill(NAVY); c.border = BOX; c.alignment = CENTER
        ws.column_dimensions[c.column_letter].width = w
    ws.row_dimensions[HDR].height = 34
    dv = {}
    for k, (key, head, q, opts, _) in enumerate(QUESTIONS):
        v = DataValidation(type="list", formula1='"' + ",".join(opts) + '"', allow_blank=True, errorStyle="stop", showErrorMessage=True,
                           errorTitle="Pilih dari daftar", error="Pilih salah satu dari dropdown."); ws.add_data_validation(v); dv[key] = v
    for n, r in enumerate(order):
        row = FIRST + n; base = r["b"] is None
        if base: a, b = _rich(r["a"], set(), RED), "—"
        else: a, b = _marked(r["a"], r["b"])
        vals = [n + 1, a, b] + [None] * len(QUESTIONS) + [r["row_id"]]
        for col, v in enumerate(vals, 1):
            c = ws.cell(row, col, v); c.border = BOX; c.alignment = WRAP; c.font = _f()
        ws.cell(row, 1).alignment = CENTER
        for k, (key, head, q, opts, on_base) in enumerate(QUESTIONS):
            c = ws.cell(row, FIRST_Q + k); c.alignment = CENTER
            if base and not on_base: c.value = "—"; c.fill = fill("D9D9D9")
            else: c.fill = fill("FFF2CC"); c.protection = Protection(locked=False); dv[key].add(c)
        ws.row_dimensions[row].height = min(409, 15 * max(1, -(-len(" ".join(r["a"])) // 52), -(-len(" ".join(r["b"] or [""])) // 52)) + 10)
    ws.column_dimensions["K"].hidden = True
    ws.freeze_panes = ws.cell(FIRST, 4); ws.protection.sheet = True

def build(out_materials=f"{D}/materials", out_private=f"{D}/private"):
    os.makedirs(out_materials, exist_ok=True); os.makedirs(out_private, exist_ok=True)
    sp = f"{out_private}/secret.txt"
    if not os.path.exists(sp): open(sp, "w").write(secrets.token_hex(16))
    secret = open(sp).read().strip(); rows, policy = rows_from_items(secret); orders = {}
    for rater in (1, 2):
        order = sorted(rows, key=lambda r: hashlib.sha1((secret + f"|order{rater}|" + r["row_id"]).encode()).hexdigest()); orders[rater] = order
        wb = Workbook(); _petunjuk(wb, policy, len(order)); _sheet(wb, rows, order); wb.properties.creator = "openpyxl"; wb.save(f"{out_materials}/rater{rater}.xlsx")
    pos = {rater: {r["row_id"]: i + 1 for i, r in enumerate(orders[rater])} for rater in (1, 2)}
    with open(f"{out_private}/key.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["row_id", "e1_item_id", "condition", "position_rater1", "position_rater2"])
        for r in rows: w.writerow([r["row_id"], r["e1_item_id"], r["condition"], pos[1][r["row_id"]], pos[2][r["row_id"]]])
    return len(rows)

def read(path):
    ws = load_workbook(path)["Penilaian"]; out = []; opts = {q[0]: q[3] for q in QUESTIONS}
    for r in range(FIRST, ws.max_row + 1):
        rid = ws.cell(r, ROWID_COL).value
        if not rid: continue
        ans = {}
        for k, (key, *_rest) in enumerate(QUESTIONS):
            v = ws.cell(r, FIRST_Q + k).value
            if v in (None, "", "—"): ans[key] = None; continue
            if v not in opts[key]: raise ValueError(f"baris {r} {key}: '{v}' bukan salah satu dari {opts[key]}")
            ans[key] = v
        out.append({"row_id": rid, "base": ws.cell(r, 3).value == "—", **ans})
    return out

def unanswered(res):
    """row ids with a missing required answer: base rows need Q5, pair rows need Q1 to Q7."""
    return [r["row_id"] for r in res if any(r[k] is None for k in (["q5"] if r["base"] else [q[0] for q in QUESTIONS]))]

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["build", "read"]); ap.add_argument("--sheet"); ap.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "build": print("rows per rater:", build())
    else:
        res = read(a.sheet); un = unanswered(res)
        print("rows:", len(res), "| base:", sum(r["base"] for r in res), "| rows with a missing answer:", len(un))
        if a.out: json.dump(res, open(a.out, "w"), indent=1, ensure_ascii=False)
