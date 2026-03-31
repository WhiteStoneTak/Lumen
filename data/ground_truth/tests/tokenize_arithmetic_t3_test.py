"""T3 post-transform test suite for tokenize_arithmetic.

Transform spec (tokenize_arithmetic.TR01): Change operator token type from
'OP' for all operators to 'ADDOP' for + and -, 'MULOP' for * and /. All other
token types (NUM, LPAREN, RPAREN) are unchanged.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_ta_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.tokenize_arithmetic


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "tokenize_arithmetic.py"
)
_SOURCE = _DEFAULT_SOURCE
tokenize_arithmetic = _load_func(_SOURCE)


class TokenizeArithmeticT3AddopMulopTests(unittest.TestCase):
    """Transformed function must use ADDOP and MULOP instead of OP."""

    def test_plus_is_addop(self) -> None:
        result = tokenize_arithmetic("3+4")
        self.assertIn(("ADDOP", "+"), result)

    def test_minus_is_addop(self) -> None:
        result = tokenize_arithmetic("5-2")
        self.assertIn(("ADDOP", "-"), result)

    def test_star_is_mulop(self) -> None:
        result = tokenize_arithmetic("2*3")
        self.assertIn(("MULOP", "*"), result)

    def test_slash_is_mulop(self) -> None:
        result = tokenize_arithmetic("6/2")
        self.assertIn(("MULOP", "/"), result)

    def test_no_op_tokens_in_result(self) -> None:
        result = tokenize_arithmetic("1+2*3-4/5")
        op_tokens = [t for t in result if t[0] == "OP"]
        self.assertEqual(op_tokens, [])

    def test_complex_expr_full(self) -> None:
        result = tokenize_arithmetic("(1+2)*3")
        self.assertEqual(result, [
            ("LPAREN", "("),
            ("NUM", "1"),
            ("ADDOP", "+"),
            ("NUM", "2"),
            ("RPAREN", ")"),
            ("MULOP", "*"),
            ("NUM", "3"),
        ])

    def test_lparen_unchanged(self) -> None:
        result = tokenize_arithmetic("(")
        self.assertEqual(result, [("LPAREN", "(")])

    def test_rparen_unchanged(self) -> None:
        result = tokenize_arithmetic(")")
        self.assertEqual(result, [("RPAREN", ")")])

    def test_num_unchanged(self) -> None:
        result = tokenize_arithmetic("42")
        self.assertEqual(result, [("NUM", "42")])

    def test_addop_plus_value_preserved(self) -> None:
        result = tokenize_arithmetic("3 + 42")
        self.assertEqual(result, [("NUM", "3"), ("ADDOP", "+"), ("NUM", "42")])


class TokenizeArithmeticT3PreservationTests(unittest.TestCase):
    """Verify non-operator tokens are preserved unchanged."""

    def test_minus_not_op(self) -> None:
        result = tokenize_arithmetic("5-2")
        types = [t[0] for t in result]
        self.assertNotIn("OP", types)
        self.assertIn("ADDOP", types)

    def test_division_not_op(self) -> None:
        result = tokenize_arithmetic("10/2")
        types = [t[0] for t in result]
        self.assertNotIn("OP", types)
        self.assertIn("MULOP", types)

    def test_all_four_operators(self) -> None:
        result = tokenize_arithmetic("1+2-3*4/5")
        types = [t[0] for t in result]
        self.assertNotIn("OP", types)
        self.assertIn("ADDOP", types)
        self.assertIn("MULOP", types)


if __name__ == "__main__":
    unittest.main()
