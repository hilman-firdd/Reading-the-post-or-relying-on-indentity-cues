"""The ablation prompts differ from their neighbours only in the stated part (run_ablation.sh)."""
import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("run_llm", os.path.join(ROOT, "run_llm.py"))
rl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rl)
IT = {"policy_text": "Content policy. POLICY TEXT.", "text": "some post text"}
INS_DIRECT = "Answer 'insufficient' if no policy is given or the post cannot be judged from its text."
INS_EVID = "If no policy is given or the words do not settle the case, answer 'insufficient'."


class PromptAblation(unittest.TestCase):
    def test_original_prompts_unchanged(self):
        self.assertIs(rl.PROMPTS["direct"], rl.p_direct)
        self.assertIs(rl.PROMPTS["evidence"], rl.p_evidence)

    def test_C_turns_quote_only_into_evidence(self):
        self.assertEqual(rl.p_abl_quote_only(IT).replace(INS_DIRECT, INS_EVID), rl.p_evidence(IT))

    def test_B_turns_quote_first_into_quote_only(self):
        a = rl.p_abl_quote_first(IT).replace("decide whether the post violates the policy.", "decide ONLY from those words and the policy.")
        self.assertEqual(a, rl.p_abl_quote_only(IT))

    def test_A_keeps_policy_post_and_insufficient_rule_of_direct(self):
        a, d = rl.p_abl_quote_first(IT), rl.p_direct(IT)
        for part in (IT["policy_text"], "POST: " + IT["text"], INS_DIRECT, "Return ONLY JSON"):
            self.assertIn(part, a)
            self.assertIn(part, d)
        self.assertTrue(a.index('"quotes"') < a.index('"verdict"'))   # quotes first, as in evidence
        self.assertTrue(d.index('"verdict"') < d.index('"quotes"'))


if __name__ == "__main__":
    unittest.main()
