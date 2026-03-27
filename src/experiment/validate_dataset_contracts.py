"""CLI validator for dataset/ground-truth/scorer contracts."""

from __future__ import annotations

import argparse
import json
import sys

from experiment.contracts import (
    ContractValidationError,
    DEFAULT_MANIFEST_REF,
    TASK_IDS,
    get_manifest_item,
    load_dataset_manifest,
    validate_scorer_result,
    validate_t2_bug_annotation,
    validate_t3_transform_spec,
)


def _summarize_manifest(manifest: dict) -> str:
    items = manifest["items"]
    func_ids = [item["func_id"] for item in items]

    task_counts: dict[str, int] = {task: 0 for task in TASK_IDS}
    for item in items:
        for task in TASK_IDS:
            if item["tasks"][task]["available"]:
                task_counts[task] += 1

    return (
        f"manifest_ok items={len(items)} funcs={func_ids} "
        f"task_counts={task_counts}"
    )


def _run_malformed_demos() -> list[str]:
    messages: list[str] = []

    malformed_t2 = {
        "lumen_schema": "t2-bug-v1",
        "func_id": "clamp",
        "source_hash": "abc",
        "bug_id": "clamp.B01",
        "bug_category": "not_a_category",
        "bug_description": "bad category demo",
        "location": {"path": "data/functions/raw/clamp.py", "start_line": 1, "end_line": 1},
        "reference_fix": {"start_line": 1, "end_line": 1, "replacement": "return value"},
        "test_suite_ref": "data/ground_truth/tests/clamp_t2_test.py",
    }

    malformed_t3 = {
        "lumen_schema": "t3-transform-v1",
        "func_id": "clamp",
        "source_hash": "abc",
        "transform_id": "clamp.TR01",
        "instruction": "",
        "test_suite_ref": "data/ground_truth/tests/clamp_t3_test.py",
    }

    malformed_result = {
        "lumen_schema": "scorer-result-v1",
        "func_id": "clamp",
        "task": "T3",
        "condition": "C4",
        "model_id": "demo-model",
        "response_ref": "results/raw/demo.json",
        "ground_truth_ref": "data/ground_truth/tests/clamp_t3_test.py",
        "score": 0.4,
        "status": "parse_failure",
        "subscores": None,
        "failure_reason": {"code": "parse_error", "message": "failed parse"},
        "evidence": {},
    }

    for label, validator, payload in (
        ("malformed_t2", validate_t2_bug_annotation, malformed_t2),
        ("malformed_t3", validate_t3_transform_spec, malformed_t3),
        ("malformed_result", validate_scorer_result, malformed_result),
    ):
        try:
            validator(payload)
        except ContractValidationError as exc:
            messages.append(f"expected_failure {label}: {exc}")
        else:
            messages.append(f"unexpected_success {label}")

    return messages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        default=DEFAULT_MANIFEST_REF,
        help="Repository-relative manifest path",
    )
    parser.add_argument(
        "--demo-malformed",
        action="store_true",
        help="Run malformed sample validations and print expected failures",
    )
    args = parser.parse_args()

    try:
        manifest = load_dataset_manifest(args.manifest, check_paths=True)
    except ContractValidationError as exc:
        print(f"manifest_error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(_summarize_manifest(manifest))

    # Explicitly load pilot seeds by func_id so this command doubles as a seed check.
    for func_id in ("clamp", "count_vowels", "is_sorted"):
        item = get_manifest_item(manifest, func_id)
        print(
            json.dumps(
                {
                    "func_id": func_id,
                    "representations": item["representations"],
                    "tasks": item["tasks"],
                },
                sort_keys=True,
            )
        )

    if args.demo_malformed:
        for line in _run_malformed_demos():
            print(line)


if __name__ == "__main__":
    main()
