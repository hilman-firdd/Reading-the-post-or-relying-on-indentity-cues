"""Unit tests for response_classifier.py.   Run:  python -m unittest discover -s tests -v

Fixtures mirror the structure of real responses in runs/ (slurs replaced by placeholders)."""
import glob, json, os, sys, unittest
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from response_classifier import classify, classify_record, CATEGORIES  # noqa: E402


class ValidVerdict(unittest.TestCase):
    def test_fenced_json_violating(self):
        r = classify('```json\n{"verdict": "violating", "quotes": ["XXX"], "confidence": 0.9}\n```')
        self.assertEqual((r["category"], r["verdict"]), ("VALID_VERDICT", "violating"))
        self.assertFalse(r["needs_manual_review"])

    def test_not_violating_quotes_first(self):
        r = classify('{"quotes": [], "verdict": "not_violating", "confidence": 0.8}')
        self.assertEqual((r["category"], r["verdict"]), ("VALID_VERDICT", "not_violating"))

    def test_synonym_mapping_matches_run_llm(self):
        self.assertEqual(classify('{"verdict": "violation"}')["verdict"], "violating")
        self.assertEqual(classify('{"verdict": "non-violating"}')["verdict"], "not_violating")

    def test_json_plus_refusal_language_is_flagged(self):
        r = classify('I cannot help with hate. {"verdict": "violating", "quotes": []}')
        self.assertEqual(r["category"], "VALID_VERDICT")
        self.assertTrue(r["needs_manual_review"])


class Abstention(unittest.TestCase):
    def test_json_insufficient(self):
        r = classify('{"verdict": "insufficient", "quotes": [], "confidence": 0.5}')
        self.assertEqual((r["category"], r["verdict"]), ("ABSTENTION", "insufficient"))
        self.assertFalse(r["needs_manual_review"])

    def test_free_text_cannot_determine_is_abstention_not_refusal(self):
        r = classify("I cannot determine whether this post violates the policy without more context.")
        self.assertEqual(r["category"], "ABSTENTION")
        self.assertTrue(r["needs_manual_review"])

    def test_word_cannot_alone_is_not_refusal(self):
        r = classify("The post cannot be judged from its text alone.")
        self.assertNotEqual(r["category"], "REFUSAL")


class Refusal(unittest.TestCase):
    def test_llama_style_refusal(self):
        r = classify("I cannot create content that promotes hate speech. Is there something else I can help you with?")
        self.assertEqual(r["category"], "REFUSAL")
        self.assertIsNone(r["verdict"])

    def test_curly_apostrophe_refusal(self):
        r = classify("I can’t fulfill that request. I can’t create content that promotes hate speech or discrimination.")
        self.assertEqual(r["category"], "REFUSAL")

    def test_wont_help_refusal(self):
        self.assertEqual(classify("I won't help with that.")["category"], "REFUSAL")

    def test_refusal_never_gets_a_verdict(self):
        self.assertIsNone(classify("I'm unable to assist with this request.")["verdict"])


class Unparseable(unittest.TestCase):
    def test_truncated_json_recovers_verdict_for_sensitivity_only(self):
        raw = '```json\n{"verdict": "violating", "quotes": ["XX YY", "XX YY", "XX YY", "XX'
        r = classify(raw)
        self.assertEqual(r["category"], "UNPARSEABLE")
        self.assertTrue(r["truncated"])
        self.assertEqual(r["recovered_verdict"], "violating")
        self.assertIsNone(r["verdict"])

    def test_unescaped_inner_quotes(self):
        raw = '```json\n{"verdict": "violating", "quotes": ["he said "XX" twice"], "confidence": 0.9}\n```'
        r = classify(raw)
        self.assertEqual(r["category"], "UNPARSEABLE")
        self.assertFalse(r["truncated"])
        self.assertEqual(r["recovered_verdict"], "violating")

    def test_null_verdict_is_not_abstention(self):
        r = classify('{"quotes": [], "verdict": null, "confidence": 0.0}')
        self.assertEqual(r["category"], "UNPARSEABLE")
        self.assertTrue(r["needs_manual_review"])

    def test_unknown_verdict_value(self):
        self.assertEqual(classify('{"verdict": "maybe"}')["category"], "UNPARSEABLE")

    def test_missing_verdict_key(self):
        self.assertEqual(classify('{"quotes": ["x"]}')["category"], "UNPARSEABLE")

    def test_free_text_without_signal(self):
        r = classify("This is a post about dogs.")
        self.assertEqual(r["category"], "UNPARSEABLE")
        self.assertTrue(r["needs_manual_review"])


class EmptyAndErrors(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(classify("   \n")["category"], "EMPTY_RESPONSE")

    def test_none_raw_is_generation_error(self):
        self.assertEqual(classify(None)["category"], "GENERATION_ERROR")

    def test_error_field_is_generation_error(self):
        self.assertEqual(classify("x", {"error": "timeout"})["category"], "GENERATION_ERROR")

    def test_baseline_record_without_raw(self):
        r = classify_record({"item_id": "a", "verdict": "violating", "quotes": []})
        self.assertEqual((r["category"], r["verdict"]), ("VALID_VERDICT", "violating"))


@unittest.skipUnless(glob.glob(os.path.join(ROOT, "runs", "*_direct.jsonl")), "run files not present")
class AgainstRealRuns(unittest.TestCase):
    """Invariants on the actual run files (they are only read)."""
    @classmethod
    def setUpClass(cls):
        cls.runs = {}
        for p in sorted(glob.glob(os.path.join(ROOT, "runs", "*_direct.jsonl")) + glob.glob(os.path.join(ROOT, "runs", "*_evidence.jsonl"))):
            recs = [json.loads(l) for l in open(p)]
            cls.runs[os.path.basename(p)] = [(r, classify_record(r)) for r in recs]

    def test_categories_are_exhaustive(self):
        for name, rc in self.runs.items():
            for _, c in rc: self.assertIn(c["category"], CATEGORIES, name)

    def test_valid_verdicts_agree_with_run_time_parser(self):
        # where the classifier finds a schema verdict, the original run_llm.parse stored the same one
        for name, rc in self.runs.items():
            bad = [r["item_id"] for r, c in rc if c["category"] in ("VALID_VERDICT", "ABSTENTION") and c["verdict"] != r["verdict"]]
            self.assertEqual(bad, [], name)

    def test_refusals_were_stored_as_insufficient_originally(self):
        # documents the original defect: every refusal had been folded into 'insufficient'
        for name, rc in self.runs.items():
            for r, c in rc:
                if c["category"] == "REFUSAL": self.assertIn(r["verdict"], ("insufficient", "refused"), name)

    def test_known_counts(self):
        cnt = {n: Counter(c["category"] for _, c in rc) for n, rc in self.runs.items()}
        # 2383 non-JSON llama answers: 2380 refusals + 3 free-text "I cannot determine whether ..." abstentions
        # (the earlier relabel_refusals.py regex counted those 3 as refusals; the audited classifier does not)
        self.assertEqual(cnt["llama3.1_8b_direct.jsonl"]["REFUSAL"], 2380)
        self.assertEqual(sum(1 for r, c in self.runs["llama3.1_8b_direct.jsonl"]
                             if c["category"] == "ABSTENTION" and c["reason"].startswith("free-text")), 3)
        self.assertEqual(cnt["llama3.1_8b_evidence.jsonl"]["REFUSAL"], 3436)
        for n in ("qwen2.5_7b_direct.jsonl", "qwen2.5_7b_evidence.jsonl", "gemma2_9b_direct.jsonl", "gemma2_9b_evidence.jsonl"):
            self.assertEqual(cnt[n]["REFUSAL"], 0, n)


if __name__ == "__main__":
    unittest.main()
