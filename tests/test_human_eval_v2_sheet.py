"""E1-CF v2 rater workbooks: dropdown-only, locked cells, blinding, row counts, read-back."""
import os, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
import openpyxl
import human_eval_v2_sheet as H

BLIND = ("REPLAY", "NEU", "PLC", "SWAP", "DEL", "PLCDEL")

class V2Sheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp(); cls.n = H.build(os.path.join(cls.d, "m"), os.path.join(cls.d, "p"))
        cls.p1, cls.p2 = (os.path.join(cls.d, "m", f"rater{i}.xlsx") for i in (1, 2))

    def test_row_counts(self):
        self.assertEqual(self.n, 88 + 88 + 80 + 88)
        r = H.read(self.p1); self.assertEqual(len(r), self.n); self.assertEqual(sum(x["base"] for x in r), 88)

    def test_orders_differ_between_raters_and_ids_match(self):
        a, b = [x["row_id"] for x in H.read(self.p1)], [x["row_id"] for x in H.read(self.p2)]
        self.assertEqual(set(a), set(b)); self.assertNotEqual(a, b)

    def test_only_dropdown_cells_are_editable(self):
        ws = openpyxl.load_workbook(self.p1)["Penilaian"]; self.assertTrue(ws.protection.sheet)
        cols = {c.column for row in ws.iter_rows(min_row=H.FIRST) for c in row if not c.protection.locked}
        self.assertTrue(cols <= set(range(H.FIRST_Q, H.FIRST_Q + len(H.QUESTIONS))))
        self.assertEqual(len(ws.data_validations.dataValidation), len(H.QUESTIONS))
        for dv in ws.data_validations.dataValidation: self.assertEqual((dv.type, dv.errorStyle), ("list", "stop"))
        base = [r for r in range(H.FIRST, ws.max_row + 1) if ws.cell(r, 3).value == "—"]
        for r in base:     # a base row has an editable Q5 cell only
            self.assertEqual([k for k in range(H.FIRST_Q, H.FIRST_Q + 7) if not ws.cell(r, k).protection.locked], [H.FIRST_Q + 4])

    def test_no_condition_names_visible_to_raters(self):
        for path in (self.p1, self.p2):
            wb = openpyxl.load_workbook(path)
            for ws in wb:
                for row in ws.iter_rows():
                    for c in row:
                        if isinstance(c.value, str) and c.column != 2 and c.column != 3:
                            for name in BLIND: self.assertNotIn(name, c.value.split())

    def test_read_rejects_free_text_and_reports_missing(self):
        wb = openpyxl.load_workbook(self.p1); ws = wb["Penilaian"]
        self.assertEqual(len(H.unanswered(H.read(self.p1))), self.n)
        ws.cell(H.FIRST, H.FIRST_Q + 4).value = "mungkin"; out = os.path.join(self.d, "bad.xlsx"); wb.save(out)
        with self.assertRaises(ValueError): H.read(out)

if __name__ == "__main__":
    unittest.main()
