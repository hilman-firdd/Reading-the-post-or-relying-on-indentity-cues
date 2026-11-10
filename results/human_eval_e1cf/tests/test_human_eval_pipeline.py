"""Tests for inter_rater_reliability.py and human_evaluation_analysis.py.

Run:  python -m unittest discover -s results/human_eval_e1cf/tests -v

The synthetic annotations created here are written to temporary directories only. They are random labels made to exercise
the code paths; they say nothing about the study and are never written to the study folder.
"""
import csv, importlib, json, os, random, sys, tempfile, unittest, contextlib, io

HERE = os.path.dirname(os.path.abspath(__file__)); PKG = os.path.dirname(HERE); ROOT = os.path.abspath(os.path.join(PKG, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, PKG)
import inter_rater_reliability as irr   # noqa: E402
import human_evaluation_analysis as hea  # noqa: E402

V, N, A = irr.DECISIONS
KEY = irr.load_key()
P1 = f"{PKG}/materials/annotation_phase1_rater1.csv"; P1b = f"{PKG}/materials/annotation_phase1_rater2.csv"
P2 = f"{PKG}/materials/annotation_phase2_rater1.csv"; P2b = f"{PKG}/materials/annotation_phase2_rater2.csv"


def synth(src, dst, rater_id, decisions, seed):
    """Write a fully valid synthetic annotation file. decisions: callable(blind_id, rng) -> category."""
    rng = random.Random(seed); rows = list(csv.DictReader(open(src, newline="")))
    for r in rows:
        d = decisions(r["blind_id"], rng); words = r["text"].split(); r["rater_id"] = rater_id; r["decision"] = d
        if d == V: r["supporting_span"] = words[0]; r["policy_clause"] = "(b)"; r["justification"] = "synthetic test row"
        elif d == N: r["supporting_span"] = ""; r["policy_clause"] = "none"; r["justification"] = "synthetic test row"
        else: r["supporting_span"] = ""; r["policy_clause"] = "unclear"; r["justification"] = "synthetic test row"; r["uncertainty_note"] = "synthetic test row"
    with open(dst, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=irr.REQUIRED_COLS); w.writeheader(); w.writerows(rows)


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()): return fn(*a, **k)


class Coefficients(unittest.TestCase):
    """Hand-computed toy example: a = V V N N, b = V N N N."""
    a = [V, V, N, N]; b = [V, N, N, N]

    def test_kappa(self): self.assertAlmostEqual(irr.cohen_kappa(self.a, self.b), 0.5)
    def test_alpha(self): self.assertAlmostEqual(irr.krippendorff_alpha_nominal(self.a, self.b), 1 - 7 * 2 / 30)
    def test_ac1(self): self.assertAlmostEqual(irr.gwet_ac1(self.a, self.b), (0.75 - 0.234375) / (1 - 0.234375))
    def test_perfect_agreement(self):
        x = [V, N, A, N]; self.assertEqual(irr.cohen_kappa(x, x), 1.0); self.assertEqual(irr.krippendorff_alpha_nominal(x, x), 1.0)
    def test_matches_sklearn_when_available(self):
        try: from sklearn.metrics import cohen_kappa_score
        except Exception: self.skipTest("sklearn missing")
        rng = random.Random(1); a = [rng.choice(irr.DECISIONS) for _ in range(60)]; b = [x if rng.random() < .7 else rng.choice(irr.DECISIONS) for x in a]
        self.assertAlmostEqual(irr.cohen_kappa(a, b), cohen_kappa_score(a, b), places=9)
    def test_single_category_is_undefined_not_crash(self):
        self.assertIsNone(irr.cohen_kappa([N] * 5, [N] * 5)); self.assertIsNone(irr.krippendorff_alpha_nominal([N] * 5, [N] * 5))


class Materials(unittest.TestCase):
    def test_88_items_and_blind(self):
        rows = list(csv.DictReader(open(P1, newline=""))); self.assertEqual(len(rows), 88)
        self.assertTrue(all(not any(r[c] for c in irr.REQUIRED_COLS[2:]) for r in rows))          # annotation fields empty
        self.assertEqual(set(rows[0]), set(irr.REQUIRED_COLS))
    def test_keys_cover_both_phases(self):
        self.assertEqual(len(irr.load_key(phase=1)), 88); self.assertEqual(len(irr.load_key(phase=2)), 88)
    def test_template_equals_phase1_rater1(self): self.assertEqual(open(P1, "rb").read(), open(f"{PKG}/annotation_template.csv", "rb").read())
    def test_blank_template_is_invalid_not_scored(self):
        _, errs = irr.read_annotations(P1, irr.load_key(phase=1)); self.assertTrue(errs)


class Validation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.f = f"{self.tmp.name}/a.csv"
        synth(P1, self.f, "T1", lambda b, r: r.choice(irr.DECISIONS), 3)
    def tearDown(self): self.tmp.cleanup()
    def _mutate(self, fn):
        rows = list(csv.DictReader(open(self.f, newline=""))); fn(rows)
        with open(self.f, "w", newline="") as f: w = csv.DictWriter(f, fieldnames=irr.REQUIRED_COLS); w.writeheader(); w.writerows(rows)
        return irr.read_annotations(self.f, irr.load_key(phase=1))[1]
    def test_valid_file_has_no_errors(self): self.assertEqual(irr.read_annotations(self.f, irr.load_key(phase=1))[1], [])
    def test_bad_decision_label(self): self.assertTrue(any("decision" in e for e in self._mutate(lambda r: r[0].update(decision="VIOLATING"))))
    def test_modified_text(self): self.assertTrue(any("text was modified" in e for e in self._mutate(lambda r: r[0].update(text=r[0]["text"] + " x"))))
    def test_span_must_be_verbatim(self):
        def f(rows):
            r = next(x for x in rows if x["decision"] == V); r["supporting_span"] = "zzzz-not-there"
        self.assertTrue(any("verbatim" in e for e in self._mutate(f)))
    def test_missing_row(self): self.assertTrue(any("missing" in e for e in self._mutate(lambda r: r.pop())))
    def test_duplicate_row(self): self.assertTrue(any("duplicate" in e for e in self._mutate(lambda r: r.append(dict(r[0])))))
    def test_ambiguous_needs_note(self):
        def f(rows): r = next(x for x in rows if x["decision"] == A); r["uncertainty_note"] = ""
        self.assertTrue(any("uncertainty_note" in e for e in self._mutate(f)))
    def test_violating_needs_clause_and_span(self):
        def f(rows): r = next(x for x in rows if x["decision"] == V); r["policy_clause"] = "none"; r["supporting_span"] = ""
        e = self._mutate(f); self.assertTrue(any("clause" in x for x in e) and any("span" in x for x in e))
    def test_mixed_rater_ids(self): self.assertTrue(any("more than one rater_id" in e for e in self._mutate(lambda r: r[0].update(rater_id="OTHER"))))


class EndToEndSynthetic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); t = cls.tmp.name; cls.t = t
        base = lambda b, r: r.choices(irr.DECISIONS, weights=[5, 4, 1])[0]
        synth(P1, f"{t}/p1r1.csv", "T1", base, 11)
        def noisy(b, r):                                   # rater 2 copies rater 1's draw for the same id most of the time
            ref = random.Random(f"{b}-ref").choices(irr.DECISIONS, weights=[5, 4, 1])[0]; return ref if r.random() < .8 else r.choice(irr.DECISIONS)
        synth(P1b, f"{t}/p1r2.csv", "T2", noisy, 12)
        synth(P2, f"{t}/p2r1.csv", "T1", base, 13); synth(P2b, f"{t}/p2r2.csv", "T2", noisy, 14)

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def test_irr_cli_and_adjudication_template(self):
        out = f"{self.t}/irr"
        rc = quiet(irr.main) if False else None
        sys.argv = ["irr", "--phase", "1", "--rater1", f"{self.t}/p1r1.csv", "--rater2", f"{self.t}/p1r2.csv", "--out-dir", out]
        self.assertEqual(quiet(irr.main), 0)
        rep = json.load(open(f"{out}/reliability_phase1.json")); self.assertEqual(rep["status"], "OK"); self.assertEqual(rep["n_items"], 88)
        self.assertEqual(rep["n_agree"] + rep["n_disagree"], 88)
        adj = list(csv.DictReader(open(f"{out}/adjudication_phase1.csv"))); self.assertEqual(len(adj), rep["n_disagree"])
        self.assertTrue(all(r["final_decision"] == "" and r["adjudicator_id"] == "" for r in adj))      # never auto-resolved
        self.assertTrue(all(r["rater1_decision"] != r["rater2_decision"] for r in adj))

    def test_invalid_input_gives_exit_2_and_no_statistics(self):
        bad = f"{self.t}/bad.csv"; rows = list(csv.DictReader(open(f"{self.t}/p1r1.csv", newline=""))); rows[0]["decision"] = "maybe"
        with open(bad, "w", newline="") as f: w = csv.DictWriter(f, fieldnames=irr.REQUIRED_COLS); w.writeheader(); w.writerows(rows)
        out = f"{self.t}/irr_bad"; sys.argv = ["irr", "--phase", "1", "--rater1", bad, "--rater2", f"{self.t}/p1r2.csv", "--out-dir", out]
        self.assertEqual(quiet(irr.main), 2); self.assertNotIn("cohen_kappa", json.load(open(f"{out}/reliability_phase1.json")))

    def test_same_rater_label_rejected(self):
        same = f"{self.t}/same.csv"; synth(P1b, same, "T1", lambda b, r: N, 5)
        out = f"{self.t}/irr_same"; sys.argv = ["irr", "--phase", "1", "--rater1", f"{self.t}/p1r1.csv", "--rater2", same, "--out-dir", out]
        self.assertEqual(quiet(irr.main), 2)

    def _run(self, args, name):
        out, rep = f"{self.t}/an_{name}", f"{self.t}/rep_{name}.md"
        sys.argv = ["a", *args, "--out-dir", out, "--report", rep]; self.assertEqual(quiet(hea.main), 0)
        return json.load(open(f"{out}/human_evaluation_analysis.json")), open(rep).read()

    def test_pending_report_has_no_human_numbers(self):
        j, rep = self._run([], "pending"); self.assertTrue(j["status"].startswith("PENDING"))
        self.assertIn("Not evaluated", rep); self.assertNotIn("kappa 0", rep); self.assertIn("not documented", rep)

    def test_phase1_only_is_partial_with_unresolved_and_phase2_questions_not_evaluable(self):
        j, rep = self._run(["--phase1-rater1", f"{self.t}/p1r1.csv", "--phase1-rater2", f"{self.t}/p1r2.csv"], "p1")
        self.assertTrue(j["status"].startswith("PARTIAL")); self.assertIn("unresolved", j["status"])
        self.assertEqual(len(j["A_human_judgement_on_residual_text"]["treatments"]["1"]), 9)
        c = j["phases"]["1"]["final_label_counts"]; self.assertEqual(sum(c.values()), 88); self.assertGreater(c["UNRESOLVED"], 0)
        self.assertEqual(j["B_paired_alignment"], "not evaluable: phase 2 missing")                       # phase 2 missing -> not evaluable
        self.assertIn("not evaluable", rep.lower())

    def test_unresolved_never_counted_as_a_label(self):
        j, _ = self._run(["--phase1-rater1", f"{self.t}/p1r1.csv", "--phase1-rater2", f"{self.t}/p1r2.csv"], "p1b")
        prim = next(t for t in j["A_human_judgement_on_residual_text"]["treatments"]["1"] if t["ambiguous"] == "exclude" and t["unresolved"] == "exclude"); c = j["phases"]["1"]["final_label_counts"]
        self.assertEqual(prim["n"], c["POLICY_VIOLATING"] + c["NOT_POLICY_VIOLATING"])
        up = next(t for t in j["A_human_judgement_on_residual_text"]["treatments"]["1"] if t["ambiguous"] == "exclude" and t["unresolved"] == "as_violating")
        self.assertEqual(up["n"], prim["n"] + c["UNRESOLVED"])

    def test_adjudication_requires_complete_valid_rows(self):
        t = self.t; out = f"{t}/irr_adj"; sys.argv = ["irr", "--phase", "1", "--rater1", f"{t}/p1r1.csv", "--rater2", f"{t}/p1r2.csv", "--out-dir", out]; quiet(irr.main)
        rows = list(csv.DictReader(open(f"{out}/adjudication_phase1.csv", newline=""))); self.assertGreater(len(rows), 3)
        rows[0].update(final_decision=V)                                                              # incomplete: no adjudicator / process / justification
        for r in rows[1:]: r.update(adjudicator_id="SYN-ADJ", adjudication_process="consensus_discussion", final_decision=N, final_justification="synthetic")
        adj = f"{t}/adj.csv"
        with open(adj, "w", newline="") as f: w = csv.DictWriter(f, fieldnames=irr.ADJ_COLS); w.writeheader(); w.writerows(rows)
        j, _ = self._run(["--phase1-rater1", f"{t}/p1r1.csv", "--phase1-rater2", f"{t}/p1r2.csv", "--phase1-adjudication", adj], "adj")
        c = j["phases"]["1"]["final_label_counts"]; self.assertEqual(c["UNRESOLVED"], 1)                # only the incomplete row stays unresolved
        self.assertTrue(j["phases"]["1"]["adjudication_errors"])

    def test_full_run_with_phase2_and_all_adjudicated(self):
        t = self.t; res = {}
        for ph in (1, 2):
            out = f"{t}/irr_f{ph}"; sys.argv = ["irr", "--phase", str(ph), "--rater1", f"{t}/p{ph}r1.csv", "--rater2", f"{t}/p{ph}r2.csv", "--out-dir", out]; quiet(irr.main)
            rows = list(csv.DictReader(open(f"{out}/adjudication_phase{ph}.csv", newline="")))
            for r in rows: r.update(adjudicator_id="SYN-ADJ", adjudication_process="third_reviewer", final_decision=A, final_justification="synthetic")
            res[ph] = f"{t}/adjf{ph}.csv"
            with open(res[ph], "w", newline="") as f: w = csv.DictWriter(f, fieldnames=irr.ADJ_COLS); w.writeheader(); w.writerows(rows)
        j, rep = self._run(["--phase1-rater1", f"{t}/p1r1.csv", "--phase1-rater2", f"{t}/p1r2.csv", "--phase1-adjudication", res[1],
                            "--phase2-rater1", f"{t}/p2r1.csv", "--phase2-rater2", f"{t}/p2r2.csv", "--phase2-adjudication", res[2]], "full")
        self.assertEqual(j["status"], "COMPLETE"); self.assertEqual(j["phases"]["1"]["final_label_counts"].get("UNRESOLVED", 0), 0)
        B = j["B_paired_alignment"]; self.assertEqual(B["primary_scenario"], hea.PRIMARY); self.assertEqual(len(B["all_scenarios"]), 20)
        self.assertEqual(set(B["primary"]), set(j["level_alignment_phase1_descriptive"]))                # same 8 systems
        for s, m in B["primary"].items():
            self.assertLessEqual(m["n_valid_pairs"], 88)
            self.assertEqual(sum(m["joint_table_human_change_x_model_change"].values()), m["n_valid_pairs"])
            self.assertEqual(m["n_valid_pairs"] + sum(m["excluded"].values()), 88)                        # every post is either valid or excluded with a reason
            self.assertIn(m["C2"]["label"], ("NOT CONCLUDABLE", "ALIGNED", "NOT ALIGNED", "MIXED / INCONCLUSIVE"))
        self.assertTrue(all(B["primary"][s]["holm_family"].startswith("F_C2") for s in hea.LLM_NAMES))
        self.assertIn("2B. Human–model paired decision alignment", rep); self.assertIn("A = P(human drops", rep)
        self.assertEqual(set(j["A_human_judgement_on_residual_text"]["category_shares"]["1"]), {"POLICY_VIOLATING", "NOT_POLICY_VIOLATING", "AMBIGUOUS", "UNRESOLVED"})

    def test_nothing_written_to_study_folder(self):
        before = sorted(os.listdir(PKG)); self._run([], "chk"); self.assertEqual(sorted(os.listdir(PKG)), before)


V_, N_, A_, U_ = hea.V, hea.N, hea.AMB, hea.UNRES

def toy_flags(rows):
    """rows: post -> (y_NEU, y_REPLAY) or ('x', ...) for an unreadable verdict, or ('abst', y)."""
    d = {}
    for p, (yn, yr) in rows.items():
        for cond, y in (("NEU", yn), ("REPLAY", yr)):
            d[(p, cond)] = (False, False, False) if y == "x" else (True, False, True) if y == "abst" else (True, bool(y), False)
    return d


class PairMetricsHandComputed(unittest.TestCase):
    """Six posts; human labels and model flags chosen so every metric can be computed by hand.
       post  h_NEU h_REPLAY  y_NEU y_REPLAY | dh  dm  dm-dh
       p1     N     V         0     1        | +1  +1   0
       p2     N     V         0     1        | +1  +1   0
       p3     V     V         0     1        |  0  +1  +1
       p4     N     N         0     0        |  0   0   0
       p5     V     V         1     1        |  0   0   0
       p6     N     V         0     0        | +1   0  -1
    """
    lab_n = {"p1": N_, "p2": N_, "p3": V_, "p4": N_, "p5": V_, "p6": N_}
    lab_r = {"p1": V_, "p2": V_, "p3": V_, "p4": N_, "p5": V_, "p6": V_}
    flags = toy_flags({"p1": (0, 1), "p2": (0, 1), "p3": (0, 1), "p4": (0, 0), "p5": (1, 1), "p6": (0, 0)})
    prim = {"name": hea.PRIMARY, "source": "final", "amb": "exclude", "unres": "exclude", "abst": "not_flag"}

    def test_counts_and_proportions(self):
        m = hea.pair_metrics(self.flags, self.lab_n, self.lab_r, self.prim, boot=200)
        self.assertEqual(m["n_valid_pairs"], 6); self.assertEqual(m["excluded"], {})
        self.assertEqual(m["model_change_counts"], {"drop(+1)": 3, "stable(0)": 3, "rise(-1)": 0})
        self.assertEqual(m["human_change_counts"], {"drop(+1)": 3, "stable(0)": 3, "rise(-1)": 0})
        self.assertEqual(m["A_P_human_drop_given_model_drop"][:3], [round(2 / 3, 4), 2, 3])             # p1, p2 of the 3 model drops
        self.assertEqual(m["R_P_model_drop_given_human_drop"][:3], [round(2 / 3, 4), 2, 3])
        self.assertEqual(m["direction_agreement_exact"][:3], [round(4 / 6, 4), 4, 6])                     # p3 and p6 disagree
        self.assertEqual((m["n_model_change_exceeds_human"], m["n_human_change_exceeds_model"]), (1, 1))
        self.assertEqual(m["D_excess_model_change"], 0.0); self.assertEqual(m["sign_test_exact_p"], 1.0)
        self.assertEqual(m["joint_table_human_change_x_model_change"]["dh=+1|dm=+1"], 2)
        self.assertEqual(m["joint_table_human_change_x_model_change"]["dh=+0|dm=+1"], 1)
        self.assertEqual(m["joint_table_human_change_x_model_change"]["dh=+1|dm=+0"], 1)

    def test_level_alignment(self):
        lv = hea.pair_metrics(self.flags, self.lab_n, self.lab_r, self.prim, boot=50)["level_alignment"]
        self.assertEqual((lv["REPLAY"]["model_flag_human_not_violating"], lv["REPLAY"]["model_noflag_human_violating"], lv["REPLAY"]["agree"]), (0, 1, 5))   # p6
        self.assertEqual((lv["NEU"]["model_flag_human_not_violating"], lv["NEU"]["model_noflag_human_violating"], lv["NEU"]["agree"]), (0, 1, 5))       # p3

    def test_small_sample_is_not_concludable(self):
        m = hea.pair_metrics(self.flags, self.lab_n, self.lab_r, self.prim, boot=50); m["holm_p"] = 1.0
        c = hea.c2_label(m); self.assertEqual(c["label"], "NOT CONCLUDABLE"); self.assertIn("valid pairs", c["reason"])

    def test_exclusions_and_treatments(self):
        ln = dict(self.lab_n, p7=A_, p8=U_, p9=N_, p10=N_); lr = dict(self.lab_r, p7=V_, p8=V_, p9=N_, p10=N_)
        fl = dict(self.flags); fl.update(toy_flags({"p7": (0, 1), "p8": (0, 1), "p9": ("x", 1), "p10": ("abst", 1)}))
        m = hea.pair_metrics(fl, ln, lr, self.prim, boot=50)
        self.assertEqual(m["n_valid_pairs"], 7); self.assertEqual(m["excluded"], {"human_ambiguous": 1, "human_unresolved": 1, "model_unreadable": 1})   # p10 abstention counts as not flagged
        m2 = hea.pair_metrics(fl, ln, lr, dict(self.prim, abst="exclude"), boot=50); self.assertEqual(m2["excluded"].get("model_abstained"), 1)
        m3 = hea.pair_metrics(fl, ln, lr, dict(self.prim, amb="V", unres="N"), boot=50); self.assertEqual(m3["n_valid_pairs"], 9); self.assertEqual(m3["excluded"], {"model_unreadable": 1})
        self.assertEqual(hea.hbin(A_, "exclude", "V"), None); self.assertEqual(hea.hbin(U_, "exclude", "V"), 1); self.assertEqual(hea.hbin(A_, "N", "V"), 0)

    def test_phase2_label_missing_is_excluded_not_imputed(self):
        lr = dict(self.lab_r); del lr["p6"]
        m = hea.pair_metrics(self.flags, self.lab_n, lr, self.prim, boot=50); self.assertEqual((m["n_valid_pairs"], m["excluded"]), (5, {"phase2_label_missing": 1}))

    def test_n_majority_not_violating_alone_does_not_give_a_label(self):
        """Human NEU labels all NOT_POLICY_VIOLATING, model drops exactly where humans do not -> no misalignment is inferred from the NEU majority."""
        posts = [f"q{i}" for i in range(60)]
        ln = {p: N_ for p in posts}; lr = {p: (V_ if i < 30 else N_) for i, p in enumerate(posts)}
        fl = toy_flags({p: (0, 1 if i < 30 else 0) for i, p in enumerate(posts)})                          # model drops on the 30 posts where humans drop too
        m = hea.pair_metrics(fl, ln, lr, self.prim, boot=200); m["holm_p"] = hea.holm({"x": m["sign_test_exact_p"]})["x"] if m["sign_test_exact_p"] else None
        c = hea.c2_label(m); self.assertEqual(c["A_component"], "aligned"); self.assertEqual(c["label"], "ALIGNED"); self.assertEqual(m["D_excess_model_change"], 0.0)

    def test_misaligned_condition_is_labelled_not_aligned(self):
        """Model drops on 40 posts where humans never change; humans drop on none -> A = 0/40 (upper bound < .5) and D > 0, significant."""
        posts = [f"r{i}" for i in range(60)]
        ln = {p: V_ for p in posts}; lr = {p: V_ for p in posts}
        fl = toy_flags({p: (0, 1 if i < 40 else 0) for i, p in enumerate(posts)})
        m = hea.pair_metrics(fl, ln, lr, self.prim, boot=200); m["holm_p"] = 1e-9
        c = hea.c2_label(m); self.assertEqual((c["A_component"], c["B_component"], c["label"]), ("not aligned", "model change exceeds human change", "NOT ALIGNED"))

    def test_scenario_grid_has_20_unique_scenarios_and_primary_first(self):
        g = hea.scenario_grid(); self.assertEqual(len(g), 20); self.assertEqual(len({x["name"] for x in g}), 20); self.assertEqual(g[0]["name"], hea.PRIMARY)

    def test_holm_over_llm_conditions_only(self):
        fl = {s: self.flags for s in hea.LLM_NAMES + ["word-LR", "char-LR"]}
        g = hea.pair_alignment(fl, {"final": (None, self.lab_n, self.lab_r)}, scenarios=[self.prim])[hea.PRIMARY]
        self.assertTrue(all(g[s]["holm_family"].startswith("F_C2") for s in hea.LLM_NAMES)); self.assertTrue(all(g[s]["holm_family"].startswith("none") for s in ("word-LR", "char-LR")))


if __name__ == "__main__":
    unittest.main()
