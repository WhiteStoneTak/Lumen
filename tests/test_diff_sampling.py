"""Unit tests for src/experiment/diff_sampling.py (W-04).

Covers determinism, type support detection, not-applicable (callable) handling,
edge-case presence, and row shape.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from experiment import diff_sampling  # noqa: E402


class TestIsSupported(unittest.TestCase):
    def test_scalar_and_list_types_supported(self):
        self.assertTrue(diff_sampling.is_supported(["builtins.int", "builtins.float"]))
        self.assertTrue(diff_sampling.is_supported(["builtins.str", "builtins.bool"]))
        self.assertTrue(diff_sampling.is_supported(["builtins.list[builtins.int]"]))
        self.assertTrue(diff_sampling.is_supported(["builtins.list[Any]"]))
        self.assertTrue(diff_sampling.is_supported(
            ["builtins.list[builtins.list[builtins.int]]"]))

    def test_callable_type_unsupported(self):
        # A callable parameter (e.g. top_k_by's key=) has no concrete generator.
        self.assertFalse(diff_sampling.is_supported(["def (*Any, **Any) -> Any"]))


class TestSampleInputs(unittest.TestCase):
    def test_determinism(self):
        types = ["builtins.int", "builtins.list[builtins.int]"]
        a = diff_sampling.sample_inputs(types, seed=123)
        b = diff_sampling.sample_inputs(types, seed=123)
        self.assertEqual(a, b)

    def test_seed_changes_random_block(self):
        types = ["builtins.int"]
        a = diff_sampling.sample_inputs(types, seed=1)
        b = diff_sampling.sample_inputs(types, seed=2)
        self.assertNotEqual(a, b)

    def test_none_for_unsupported(self):
        self.assertIsNone(diff_sampling.sample_inputs(["def (*Any, **Any) -> Any"]))

    def test_row_shape_matches_param_count(self):
        types = ["builtins.int", "builtins.str", "builtins.float"]
        rows = diff_sampling.sample_inputs(types, n_random=5)
        self.assertIsNotNone(rows)
        for row in rows:
            self.assertEqual(len(row), 3)

    def test_zero_arg_function(self):
        self.assertEqual(diff_sampling.sample_inputs([]), [[]])

    def test_edge_cases_present(self):
        rows = diff_sampling.sample_inputs(["builtins.int"], n_random=0)
        flat = [r[0] for r in rows]
        self.assertIn(0, flat)
        self.assertIn(1, flat)
        self.assertIn(-1, flat)

    def test_list_elements_have_right_type(self):
        rows = diff_sampling.sample_inputs(["builtins.list[builtins.int]"], seed=7)
        self.assertIsNotNone(rows)
        for row in rows:
            for elem in row[0]:
                self.assertIsInstance(elem, int)


if __name__ == "__main__":
    unittest.main()
