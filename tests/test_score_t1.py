"""Tests for the canonical T1 entrypoint src/experiment/score_t1.py (R1-3).

Verifies the alias exposes the checklist scorer unchanged and that the
anti-ceiling resolution claim in docs/t1-scoring-spec.md holds on the real
checklists.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from experiment import score_t1  # noqa: E402
from experiment.score_t1_checklist import score_t1_checklist  # noqa: E402

CHECKLIST_DIR = ROOT / "data" / "ground_truth" / "checklists"


def _scorer_input(func_id: str) -> dict:
    return {
        "lumen_schema": "scorer-input-v1",
        "func_id": func_id,
        "task": "T1",
        "condition": "C1",
        "model_id": "test-model",
        "response_ref": "results/raw/placeholder.json",
    }


class TestCanonicalAlias(unittest.TestCase):
    def test_alias_identity(self):
        self.assertIs(score_t1.score_t1, score_t1_checklist)

    def test_perfect_response_scores_one(self):
        cl = json.loads((CHECKLIST_DIR / "clamp.json").read_text())
        perfect = " ".join(p["statement"] for p in cl["properties"])
        result = score_t1.score_t1(_scorer_input("clamp"), perfect)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["score"], 1.0)

    def test_wrong_response_scores_zero(self):
        wrong = "This function sorts a list of integers and returns their sum."
        result = score_t1.score_t1(_scorer_input("clamp"), wrong)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["score"], 0.0)

    def test_empty_response_is_invalid(self):
        result = score_t1.score_t1(_scorer_input("clamp"), "")
        self.assertEqual(result["status"], "invalid_response")
        self.assertEqual(result["score"], 0.0)


class TestAntiCeilingResolution(unittest.TestCase):
    def test_each_checklist_offers_at_least_five_levels(self):
        # Anti-ceiling: P+1 attainable levels per function; require >= 5,
        # comfortably above the T2 composite's realised 3.
        for path in CHECKLIST_DIR.glob("*.json"):
            if "TEMPLATE" in path.name:
                continue
            cl = json.loads(path.read_text())
            p = len(cl["properties"])
            self.assertGreaterEqual(
                p + 1, 5, msg=f"{path.name}: only {p} properties (<4)"
            )

    def test_pooled_attainable_values_exceed_t2(self):
        from fractions import Fraction

        pool: set[Fraction] = set()
        for path in CHECKLIST_DIR.glob("*.json"):
            if "TEMPLATE" in path.name:
                continue
            cl = json.loads(path.read_text())
            p = len(cl["properties"])
            for k in range(p + 1):
                pool.add(Fraction(k, p))
        # T2 composite realised 3 distinct values; T1 must do far better.
        self.assertGreater(len(pool), 3)


if __name__ == "__main__":
    unittest.main()
