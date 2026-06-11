"""Sandbox + timeout tests for the T3 scorer (R1-4 / WOV-238).

Covers the four cases the issue mandates against the *sandboxed* runner:
all-pass, partial-pass, syntax-error output, and infinite-loop output
(timeout). The non-timeout cases also confirm the subprocess path returns the
same scores as the in-process path.
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from experiment.score_t3 import (  # noqa: E402
    FR_EXECUTION_TIMEOUT,
    score_t3,
    score_t3_sandboxed,
)


def _scorer_input(func_id: str) -> dict:
    return {
        "lumen_schema": "scorer-input-v1",
        "func_id": func_id,
        "task": "T3",
        "condition": "C1",
        "model_id": "test-model",
        "response_ref": "results/raw/placeholder.json",
    }


# clamp T3 transform: raise ValueError when lo > hi (correct = all pass).
CLAMP_CORRECT = '''```python
def clamp(value: float, lo: float, hi: float) -> float:
    if lo > hi:
        raise ValueError("lo must be <= hi")
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value
```'''

# count_vowels T3 transform: must add y/Y. Original (no y) passes only the
# unchanged-behaviour tests -> strictly partial.
COUNT_VOWELS_PARTIAL = '''```python
def count_vowels(s: str) -> int:
    count = 0
    for ch in s.lower():
        if ch in "aeiou":
            count += 1
    return count
```'''

CLAMP_SYNTAX_ERROR = '''```python
def clamp(value, lo, hi)
    return value
```'''

# Non-terminating candidate: importing the module spins forever.
CLAMP_INFINITE_LOOP = '''```python
while True:
    pass

def clamp(value, lo, hi):
    return value
```'''


class TestSandboxedT3(unittest.TestCase):
    def test_all_pass_scores_one(self):
        r = score_t3_sandboxed(_scorer_input("clamp"), CLAMP_CORRECT)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["score"], 1.0)

    def test_partial_pass_is_fractional(self):
        r = score_t3_sandboxed(_scorer_input("count_vowels"), COUNT_VOWELS_PARTIAL)
        self.assertEqual(r["status"], "ok")
        self.assertGreater(r["score"], 0.0)
        self.assertLess(r["score"], 1.0)

    def test_syntax_error_is_parse_failure(self):
        r = score_t3_sandboxed(_scorer_input("clamp"), CLAMP_SYNTAX_ERROR)
        self.assertEqual(r["status"], "parse_failure")
        self.assertEqual(r["score"], 0.0)

    def test_infinite_loop_times_out(self):
        start = time.monotonic()
        r = score_t3_sandboxed(
            _scorer_input("clamp"), CLAMP_INFINITE_LOOP, timeout_s=3.0
        )
        elapsed = time.monotonic() - start
        self.assertEqual(r["status"], "execution_failure")
        self.assertEqual(r["score"], 0.0)
        self.assertEqual(r["failure_reason"]["code"], FR_EXECUTION_TIMEOUT)
        # The timeout fences the hang: returns shortly after the 3s budget.
        self.assertLess(elapsed, 15.0)

    def test_sandbox_matches_inprocess_on_correct(self):
        sb = score_t3_sandboxed(_scorer_input("clamp"), CLAMP_CORRECT)
        ip = score_t3(_scorer_input("clamp"), CLAMP_CORRECT)
        self.assertEqual(sb["score"], ip["score"])
        self.assertEqual(sb["evidence"]["total"], ip["evidence"]["total"])


if __name__ == "__main__":
    unittest.main()
