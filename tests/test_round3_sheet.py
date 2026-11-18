"""Round-3 validation workbook (R1 and R3): dropdown-only answers, locked cells, stratified sample, read-back."""
import json, os, sys, tempfile, types, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import openpyxl
import hitl_sheet, run_llm

LABELS = ("hatespeech", "offensive", "normal")

def synthetic(n=6):
    items = [{"item_id": "o", "mr": "ORIG", "policy": "original", "policy_text": "Content policy: original.", "text": "x", "label": "normal"}]
    for mr, pol in (("R1", "Content policy: [no policy text is provided]."), ("R3", "Content policy. Negated.")):
        for lab in LABELS:
            for k in range(n):
                items.append({"item_id": f"{mr}-{lab}-{k}", "mr": mr, "policy": "x", "policy_text": pol, "text": f"post {lab} {k}", "label": lab})
    return items

class Round3(unittest.TestCase):
    def build(self, per_stratum, seed=42):
        d = tempfile.mkdtemp(); p = os.path.join(d, "items.jsonl"); out = os.path.join(d, "r3.xlsx")
        open(p, "w").write("\n".join(json.dumps(i) for i in synthetic()))
        run_llm.cmd_export3(types.SimpleNamespace(items=p, per_stratum=per_stratum, seed=seed, out=out))
        return out

    def test_sample_is_stratified_and_deterministic(self):
        a = hitl_sheet.read(self.build(2)); b = hitl_sheet.read(self.build(2))
        self.assertEqual([r["item_id"] for r in a], [r["item_id"] for r in b])
        self.assertEqual(len(a), 2 * 3 * 2)                       # 2 MRs x 3 labels x 2 items
        for mr in ("R1", "R3"):
            for lab in LABELS:
                self.assertEqual(sum(r["item_id"].startswith(f"{mr}-{lab}-") for r in a), 2)
        self.assertEqual([r["mr"] for r in a], ["R1"] * 6 + ["R3"] * 6)    # grouped by MR

    def test_zero_means_census(self):
        self.assertEqual(len(hitl_sheet.read(self.build(0))), 2 * 3 * 6)

    def test_only_dropdown_cells_are_editable(self):
        wb = openpyxl.load_workbook(self.build(2))
        for sheet, col in ((hitl_sheet.S1, "E"), (hitl_sheet.S2, "E"), (hitl_sheet.SK, "H")):
            ws = wb[sheet]; self.assertTrue(ws.protection.sheet)
            unlocked = {c.column_letter for row in ws.iter_rows(min_row=hitl_sheet.FIRST) for c in row if not c.protection.locked}
            self.assertEqual(unlocked, {col})
            dv = ws.data_validations.dataValidation
            self.assertEqual(len(dv), 1); self.assertEqual(dv[0].type, "list"); self.assertEqual(dv[0].errorStyle, "stop")
            self.assertEqual(dv[0].formula1, '"Ya,Tidak,Ragu"')

    def test_read_rejects_free_text(self):
        out = self.build(1); wb = openpyxl.load_workbook(out); wb[hitl_sheet.S1].cell(hitl_sheet.FIRST, 5).value = "mungkin"; wb.save(out)
        with self.assertRaises(ValueError): hitl_sheet.read(out)

    def test_questions_match_the_reference_label(self):
        ws = openpyxl.load_workbook(self.build(0))[hitl_sheet.S1]
        for r in range(hitl_sheet.FIRST, ws.max_row + 1):
            iid, q = ws.cell(r, 6).value, ws.cell(r, 4).value
            if iid.startswith("R1"): self.assertIn("informasi tidak cukup", q)
            elif "-normal-" in iid: self.assertIn("MELANGGAR?", q)
            else: self.assertIn("TIDAK melanggar?", q)

if __name__ == "__main__":
    unittest.main()
