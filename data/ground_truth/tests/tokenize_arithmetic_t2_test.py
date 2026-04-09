"""T2 test suite for tokenize_arithmetic.

Correct behaviour: tokenizes an arithmetic expression into (type, value)
pairs. NUM tokens cover both integer and decimal literals. OP tokens cover
+, -, *, /. LPAREN/RPAREN cover parentheses. Whitespace is ignored.

Introduced bug (missing_boundary_check): the digit-scan inner loop uses
only `expr[j].isdigit()` instead of `expr[j].isdigit() or expr[j] == '.'`.
Decimal numbers are split at the decimal point: e.g. '3.14' produces
[("NUM","3"), ("NUM","14")] instead of [("NUM","3.14")].
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_ta_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.tokenize_arithmetic


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw"
    / "tokenize_arithmetic.py"
)
_SOURCE = _DEFAULT_SOURCE
tokenize_arithmetic = _load_func(_SOURCE)


class TokenizeArithmeticCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_simple_addition(self):
        result = tokenize_arithmetic("3 + 42")
        self.assertEqual(result, [("NUM", "3"), ("OP", "+"), ("NUM", "42")])

    def test_parenthesized_expression(self):
        result = tokenize_arithmetic("(1+2)*3")
        self.assertEqual(result, [
            ("LPAREN", "("), ("NUM", "1"), ("OP", "+"), ("NUM", "2"),
            ("RPAREN", ")"), ("OP", "*"), ("NUM", "3"),
        ])

    def test_division(self):
        result = tokenize_arithmetic("10/2")
        self.assertEqual(result, [("NUM", "10"), ("OP", "/"), ("NUM", "2")])

    def test_whitespace_ignored(self):
        result = tokenize_arithmetic("  1  +  2  ")
        self.assertEqual(result, [("NUM", "1"), ("OP", "+"), ("NUM", "2")])

    def test_integer_only(self):
        result = tokenize_arithmetic("123")
        self.assertEqual(result, [("NUM", "123")])


class TokenizeArithmeticBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the missing_boundary_check bug.

    The bug truncates decimal literals at the decimal point because the
    inner scan loop does not continue through '.'.
    """

    def test_decimal_literal_not_split(self):
        # '3.14' must produce a single NUM token, not two
        result = tokenize_arithmetic("3.14")
        self.assertEqual(
            result, [("NUM", "3.14")],
            msg=f"Decimal '3.14' must be one NUM token; "
                f"buggy version splits it; got {result}",
        )

    def test_decimal_in_expression(self):
        # '1.5 + 2.5' — each decimal must be a single NUM
        result = tokenize_arithmetic("1.5 + 2.5")
        self.assertEqual(
            result, [("NUM", "1.5"), ("OP", "+"), ("NUM", "2.5")],
            msg=f"Decimal literals in expression must not be split; got {result}",
        )

    def test_decimal_with_leading_zero(self):
        result = tokenize_arithmetic("0.5 * 4")
        self.assertEqual(
            result, [("NUM", "0.5"), ("OP", "*"), ("NUM", "4")],
            msg=f"'0.5' must be one NUM token; got {result}",
        )

    def test_integer_token_unaffected(self):
        # Regression: integers must still tokenize correctly
        result = tokenize_arithmetic("42 - 7")
        self.assertEqual(result, [("NUM", "42"), ("OP", "-"), ("NUM", "7")])


if __name__ == "__main__":
    unittest.main()
