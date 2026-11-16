#!/usr/bin/env python3
"""
Rater-documentation form: six dropdown questions, no free text.

  python rater_doc_sheet.py build  [--out dokumentasi_penilai.xlsx]
  python rater_doc_sheet.py read   [--sheet dokumentasi_penilai_terisi.xlsx] [--out rater_documentation.json]

`read` accepts only the listed options and reports unanswered questions. Nothing here touches the validation data.
"""
import argparse
import json
import sys

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

NA = "Tidak diketahui / tidak terdokumentasi"
BG = ["Penulis naskah (peneliti utama)", "Penulis lain / pembimbing", "Rekan peneliti atau mahasiswa (bukan penulis)",
      "Anotator eksternal terlatih", "Anotator crowdsourcing", NA]
QUESTIONS = [
    ("rater1_background", "Latar belakang Penilai 1", BG),
    ("rater2_background", "Latar belakang Penilai 2", BG),
    ("independence", "Apakah kedua penilai bekerja tanpa melihat jawaban satu sama lain?",
     ["Ya, dikerjakan terpisah (berkas atau waktu berbeda)", "Ya, satu berkas tetapi tidak saling melihat",
      "Tidak, sebagian saling melihat", "Tidak, saling melihat", NA]),
    ("adjudicator", "Siapa yang memutuskan item yang dinilai berbeda?",
     ["Penulis naskah (peneliti utama)", "Penulis lain / pembimbing", "Pihak ketiga independen", "Salah satu penilai", NA]),
    ("adjudicator_saw_raters", "Apakah pemutus melihat jawaban kedua penilai saat memutuskan?",
     ["Ya, melihat jawaban keduanya", "Tidak, memutuskan tanpa melihatnya", NA]),
    ("preparation", "Persiapan penilai sebelum menilai",
     ["Tidak ada", "Hanya petunjuk di lembar", "Penjelasan lisan atau tertulis singkat", "Pelatihan dengan contoh dan diskusi", NA]),
]
HEAD = PatternFill("solid", fgColor="1F3864"); ASK = PatternFill("solid", fgColor="DDEBF7"); FILL = PatternFill("solid", fgColor="FFF2CC")
THIN = Side(style="thin", color="999999"); BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def build(out):
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "Petunjuk"
    lines = ["Dokumentasi penilai validasi manusia", "",
             "Isi lembar 'Isian': satu dropdown per baris (kolom C, sel kuning). Tidak ada isian bebas.",
             "Jika tidak ingat atau tidak ada catatan, pilih 'Tidak diketahui / tidak terdokumentasi'. Jangan menebak.",
             "Jawaban dipakai untuk bagian metode naskah dan untuk audit (menggantikan 'not documented').",
             "Sel lain dikunci (tanpa kata sandi). Simpan sebagai dokumentasi_penilai_terisi.xlsx dan kirim kembali."]
    for i, t in enumerate(lines, 1):
        ws.cell(i, 1, t).font = Font(bold=(i == 1), size=14 if i == 1 else 11)
    ws.column_dimensions["A"].width = 110
    ls = wb.create_sheet("Daftar")
    for j, (_, _, opts) in enumerate(QUESTIONS, 1):
        for i, o in enumerate(opts, 1): ls.cell(i, j, o)
        ls.column_dimensions[openpyxl.utils.get_column_letter(j)].width = 50
    ls.sheet_state = "hidden"
    w = wb.create_sheet("Isian", 1)
    for c, h in enumerate(["No", "Pertanyaan", "Jawaban (pilih dari dropdown)", "Status"], 1):
        x = w.cell(1, c, h); x.font = Font(bold=True, color="FFFFFF"); x.fill = HEAD; x.border = BOX; x.alignment = Alignment(vertical="center")
    for i, (_, q, opts) in enumerate(QUESTIONS, 1):
        r = i + 1
        w.cell(r, 1, i); w.cell(r, 2, q); w.cell(r, 3).fill = FILL
        w.cell(r, 4, f'=IF(C{r}="","BELUM DIISI","OK")')
        for c in range(1, 5):
            w.cell(r, c).border = BOX; w.cell(r, c).alignment = Alignment(wrap_text=True, vertical="center")
        w.cell(r, 2).fill = ASK
        col = openpyxl.utils.get_column_letter(i)
        dv = DataValidation(type="list", formula1=f"=Daftar!${col}$1:${col}${len(opts)}", allow_blank=True,
                            showErrorMessage=True, errorStyle="stop", errorTitle="Pilih dari daftar", error="Pilih salah satu opsi dari dropdown.")
        w.add_data_validation(dv); dv.add(w.cell(r, 3))
        w.cell(r, 3).protection = openpyxl.styles.Protection(locked=False)
        w.row_dimensions[r].height = 36
    w.cell(8, 2, "Terisi").font = Font(bold=True); w.cell(8, 3, '=COUNTA(C2:C7)&" dari 6"')
    w.column_dimensions["A"].width = 5; w.column_dimensions["B"].width = 58; w.column_dimensions["C"].width = 52; w.column_dimensions["D"].width = 14
    w.freeze_panes = "A2"; w.protection.sheet = True
    wb.save(out); print("written:", out)


def read(path):
    ws = openpyxl.load_workbook(path)["Isian"]; res = {}; missing = []
    for i, (key, q, opts) in enumerate(QUESTIONS, 1):
        v = ws.cell(i + 1, 3).value
        if v is None or str(v).strip() == "": missing.append(key); res[key] = None; continue
        if v not in opts: raise ValueError(f"question {i} ({key}): '{v}' is not one of the allowed options")
        res[key] = v
    res["unanswered"] = missing
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["build", "read"])
    ap.add_argument("--out"); ap.add_argument("--sheet", default="dokumentasi_penilai_terisi.xlsx")
    a = ap.parse_args()
    if a.cmd == "build": build(a.out or "dokumentasi_penilai.xlsx")
    else:
        r = read(a.sheet); json.dump(r, open(a.out or "rater_documentation.json", "w"), indent=1, ensure_ascii=False)
        print("unanswered:", r["unanswered"] or "none"); sys.exit(0)
