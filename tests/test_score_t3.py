"""Tests for the narrow T3 scorer (src/experiment/score_t3.py).

Coverage:
1.  Correct clamp transform (ValueError for lo > hi) scores 1.0
2.  Correct count_vowels transform (y/Y as vowels) scores 1.0
3.  Correct is_sorted transform (strict ascending) scores 1.0
4.  Syntax error response → score=0.0, status="parse_failure"
5.  Wrong function name → score=0.0, status="parse_failure"
6.  No code candidate → score=0.0, status="parse_failure"
7.  Partially correct transform → score ∈ (0.0, 1.0)
8.  Prose + code-block response (extraction from mixed response)
9.  Multiple code blocks: prefers one containing target function
10. Emitted result validates under scorer-result-v1
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from experiment.contracts import (  # noqa: E402
    ContractValidationError,
    validate_scorer_result,
)
from experiment.score_t3 import (  # noqa: E402
    extract_t3_code_candidate,
    parse_t3_candidate,
    run_t3_tests,
    score_t3,
    load_t3_scoring_context,
)


# ---------------------------------------------------------------------------
# Shared scorer-input payloads
# ---------------------------------------------------------------------------

def _scorer_input(func_id: str) -> dict:
    return {
        "lumen_schema": "scorer-input-v1",
        "func_id": func_id,
        "task": "T3",
        "condition": "C1",
        "model_id": "test-model",
        "response_ref": "results/raw/placeholder.json",
    }


# ---------------------------------------------------------------------------
# Correct transformed implementations
# ---------------------------------------------------------------------------

CLAMP_CORRECT_T3 = '''\
def clamp(value: float, lo: float, hi: float) -> float:
    """Return value clamped to [lo, hi], raising ValueError if lo > hi."""
    if lo > hi:
        raise ValueError(f"lo must be <= hi, got lo={lo}, hi={hi}")
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value
'''

COUNT_VOWELS_CORRECT_T3 = '''\
def count_vowels(s: str) -> int:
    """Count vowels including y/Y."""
    count = 0
    for ch in s.lower():
        if ch in "aeiouy":
            count += 1
    return count
'''

IS_SORTED_CORRECT_T3 = '''\
def is_sorted(items: list) -> bool:
    """Return True if items is in strictly ascending order."""
    for i in range(len(items) - 1):
        if items[i] >= items[i + 1]:
            return False
    return True
'''

# Partial: original count_vowels (no 'y' support) — passes original-behaviour
# tests but fails all y/Y tests.  Exactly 5 of 11 tests pass.
COUNT_VOWELS_PARTIAL_T3 = '''\
def count_vowels(s: str) -> int:
    """Count vowels (original, without y/Y support)."""
    count = 0
    for ch in s.lower():
        if ch in "aeiou":
            count += 1
    return count
'''


# ---------------------------------------------------------------------------
# Helper: wrap code in fenced block
# ---------------------------------------------------------------------------

def _wrap_python(code: str) -> str:
    return f"```python\n{code}\n```"


def _wrap_generic(code: str) -> str:
    return f"```\n{code}\n```"


# ---------------------------------------------------------------------------
# Unit tests: extract_t3_code_candidate
# ---------------------------------------------------------------------------

class TestExtractT3CodeCandidate(unittest.TestCase):
    def test_extracts_python_fenced_block(self) -> None:
        response = _wrap_python(CLAMP_CORRECT_T3)
        result = extract_t3_code_candidate(response, "clamp")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("def clamp(", result)

    def test_extracts_generic_fenced_block(self) -> None:
        response = _wrap_generic(CLAMP_CORRECT_T3)
        result = extract_t3_code_candidate(response, "clamp")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("def clamp(", result)

    def test_prefers_block_with_target_function(self) -> None:
        # Two blocks: first has wrong function, second has target
        first_block = "```python\ndef other_func():\n    pass\n```"
        second_block = _wrap_python(CLAMP_CORRECT_T3)
        response = f"Some prose.\n\n{first_block}\n\nThen:\n\n{second_block}"
        result = extract_t3_code_candidate(response, "clamp")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("def clamp(", result)

    def test_falls_back_to_prose_def(self) -> None:
        # No fenced blocks, but has a bare def
        response = (
            "Here is the answer:\n\n"
            "def clamp(value, lo, hi):\n"
            "    return max(lo, min(hi, value))\n"
        )
        result = extract_t3_code_candidate(response, "clamp")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("def clamp(", result)

    def test_returns_none_when_no_candidate(self) -> None:
        response = "I don't know what to do here. No code."
        result = extract_t3_code_candidate(response, "clamp")
        self.assertIsNone(result)

    def test_mixed_prose_and_code_block(self) -> None:
        response = (
            "Here is my analysis of the transform.\n\n"
            "The function should raise ValueError when lo > hi.\n\n"
            + _wrap_python(CLAMP_CORRECT_T3)
            + "\n\nThat's my final answer."
        )
        result = extract_t3_code_candidate(response, "clamp")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("def clamp(", result)
        self.assertIn("ValueError", result)


# ---------------------------------------------------------------------------
# Unit tests: parse_t3_candidate
# ---------------------------------------------------------------------------

class TestParseT3Candidate(unittest.TestCase):
    def test_valid_clamp_code(self) -> None:
        valid, err = parse_t3_candidate(CLAMP_CORRECT_T3, "clamp")
        self.assertTrue(valid)
        self.assertEqual(err, "")

    def test_syntax_error_returns_false(self) -> None:
        code = "def clamp(value lo hi):\n    return value\n"
        valid, err = parse_t3_candidate(code, "clamp")
        self.assertFalse(valid)
        self.assertIn("SyntaxError", err)

    def test_wrong_function_name_returns_false(self) -> None:
        code = "def wrong_name(x):\n    return x\n"
        valid, err = parse_t3_candidate(code, "clamp")
        self.assertFalse(valid)
        self.assertIn("not found; found:", err)

    def test_no_function_def_returns_false(self) -> None:
        code = "x = 1 + 2\n"
        valid, err = parse_t3_candidate(code, "clamp")
        self.assertFalse(valid)
        self.assertIn("No function definition", err)

    def test_valid_count_vowels_code(self) -> None:
        valid, err = parse_t3_candidate(COUNT_VOWELS_CORRECT_T3, "count_vowels")
        self.assertTrue(valid)
        self.assertEqual(err, "")

    def test_valid_is_sorted_code(self) -> None:
        valid, err = parse_t3_candidate(IS_SORTED_CORRECT_T3, "is_sorted")
        self.assertTrue(valid)
        self.assertEqual(err, "")


# ---------------------------------------------------------------------------
# Integration tests: score_t3 end-to-end
# ---------------------------------------------------------------------------

class TestScoreT3Composite(unittest.TestCase):
    def _run(self, func_id: str, response: str) -> dict:
        return score_t3(_scorer_input(func_id), response)

    # -- correct implementations score 1.0 --

    def test_clamp_correct_transform_scores_one(self) -> None:
        result = self._run("clamp", _wrap_python(CLAMP_CORRECT_T3))
        self.assertEqual(result["score"], 1.0)
        self.assertEqual(result["status"], "ok")

    def test_count_vowels_correct_transform_scores_one(self) -> None:
        result = self._run("count_vowels", _wrap_python(COUNT_VOWELS_CORRECT_T3))
        self.assertEqual(result["score"], 1.0)
        self.assertEqual(result["status"], "ok")

    def test_is_sorted_correct_transform_scores_one(self) -> None:
        result = self._run("is_sorted", _wrap_python(IS_SORTED_CORRECT_T3))
        self.assertEqual(result["score"], 1.0)
        self.assertEqual(result["status"], "ok")

    # -- failure modes --

    def test_syntax_error_gives_parse_failure(self) -> None:
        bad_code = "def count_vowels(s str):\n    return 0\n"
        result = self._run("count_vowels", _wrap_python(bad_code))
        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["status"], "parse_failure")
        self.assertIsNotNone(result["failure_reason"])
        self.assertEqual(result["failure_reason"]["code"], "syntax_error")

    def test_wrong_function_name_gives_parse_failure(self) -> None:
        bad_code = "def wrong_name(s: str) -> int:\n    return 0\n"
        result = self._run("count_vowels", _wrap_python(bad_code))
        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["status"], "parse_failure")
        self.assertIsNotNone(result["failure_reason"])
        self.assertEqual(result["failure_reason"]["code"], "wrong_function_name")

    def test_no_code_candidate_gives_parse_failure(self) -> None:
        result = self._run("clamp", "I have no idea how to transform this function.")
        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["status"], "parse_failure")
        self.assertIsNotNone(result["failure_reason"])
        self.assertEqual(result["failure_reason"]["code"], "no_code_candidate")

    # -- partial pass rate --

    def test_partial_transform_gives_fractional_score(self) -> None:
        # COUNT_VOWELS_PARTIAL_T3 passes original-behaviour tests but fails y/Y tests
        result = self._run("count_vowels", _wrap_python(COUNT_VOWELS_PARTIAL_T3))
        self.assertEqual(result["status"], "ok")
        self.assertGreater(result["score"], 0.0)
        self.assertLess(result["score"], 1.0)

    # -- extraction from mixed prose+code --

    def test_prose_and_code_block_extraction(self) -> None:
        response = (
            "To implement the transform for clamp, I'll add a precondition check.\n\n"
            + _wrap_python(CLAMP_CORRECT_T3)
            + "\n\nThis ensures ValueError is raised for invalid ranges."
        )
        result = self._run("clamp", response)
        self.assertEqual(result["score"], 1.0)
        self.assertEqual(result["status"], "ok")

    # -- multiple code blocks: prefers one with target function --

    def test_multiple_blocks_prefers_target_function(self) -> None:
        # First block has wrong func, second has correct clamp
        response = (
            "Here's an example of a different function:\n\n"
            "```python\ndef other_func(x):\n    return x\n```\n\n"
            "And here's the actual clamp transform:\n\n"
            + _wrap_python(CLAMP_CORRECT_T3)
        )
        result = self._run("clamp", response)
        self.assertEqual(result["score"], 1.0)

    # -- generic fenced block (no language tag) --

    def test_generic_fenced_block_extracted(self) -> None:
        result = self._run("count_vowels", _wrap_generic(COUNT_VOWELS_CORRECT_T3))
        self.assertEqual(result["score"], 1.0)
        self.assertEqual(result["status"], "ok")

    # -- contract validation --

    def test_result_validates_under_scorer_result_v1(self) -> None:
        cases = [
            ("clamp", _wrap_python(CLAMP_CORRECT_T3)),
            ("count_vowels", _wrap_python(COUNT_VOWELS_CORRECT_T3)),
            ("is_sorted", _wrap_python(IS_SORTED_CORRECT_T3)),
            ("clamp", "No code here."),
            ("count_vowels", _wrap_python(COUNT_VOWELS_PARTIAL_T3)),
        ]
        for func_id, response in cases:
            with self.subTest(func_id=func_id):
                result = self._run(func_id, response)
                validated = validate_scorer_result(result)
                self.assertEqual(validated["lumen_schema"], "scorer-result-v1")
                self.assertEqual(validated["task"], "T3")

    def test_score_in_unit_interval(self) -> None:
        cases = [
            ("clamp", _wrap_python(CLAMP_CORRECT_T3)),
            ("count_vowels", _wrap_python(COUNT_VOWELS_PARTIAL_T3)),
            ("clamp", "nothing"),
        ]
        for func_id, response in cases:
            with self.subTest(func_id=func_id):
                result = self._run(func_id, response)
                self.assertGreaterEqual(result["score"], 0.0)
                self.assertLessEqual(result["score"], 1.0)

    def test_ok_status_has_no_failure_reason(self) -> None:
        result = self._run("clamp", _wrap_python(CLAMP_CORRECT_T3))
        self.assertEqual(result["status"], "ok")
        self.assertIsNone(result["failure_reason"])

    def test_parse_failure_has_failure_reason(self) -> None:
        result = self._run("clamp", "no code here")
        self.assertNotEqual(result["status"], "ok")
        self.assertIsNotNone(result["failure_reason"])

    def test_evidence_contains_passed_total_on_ok(self) -> None:
        result = self._run("clamp", _wrap_python(CLAMP_CORRECT_T3))
        self.assertIn("passed", result["evidence"])
        self.assertIn("total", result["evidence"])
        self.assertGreater(result["evidence"]["total"], 0)


if __name__ == "__main__":
    unittest.main()
