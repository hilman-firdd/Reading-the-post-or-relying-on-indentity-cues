"""E1-CF v2 item builder: determinism, rule conformance, and consistency with the v1 items."""
import hashlib, importlib.util, json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
spec = importlib.util.spec_from_file_location("b2", "build_e1cf_v2.py"); B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
OUT = "results/e1_counterfactual_v2/items_e1cf_v2.jsonl"

def load(p): return [json.loads(l) for l in open(p)]
def toks(r): return r["tokens"] if isinstance(r["tokens"], list) else json.loads(r["tokens"])

class V2(unittest.TestCase):
    def test_tables_are_consistent(self):
        self.assertEqual(set(B.TOKEN_CLASS), set(B.GROUP_OF))                   # every identity token has a class
        for g, forms in B.FORMS.items():
            for cls, f in forms.items(): self.assertEqual(B.GROUP_OF[f], g)    # every form belongs to its own group
        for t, cls in B.TOKEN_CLASS.items(): self.assertIn(cls, ("SG", "PL", "ADJ", "REL"))

    def test_build_is_deterministic(self):
        B.main(); a = hashlib.sha1(open(OUT, "rb").read()).hexdigest(); B.main()
        self.assertEqual(a, hashlib.sha1(open(OUT, "rb").read()).hexdigest())
        self.assertEqual(a, json.load(open("results/e1_counterfactual_v2/build_summary.json"))["items_sha1"])

    def test_unchanged_conditions_match_v1(self):
        v1 = {(r["e1_item_id"], r["cf_condition"]): r["text"] for r in load("results/e1_counterfactual/items_e1cf.jsonl")}
        for r in load(OUT):
            if r["cf_condition"] in ("REPLAY", "NEU", "PLC"): self.assertEqual(r["text"], v1[(r["e1_item_id"], r["cf_condition"])])

    def test_swap_follows_the_rules(self):
        replay = {r["e1_item_id"]: toks(r) for r in load(OUT) if r["cf_condition"] == "REPLAY"}
        n = 0
        for r in load(OUT):
            if r["cf_condition"] not in ("SWAP", "SWAP2"): continue
            n += 1; src, new, m = replay[r["e1_item_id"]], toks(r), r["cf_meta"]["swap_A_to_B"]
            self.assertEqual(len(src), len(new))                                   # same number of tokens
            self.assertEqual(len(set(m.values())), len(m))                         # distinct B per A
            self.assertFalse(set(m.values()) & set(m))                             # B is never an A of the post
            for a, b_ in zip(src, new):
                g = B.GROUP_OF.get(a.lower())
                if g in m:
                    self.assertEqual(B.GROUP_OF[b_.lower()], m[g])                 # replaced by a form of B
                    self.assertEqual(b_.lower(), B.FORMS[m[g]][B.TOKEN_CLASS[a.lower()]])   # the slot of the original token (number, part of speech)
                    if g not in B.TYPE_OF: self.assertEqual(r["cf_meta"]["stratum"], "cross_type")
                    else: self.assertEqual(B.TYPE_OF[m[g]], B.TYPE_OF[g])          # same protected-attribute type
                else: self.assertEqual(a, b_)                                      # all other tokens untouched
        self.assertGreater(n, 100)

    def test_swap2_differs_from_swap(self):
        s1 = {r["e1_item_id"]: r["cf_meta"]["swap_A_to_B"] for r in load(OUT) if r["cf_condition"] == "SWAP"}
        for r in load(OUT):
            if r["cf_condition"] == "SWAP2":
                for a, b_ in r["cf_meta"]["swap_A_to_B"].items(): self.assertNotEqual(b_, s1[r["e1_item_id"]][a])

if __name__ == "__main__":
    unittest.main()
