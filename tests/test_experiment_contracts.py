from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from experiment.contracts import (  # noqa: E402
    ContractValidationError,
    get_manifest_item,
    load_dataset_manifest,
    load_ground_truth_for_scorer_input,
    validate_scorer_result,
    validate_t2_bug_annotation,
)


class ExperimentContractTests(unittest.TestCase):
    def test_manifest_validates_and_contains_pilot_funcs(self) -> None:
        manifest = load_dataset_manifest(check_paths=True)
        func_ids = {item["func_id"] for item in manifest["items"]}
        self.assertEqual(func_ids, {"clamp", "count_vowels", "is_sorted"})

    def test_manifest_task_availability_is_consistent(self) -> None:
        manifest = load_dataset_manifest(check_paths=True)
        for func_id in ("clamp", "count_vowels", "is_sorted"):
            item = get_manifest_item(manifest, func_id)
            self.assertTrue(item["tasks"]["T1"]["available"])
            self.assertFalse(item["tasks"]["T2"]["available"])
            self.assertFalse(item["tasks"]["T3"]["available"])

    def test_t1_ground_truth_loads_from_scorer_input_contract(self) -> None:
        scorer_input = {
            "lumen_schema": "scorer-input-v1",
            "func_id": "clamp",
            "task": "T1",
            "condition": "C4",
            "model_id": "demo-model",
            "response_ref": "results/raw/placeholder.json",
        }
        payload = load_ground_truth_for_scorer_input(scorer_input, check_paths=False)
        self.assertEqual(payload["lumen_schema"], "t1-checklist-v1")
        self.assertEqual(payload["func_id"], "clamp")

    def test_malformed_manifest_item_fails_fast(self) -> None:
        manifest = load_dataset_manifest(check_paths=True)
        bad_item = copy.deepcopy(manifest["items"][0])
        bad_item["tasks"]["T1"]["ground_truth_ref"] = None

        bad_manifest = {
            "lumen_schema": manifest["lumen_schema"],
            "protocol_scope": manifest["protocol_scope"],
            "items": [bad_item],
        }

        from experiment.contracts import validate_dataset_manifest

        with self.assertRaises(ContractValidationError):
            validate_dataset_manifest(bad_manifest, check_paths=False)

    def test_malformed_t2_category_fails(self) -> None:
        bad_t2 = {
            "lumen_schema": "t2-bug-v1",
            "func_id": "clamp",
            "source_hash": "x",
            "bug_id": "clamp.B01",
            "bug_category": "invalid_label",
            "bug_description": "broken",
            "location": {
                "path": "data/functions/raw/clamp.py",
                "start_line": 1,
                "end_line": 1,
            },
            "reference_fix": {
                "start_line": 1,
                "end_line": 1,
                "replacement": "return value",
            },
            "test_suite_ref": "data/ground_truth/tests/clamp_t2_test.py",
        }

        with self.assertRaises(ContractValidationError):
            validate_t2_bug_annotation(bad_t2, check_paths=False)

    def test_t3_parse_failure_requires_zero_score(self) -> None:
        bad_result = {
            "lumen_schema": "scorer-result-v1",
            "func_id": "clamp",
            "task": "T3",
            "condition": "C1",
            "model_id": "demo-model",
            "response_ref": "results/raw/placeholder.json",
            "ground_truth_ref": "data/ground_truth/tests/clamp_t3_test.py",
            "score": 0.2,
            "status": "parse_failure",
            "subscores": None,
            "failure_reason": {"code": "parse_error", "message": "syntax error"},
            "evidence": {},
        }

        with self.assertRaises(ContractValidationError):
            validate_scorer_result(bad_result)


if __name__ == "__main__":
    unittest.main()
