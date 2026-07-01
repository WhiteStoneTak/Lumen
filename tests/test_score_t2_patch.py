"""Unit tests for src/experiment/score_t2_patch.py (W-04).

Covers structural equivalence, behavioral (differential) agreement including the
not-applicable path, and continuous patch-pass fraction against a real T2 bug.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from experiment import score_t2_patch as m  # noqa: E402


CLAMP_REF = (
    "def clamp(value, lo, hi):\n"
    "    if value < lo:\n        return lo\n"
    "    if value > hi:\n        return hi\n"
    "    return value\n"
)


class TestStructuralEquivalence(unittest.TestCase):
    def test_identical_is_equivalent(self):
        r = m.structural_equivalence(CLAMP_REF, CLAMP_REF, "clamp")
        self.assertEqual(r["status"], "ok")
        self.assertTrue(r["ast_equivalent"])
        self.assertEqual(r["similarity"], 1.0)

    def test_docstring_difference_ignored(self):
        with_doc = (
            'def clamp(value, lo, hi):\n    """doc."""\n'
            "    if value < lo:\n        return lo\n"
            "    if value > hi:\n        return hi\n    return value\n"
        )
        r = m.structural_equivalence(with_doc, CLAMP_REF, "clamp")
        self.assertTrue(r["ast_equivalent"])

    def test_operator_difference_not_equivalent(self):
        buggy = CLAMP_REF.replace("value > hi", "value < hi")
        r = m.structural_equivalence(buggy, CLAMP_REF, "clamp")
        self.assertFalse(r["ast_equivalent"])
        self.assertLess(r["similarity"], 1.0)

    def test_unparseable_is_not_applicable(self):
        r = m.structural_equivalence("def clamp(:\n  bad", CLAMP_REF, "clamp")
        self.assertEqual(r["status"], "not_applicable")


class TestBehavioralAgreement(unittest.TestCase):
    TYPES = ["builtins.float", "builtins.float", "builtins.float"]

    def test_identical_full_agreement(self):
        r = m.behavioral_agreement(CLAMP_REF, CLAMP_REF, "clamp", self.TYPES)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["agreement"], 1.0)

    def test_wrong_candidate_below_one(self):
        buggy = CLAMP_REF.replace("value > hi", "value < hi")
        r = m.behavioral_agreement(buggy, CLAMP_REF, "clamp", self.TYPES)
        self.assertEqual(r["status"], "ok")
        self.assertLess(r["agreement"], 1.0)

    def test_unsupported_types_not_applicable(self):
        r = m.behavioral_agreement(CLAMP_REF, CLAMP_REF, "clamp",
                                   ["def (*Any, **Any) -> Any"])
        self.assertEqual(r["status"], "not_applicable")


class TestPatchPassFraction(unittest.TestCase):
    def test_correct_fix_full_pass(self):
        truth = m._load_bug_truth("clamp")
        buggy = (m.REPO_ROOT / truth["location"]["path"]).read_text(encoding="utf-8")
        # The reference replacement is the correct fix line.
        fix_line = truth["reference_fix"]["replacement"]
        r = m.patch_pass_fraction(buggy, truth, fix_line)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["fraction"], 1.0)

    def test_no_change_keeps_bug_below_one(self):
        truth = m._load_bug_truth("clamp")
        buggy = (m.REPO_ROOT / truth["location"]["path"]).read_text(encoding="utf-8")
        # "Fix" that re-introduces the buggy line -> tests should still fail.
        bad = "    if value < hi:"
        r = m.patch_pass_fraction(buggy, truth, bad)
        self.assertEqual(r["status"], "ok")
        self.assertLess(r["fraction"], 1.0)


if __name__ == "__main__":
    unittest.main()
