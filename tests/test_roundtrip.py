"""Tests for src/experiment/roundtrip.py (R4-1 / W-03).

Covers the docstring->contract parser, the recovery metrics on two hand-built
fixtures (one perfect round trip, one with known loss), and the end-to-end
single-function run.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from experiment.roundtrip import (  # noqa: E402
    parse_contracts_from_docstring,
    recovery_metrics,
    run_func,
)


# A minimal C4 IR fixture (hand-built).
def _ir_fixture():
    ast = {
        "_type": "Module",
        "body": [{
            "_type": "FunctionDef",
            "name": "f",
            "args": {"_type": "arguments", "args": [
                {"_type": "arg", "arg": "x", "annotation": {"_type": "Name", "id": "int"}},
            ]},
            "returns": {"_type": "Name", "id": "int"},
            "body": [{"_type": "Return", "value": {"_type": "Name", "id": "x"}}],
        }],
    }
    return {
        "lumen_schema": "ir-v1",
        "func_id": "f",
        "type_info": {
            "params": [{"name": "x", "mypy_type": "builtins.int"}],
            "return_type": "builtins.int",
        },
        "contracts": {
            "preconditions": ["x >= 0"],
            "postconditions": ["the return value equals x", "the return value is >= 0"],
            "invariants": [],
        },
        "ast": ast,
    }


class TestDocstringContractParser(unittest.TestCase):
    SRC = '''
def f(x: int) -> int:
    """
    Preconditions:
    - x >= 0

    Postconditions:
    - the return value equals x

    Invariants:
    - None.
    """
    return x
'''

    def test_sections_parsed(self):
        c = parse_contracts_from_docstring(self.SRC)
        self.assertEqual(c["preconditions"], ["x >= 0"])
        self.assertEqual(c["postconditions"], ["the return value equals x"])

    def test_none_bullet_is_empty(self):
        c = parse_contracts_from_docstring(self.SRC)
        self.assertEqual(c["invariants"], [])

    def test_no_docstring_returns_empty(self):
        c = parse_contracts_from_docstring("def g(x):\n    return x\n")
        self.assertEqual(c, {"preconditions": [], "postconditions": [], "invariants": []})


class TestRecoveryMetricsPerfect(unittest.TestCase):
    """Perfect round trip: recovered C4' identical to C4."""

    def test_all_retention_one_and_hash_match(self):
        ir = _ir_fixture()
        recovered = {
            "ast": ir["ast"],  # identical -> hash match
            "contracts": ir["contracts"],
            "type_info": {"params": {"x": "int"}, "return_type": "int"},
        }
        m = recovery_metrics(ir, recovered)
        self.assertEqual(m["node_kind_retention"], 1.0)
        self.assertEqual(m["type_annotation_retention"], 1.0)
        self.assertEqual(m["parent_child_retention"], 1.0)
        self.assertEqual(m["contract_clause_retention"]["preconditions"], 1.0)
        self.assertEqual(m["contract_clause_retention"]["postconditions"], 1.0)
        self.assertEqual(m["cross_reference_retention"], 1.0)
        self.assertTrue(m["canonical_hash_agreement"])


class TestRecoveryMetricsLossy(unittest.TestCase):
    """Known loss: a dropped postcondition, a dropped node, a lost type."""

    def test_known_losses_detected(self):
        ir = _ir_fixture()
        lossy_ast = {
            "_type": "Module",
            "body": [{
                "_type": "FunctionDef", "name": "f",
                "args": {"_type": "arguments", "args": [
                    {"_type": "arg", "arg": "x"},  # annotation dropped
                ]},
                "returns": None,  # return type lost
                "body": [],       # Return node dropped
            }],
        }
        recovered = {
            "ast": lossy_ast,
            "contracts": {
                "preconditions": ["x >= 0"],
                "postconditions": ["the return value equals x"],  # 1 of 2 kept
                "invariants": [],
            },
            "type_info": {"params": {}, "return_type": None},  # types lost
        }
        m = recovery_metrics(ir, recovered)
        self.assertLess(m["node_kind_retention"], 1.0)        # Return/Name dropped
        self.assertLess(m["type_annotation_retention"], 1.0)  # x:int + return lost
        self.assertEqual(m["contract_clause_retention"]["postconditions"], 0.5)
        self.assertFalse(m["canonical_hash_agreement"])


class TestEndToEnd(unittest.TestCase):
    def test_clamp_roundtrip_recovers_content(self):
        result = run_func("clamp")
        m = result["metrics"]
        # Content fully recovered; AST not byte-identical (C1+ adds a docstring).
        self.assertEqual(m["node_kind_retention"], 1.0)
        self.assertEqual(m["type_annotation_retention"], 1.0)
        self.assertEqual(m["contract_clause_retention"]["postconditions"], 1.0)
        self.assertFalse(m["canonical_hash_agreement"])


if __name__ == "__main__":
    unittest.main()
