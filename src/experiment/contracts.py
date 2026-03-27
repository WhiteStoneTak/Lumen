"""Protocol-first dataset, ground-truth, and scorer contracts for Route A.

This module defines the bounded experiment foundation requested for pilot
execution:
- function-centric dataset manifest contract
- task-specific ground-truth contracts (T1/T2/T3)
- shared scorer input/output contracts
- deterministic path resolution and validation helpers

It intentionally does not implement the full experiment runner or task scorers.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from pipeline.check_no_recursion import is_recursive
from utils.hash import hash_content


DATASET_MANIFEST_SCHEMA = "dataset-manifest-v1"
T1_CHECKLIST_SCHEMA = "t1-checklist-v1"
T2_BUG_SCHEMA = "t2-bug-v1"
T3_TRANSFORM_SCHEMA = "t3-transform-v1"
SCORER_INPUT_SCHEMA = "scorer-input-v1"
SCORER_RESULT_SCHEMA = "scorer-result-v1"
DEFAULT_MANIFEST_REF = "data/dataset/functions_manifest.json"

REPRESENTATION_IDS = ("C1", "C1+", "C2", "C3", "C4")
TASK_IDS = ("T1", "T2", "T3")

T1_PROPERTY_CATEGORIES = {"inputs", "outputs", "behavior", "edge_case"}
T2_BUG_CATEGORIES = {
    "off_by_one",
    "wrong_comparison_operator",
    "missing_boundary_check",
    "incorrect_variable_reference",
    "swapped_arguments",
}

TASK_TO_GROUND_TRUTH_SCHEMA = {
    "T1": T1_CHECKLIST_SCHEMA,
    "T2": T2_BUG_SCHEMA,
    "T3": T3_TRANSFORM_SCHEMA,
}


class ContractValidationError(ValueError):
    """Raised when a dataset or scorer contract is malformed or inconsistent."""


@dataclass(frozen=True)
class FailureReason:
    """Standardized scorer failure reason payload."""

    code: str
    message: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            payload["details"] = self.details
        return payload


def repo_root() -> Path:
    """Return repository root path for deterministic path resolution."""
    return Path(__file__).resolve().parents[2]


def resolve_repo_path(path_ref: str, *, must_exist: bool = True) -> Path:
    """Resolve a repository-relative path and optionally verify it exists."""
    if not isinstance(path_ref, str) or not path_ref.strip():
        raise ContractValidationError(f"Path reference must be a non-empty string: {path_ref!r}")

    candidate = Path(path_ref)
    if candidate.is_absolute():
        raise ContractValidationError(f"Path reference must be repository-relative: {path_ref}")

    root = repo_root().resolve()
    resolved = (root / candidate).resolve()

    if root != resolved and root not in resolved.parents:
        raise ContractValidationError(
            f"Path escapes repository root: {path_ref} -> {resolved}"
        )

    if must_exist and not resolved.exists():
        raise ContractValidationError(f"Path does not exist: {path_ref}")

    return resolved


def _require_object(payload: Any, *, context: str) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise ContractValidationError(f"{context} must be a JSON object.")
    return payload


def _require_non_empty_str(
    payload: Mapping[str, Any],
    field: str,
    *,
    context: str,
) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError(f"{context}.{field} must be a non-empty string.")
    return value


def _require_bool(payload: Mapping[str, Any], field: str, *, context: str) -> bool:
    value = payload.get(field)
    if not isinstance(value, bool):
        raise ContractValidationError(f"{context}.{field} must be a boolean.")
    return value


def _require_int(payload: Mapping[str, Any], field: str, *, context: str) -> int:
    value = payload.get(field)
    if not isinstance(value, int):
        raise ContractValidationError(f"{context}.{field} must be an integer.")
    return value


def _load_json(path_ref: str, *, context: str) -> dict[str, Any]:
    path = resolve_repo_path(path_ref, must_exist=True)
    try:
        content = path.read_text(encoding="utf-8")
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ContractValidationError(f"{context}: invalid JSON in {path_ref}: {exc}") from exc
    except OSError as exc:
        raise ContractValidationError(f"{context}: failed reading {path_ref}: {exc}") from exc

    return dict(_require_object(payload, context=context))


def _parse_top_level_structure(source: str, *, func_id: str) -> tuple[bool, bool]:
    """Return (non_recursive, single_function) eligibility from raw source."""
    tree = ast.parse(source)

    top_level_defs = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    has_disallowed_top_level = any(
        isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef)) for node in tree.body
    )

    single_function = (
        len(top_level_defs) == 1
        and top_level_defs[0].name == func_id
        and not has_disallowed_top_level
    )

    non_recursive = not is_recursive(source)
    return non_recursive, single_function


def validate_t1_checklist(
    payload: Mapping[str, Any],
    *,
    expected_func_id: str | None = None,
    expected_source_hash: str | None = None,
) -> dict[str, Any]:
    """Validate a T1 checklist artifact (`t1-checklist-v1`)."""
    obj = _require_object(payload, context="t1")

    schema = _require_non_empty_str(obj, "lumen_schema", context="t1")
    if schema != T1_CHECKLIST_SCHEMA:
        raise ContractValidationError(
            f"t1.lumen_schema must be '{T1_CHECKLIST_SCHEMA}', got '{schema}'."
        )

    func_id = _require_non_empty_str(obj, "func_id", context="t1")
    source_hash = _require_non_empty_str(obj, "source_hash", context="t1")

    if expected_func_id is not None and func_id != expected_func_id:
        raise ContractValidationError(
            f"t1.func_id mismatch: expected '{expected_func_id}', got '{func_id}'."
        )
    if expected_source_hash is not None and source_hash != expected_source_hash:
        raise ContractValidationError(
            "t1.source_hash mismatch against manifest source_hash."
        )

    properties = obj.get("properties")
    if not isinstance(properties, list) or not properties:
        raise ContractValidationError("t1.properties must be a non-empty list.")

    seen_ids: set[str] = set()
    for idx, raw_property in enumerate(properties):
        prop = _require_object(raw_property, context=f"t1.properties[{idx}]")
        property_id = _require_non_empty_str(prop, "property_id", context=f"t1.properties[{idx}]")
        category = _require_non_empty_str(prop, "category", context=f"t1.properties[{idx}]")
        statement = _require_non_empty_str(prop, "statement", context=f"t1.properties[{idx}]")
        required = _require_bool(prop, "required", context=f"t1.properties[{idx}]")

        if category not in T1_PROPERTY_CATEGORIES:
            raise ContractValidationError(
                f"t1.properties[{idx}].category '{category}' is not allowed. "
                f"Allowed: {sorted(T1_PROPERTY_CATEGORIES)}"
            )
        if not property_id.startswith(f"{func_id}."):
            raise ContractValidationError(
                f"t1.properties[{idx}].property_id must start with '{func_id}.'."
            )
        if property_id in seen_ids:
            raise ContractValidationError(
                f"t1.properties[{idx}].property_id '{property_id}' is duplicated."
            )
        seen_ids.add(property_id)

        if not statement.strip():
            raise ContractValidationError(
                f"t1.properties[{idx}].statement must not be blank."
            )

        if not isinstance(required, bool):
            raise ContractValidationError(
                f"t1.properties[{idx}].required must be a boolean."
            )

    return dict(obj)


def validate_t2_bug_annotation(
    payload: Mapping[str, Any],
    *,
    expected_func_id: str | None = None,
    expected_source_hash: str | None = None,
    check_paths: bool = True,
) -> dict[str, Any]:
    """Validate a T2 bug annotation artifact (`t2-bug-v1`)."""
    obj = _require_object(payload, context="t2")

    schema = _require_non_empty_str(obj, "lumen_schema", context="t2")
    if schema != T2_BUG_SCHEMA:
        raise ContractValidationError(
            f"t2.lumen_schema must be '{T2_BUG_SCHEMA}', got '{schema}'."
        )

    func_id = _require_non_empty_str(obj, "func_id", context="t2")
    source_hash = _require_non_empty_str(obj, "source_hash", context="t2")
    bug_id = _require_non_empty_str(obj, "bug_id", context="t2")
    bug_category = _require_non_empty_str(obj, "bug_category", context="t2")
    _require_non_empty_str(obj, "bug_description", context="t2")
    test_suite_ref = _require_non_empty_str(obj, "test_suite_ref", context="t2")

    if expected_func_id is not None and func_id != expected_func_id:
        raise ContractValidationError(
            f"t2.func_id mismatch: expected '{expected_func_id}', got '{func_id}'."
        )
    if expected_source_hash is not None and source_hash != expected_source_hash:
        raise ContractValidationError(
            "t2.source_hash mismatch against manifest source_hash."
        )

    if not bug_id.startswith(f"{func_id}.B"):
        raise ContractValidationError(
            f"t2.bug_id must start with '{func_id}.B'."
        )

    if bug_category not in T2_BUG_CATEGORIES:
        raise ContractValidationError(
            f"t2.bug_category '{bug_category}' is invalid. "
            f"Allowed categories: {sorted(T2_BUG_CATEGORIES)}"
        )

    location = _require_object(obj.get("location"), context="t2.location")
    location_path = _require_non_empty_str(location, "path", context="t2.location")
    location_start = _require_int(location, "start_line", context="t2.location")
    location_end = _require_int(location, "end_line", context="t2.location")

    if location_start < 1 or location_end < location_start:
        raise ContractValidationError(
            "t2.location must use 1-based inclusive line numbers with end_line >= start_line."
        )

    reference_fix = _require_object(obj.get("reference_fix"), context="t2.reference_fix")
    fix_start = _require_int(reference_fix, "start_line", context="t2.reference_fix")
    fix_end = _require_int(reference_fix, "end_line", context="t2.reference_fix")
    _require_non_empty_str(reference_fix, "replacement", context="t2.reference_fix")

    if fix_start < 1 or fix_end < fix_start:
        raise ContractValidationError(
            "t2.reference_fix must use 1-based inclusive line numbers with end_line >= start_line."
        )

    if check_paths:
        resolve_repo_path(location_path, must_exist=True)
        resolve_repo_path(test_suite_ref, must_exist=True)

    return dict(obj)


def validate_t3_transform_spec(
    payload: Mapping[str, Any],
    *,
    expected_func_id: str | None = None,
    expected_source_hash: str | None = None,
    check_paths: bool = True,
) -> dict[str, Any]:
    """Validate a T3 transformation-spec artifact (`t3-transform-v1`)."""
    obj = _require_object(payload, context="t3")

    schema = _require_non_empty_str(obj, "lumen_schema", context="t3")
    if schema != T3_TRANSFORM_SCHEMA:
        raise ContractValidationError(
            f"t3.lumen_schema must be '{T3_TRANSFORM_SCHEMA}', got '{schema}'."
        )

    func_id = _require_non_empty_str(obj, "func_id", context="t3")
    source_hash = _require_non_empty_str(obj, "source_hash", context="t3")
    transform_id = _require_non_empty_str(obj, "transform_id", context="t3")
    instruction = _require_non_empty_str(obj, "instruction", context="t3")
    test_suite_ref = _require_non_empty_str(obj, "test_suite_ref", context="t3")

    if expected_func_id is not None and func_id != expected_func_id:
        raise ContractValidationError(
            f"t3.func_id mismatch: expected '{expected_func_id}', got '{func_id}'."
        )
    if expected_source_hash is not None and source_hash != expected_source_hash:
        raise ContractValidationError(
            "t3.source_hash mismatch against manifest source_hash."
        )

    if not transform_id.startswith(f"{func_id}.TR"):
        raise ContractValidationError(
            f"t3.transform_id must start with '{func_id}.TR'."
        )

    if not instruction.strip():
        raise ContractValidationError("t3.instruction must be non-empty natural language text.")

    if check_paths:
        resolve_repo_path(test_suite_ref, must_exist=True)

    return dict(obj)


def _validate_task_ground_truth(
    *,
    task_id: str,
    ground_truth_ref: str,
    expected_func_id: str,
    expected_source_hash: str,
    check_paths: bool,
) -> dict[str, Any]:
    payload = _load_json(ground_truth_ref, context=f"{task_id} artifact")
    if task_id == "T1":
        return validate_t1_checklist(
            payload,
            expected_func_id=expected_func_id,
            expected_source_hash=expected_source_hash,
        )
    if task_id == "T2":
        return validate_t2_bug_annotation(
            payload,
            expected_func_id=expected_func_id,
            expected_source_hash=expected_source_hash,
            check_paths=check_paths,
        )
    if task_id == "T3":
        return validate_t3_transform_spec(
            payload,
            expected_func_id=expected_func_id,
            expected_source_hash=expected_source_hash,
            check_paths=check_paths,
        )
    raise ContractValidationError(f"Unsupported task id: {task_id}")


def _artifact_source_hash(path_ref: str | None) -> str | None:
    if path_ref is None:
        return None
    payload = _load_json(path_ref, context=f"artifact {path_ref}")
    source_hash = payload.get("source_hash")
    if source_hash is None:
        return None
    if not isinstance(source_hash, str) or not source_hash:
        raise ContractValidationError(
            f"artifact {path_ref} has malformed source_hash field."
        )
    return source_hash


def validate_dataset_manifest_item(
    item: Mapping[str, Any],
    *,
    check_paths: bool = True,
) -> dict[str, Any]:
    """Validate one function-centric item inside `dataset-manifest-v1`."""
    obj = _require_object(item, context="manifest.item")

    func_id = _require_non_empty_str(obj, "func_id", context="manifest.item")
    source_hash = _require_non_empty_str(obj, "source_hash", context="manifest.item")

    inclusion_status = _require_non_empty_str(obj, "inclusion_status", context="manifest.item")
    if inclusion_status not in {"included", "excluded", "deferred"}:
        raise ContractValidationError(
            "manifest.item.inclusion_status must be one of: included, excluded, deferred."
        )

    dataset_tier = _require_non_empty_str(obj, "dataset_tier", context="manifest.item")
    if dataset_tier not in {"pilot", "full"}:
        raise ContractValidationError(
            "manifest.item.dataset_tier must be one of: pilot, full."
        )

    eligibility = _require_object(obj.get("eligibility"), context="manifest.item.eligibility")
    for key in ("non_recursive", "single_function"):
        status = _require_non_empty_str(eligibility, key, context="manifest.item.eligibility")
        if status not in {"eligible", "ineligible", "unknown"}:
            raise ContractValidationError(
                f"manifest.item.eligibility.{key} must be eligible|ineligible|unknown."
            )

    artifacts = _require_object(obj.get("artifacts"), context="manifest.item.artifacts")
    artifact_keys = {
        "raw_source",
        "annotated_text",
        "ast",
        "typed_ast",
        "ir",
    }
    for key in artifact_keys:
        if key not in artifacts:
            raise ContractValidationError(f"manifest.item.artifacts missing key '{key}'.")
        value = artifacts[key]
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ContractValidationError(
                f"manifest.item.artifacts.{key} must be null or non-empty string."
            )

    representations = _require_object(
        obj.get("representations"), context="manifest.item.representations"
    )
    for rep in REPRESENTATION_IDS:
        if rep not in representations:
            raise ContractValidationError(
                f"manifest.item.representations missing '{rep}'."
            )
        if not isinstance(representations[rep], bool):
            raise ContractValidationError(
                f"manifest.item.representations.{rep} must be boolean."
            )

    tasks = _require_object(obj.get("tasks"), context="manifest.item.tasks")
    for task_id in TASK_IDS:
        task_obj = _require_object(tasks.get(task_id), context=f"manifest.item.tasks.{task_id}")
        available = _require_bool(task_obj, "available", context=f"manifest.item.tasks.{task_id}")
        gt_ref = task_obj.get("ground_truth_ref")
        if available:
            if not isinstance(gt_ref, str) or not gt_ref.strip():
                raise ContractValidationError(
                    f"manifest.item.tasks.{task_id}.ground_truth_ref must be set when available=true."
                )
        else:
            if gt_ref is not None:
                raise ContractValidationError(
                    f"manifest.item.tasks.{task_id}.ground_truth_ref must be null when available=false."
                )

    lineage = _require_object(obj.get("lineage"), context="manifest.item.lineage")
    lineage_keys = {
        "raw_source_hash",
        "ast_source_hash",
        "typed_ast_source_hash",
        "ir_source_hash",
        "t1_source_hash",
    }
    for key in lineage_keys:
        if key not in lineage:
            raise ContractValidationError(f"manifest.item.lineage missing key '{key}'.")
        value = lineage[key]
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ContractValidationError(
                f"manifest.item.lineage.{key} must be null or non-empty string."
            )

    rep_to_artifact = {
        "C1": "raw_source",
        "C1+": "annotated_text",
        "C2": "ast",
        "C3": "typed_ast",
        "C4": "ir",
    }
    for rep, key in rep_to_artifact.items():
        path_ref = artifacts[key]
        has_ref = isinstance(path_ref, str)
        is_available = representations[rep]

        if is_available and not has_ref:
            raise ContractValidationError(
                f"manifest.item.representations.{rep}=true requires artifacts.{key}."
            )
        if not is_available and has_ref:
            raise ContractValidationError(
                f"manifest.item.representations.{rep}=false requires artifacts.{key}=null."
            )
        if is_available and check_paths and isinstance(path_ref, str):
            resolve_repo_path(path_ref, must_exist=True)

    raw_source_ref = artifacts["raw_source"]
    if not isinstance(raw_source_ref, str):
        raise ContractValidationError("manifest.item.artifacts.raw_source must be set.")

    raw_path = resolve_repo_path(raw_source_ref, must_exist=check_paths)
    raw_source = raw_path.read_text(encoding="utf-8") if check_paths else ""

    if check_paths:
        computed_source_hash = hash_content(raw_source)
        if source_hash != computed_source_hash:
            raise ContractValidationError(
                f"manifest item '{func_id}' source_hash does not match raw source content."
            )

        non_recursive, single_function = _parse_top_level_structure(raw_source, func_id=func_id)
        non_recursive_status = eligibility["non_recursive"]
        single_function_status = eligibility["single_function"]

        if non_recursive_status == "eligible" and not non_recursive:
            raise ContractValidationError(
                f"manifest item '{func_id}' claims non_recursive=eligible but source is recursive."
            )
        if non_recursive_status == "ineligible" and non_recursive:
            raise ContractValidationError(
                f"manifest item '{func_id}' claims non_recursive=ineligible but source is non-recursive."
            )
        if single_function_status == "eligible" and not single_function:
            raise ContractValidationError(
                f"manifest item '{func_id}' claims single_function=eligible but source fails single-function scope."
            )
        if single_function_status == "ineligible" and single_function:
            raise ContractValidationError(
                f"manifest item '{func_id}' claims single_function=ineligible but source is single-function."
            )

    for task_id in TASK_IDS:
        task_obj = tasks[task_id]
        available = task_obj["available"]
        gt_ref = task_obj["ground_truth_ref"]
        if available and isinstance(gt_ref, str):
            gt_payload = _validate_task_ground_truth(
                task_id=task_id,
                ground_truth_ref=gt_ref,
                expected_func_id=func_id,
                expected_source_hash=source_hash,
                check_paths=check_paths,
            )
            schema = gt_payload.get("lumen_schema")
            if schema != TASK_TO_GROUND_TRUTH_SCHEMA[task_id]:
                raise ContractValidationError(
                    f"manifest item '{func_id}' task {task_id} ground truth schema mismatch: {schema!r}."
                )

    raw_source_hash = source_hash if check_paths else lineage["raw_source_hash"]
    ast_source_hash = _artifact_source_hash(artifacts["ast"]) if artifacts["ast"] else None
    typed_ast_source_hash = (
        _artifact_source_hash(artifacts["typed_ast"]) if artifacts["typed_ast"] else None
    )
    ir_source_hash = _artifact_source_hash(artifacts["ir"]) if artifacts["ir"] else None
    t1_source_hash = (
        _artifact_source_hash(tasks["T1"]["ground_truth_ref"])
        if tasks["T1"]["available"]
        else None
    )

    if lineage["raw_source_hash"] != raw_source_hash:
        raise ContractValidationError(
            f"manifest item '{func_id}' lineage.raw_source_hash is inconsistent."
        )
    if lineage["ast_source_hash"] != ast_source_hash:
        raise ContractValidationError(
            f"manifest item '{func_id}' lineage.ast_source_hash is inconsistent."
        )
    if lineage["typed_ast_source_hash"] != typed_ast_source_hash:
        raise ContractValidationError(
            f"manifest item '{func_id}' lineage.typed_ast_source_hash is inconsistent."
        )
    if lineage["ir_source_hash"] != ir_source_hash:
        raise ContractValidationError(
            f"manifest item '{func_id}' lineage.ir_source_hash is inconsistent."
        )
    if lineage["t1_source_hash"] != t1_source_hash:
        raise ContractValidationError(
            f"manifest item '{func_id}' lineage.t1_source_hash is inconsistent."
        )

    if inclusion_status == "included":
        if eligibility["non_recursive"] != "eligible":
            raise ContractValidationError(
                f"manifest item '{func_id}' is included but non_recursive is not eligible."
            )
        if eligibility["single_function"] != "eligible":
            raise ContractValidationError(
                f"manifest item '{func_id}' is included but single_function is not eligible."
            )

    return dict(obj)


def validate_dataset_manifest(
    payload: Mapping[str, Any],
    *,
    check_paths: bool = True,
) -> dict[str, Any]:
    """Validate full function-centric dataset manifest (`dataset-manifest-v1`)."""
    obj = _require_object(payload, context="manifest")

    schema = _require_non_empty_str(obj, "lumen_schema", context="manifest")
    if schema != DATASET_MANIFEST_SCHEMA:
        raise ContractValidationError(
            f"manifest.lumen_schema must be '{DATASET_MANIFEST_SCHEMA}', got '{schema}'."
        )

    _require_non_empty_str(obj, "protocol_scope", context="manifest")

    items = obj.get("items")
    if not isinstance(items, list) or not items:
        raise ContractValidationError("manifest.items must be a non-empty list.")

    seen_func_ids: set[str] = set()
    for idx, raw_item in enumerate(items):
        item = validate_dataset_manifest_item(raw_item, check_paths=check_paths)
        func_id = item["func_id"]
        if func_id in seen_func_ids:
            raise ContractValidationError(
                f"manifest.items[{idx}] duplicates func_id '{func_id}'."
            )
        seen_func_ids.add(func_id)

    return dict(obj)


def load_dataset_manifest(
    manifest_ref: str = DEFAULT_MANIFEST_REF,
    *,
    check_paths: bool = True,
) -> dict[str, Any]:
    """Load and validate the dataset manifest from disk."""
    payload = _load_json(manifest_ref, context="manifest")
    return validate_dataset_manifest(payload, check_paths=check_paths)


def get_manifest_item(manifest: Mapping[str, Any], func_id: str) -> dict[str, Any]:
    """Return the manifest item for *func_id*, or raise if missing."""
    items = manifest.get("items")
    if not isinstance(items, list):
        raise ContractValidationError("manifest.items missing or malformed.")

    for item in items:
        if isinstance(item, Mapping) and item.get("func_id") == func_id:
            return dict(item)

    raise ContractValidationError(f"func_id '{func_id}' is not present in manifest.")


def validate_failure_reason(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate standardized failure reason shape."""
    obj = _require_object(payload, context="failure_reason")
    _require_non_empty_str(obj, "code", context="failure_reason")
    _require_non_empty_str(obj, "message", context="failure_reason")

    details = obj.get("details")
    if details is not None and not isinstance(details, Mapping):
        raise ContractValidationError("failure_reason.details must be an object when set.")

    return dict(obj)


def validate_scorer_input(
    payload: Mapping[str, Any],
    *,
    check_paths: bool = True,
) -> dict[str, Any]:
    """Validate and resolve scorer input contract (`scorer-input-v1`)."""
    obj = _require_object(payload, context="scorer_input")

    schema = _require_non_empty_str(obj, "lumen_schema", context="scorer_input")
    if schema != SCORER_INPUT_SCHEMA:
        raise ContractValidationError(
            f"scorer_input.lumen_schema must be '{SCORER_INPUT_SCHEMA}', got '{schema}'."
        )

    func_id = _require_non_empty_str(obj, "func_id", context="scorer_input")
    task_id = _require_non_empty_str(obj, "task", context="scorer_input")
    condition = _require_non_empty_str(obj, "condition", context="scorer_input")
    _require_non_empty_str(obj, "model_id", context="scorer_input")
    response_ref = _require_non_empty_str(obj, "response_ref", context="scorer_input")

    if task_id not in TASK_IDS:
        raise ContractValidationError(
            f"scorer_input.task must be one of {TASK_IDS}, got '{task_id}'."
        )
    if condition not in REPRESENTATION_IDS:
        raise ContractValidationError(
            f"scorer_input.condition must be one of {REPRESENTATION_IDS}, got '{condition}'."
        )

    manifest_ref = obj.get("manifest_ref") or DEFAULT_MANIFEST_REF
    if not isinstance(manifest_ref, str) or not manifest_ref.strip():
        raise ContractValidationError("scorer_input.manifest_ref must be a string when provided.")

    manifest = load_dataset_manifest(manifest_ref, check_paths=check_paths)
    item = get_manifest_item(manifest, func_id)

    task_info = item["tasks"][task_id]
    if not task_info["available"]:
        raise ContractValidationError(
            f"scorer_input task '{task_id}' is unavailable for func_id '{func_id}' in manifest."
        )

    ground_truth_ref = task_info["ground_truth_ref"]
    if not isinstance(ground_truth_ref, str):
        raise ContractValidationError(
            f"manifest task '{task_id}' for '{func_id}' has invalid ground_truth_ref."
        )

    if check_paths:
        resolve_repo_path(response_ref, must_exist=True)
        resolve_repo_path(ground_truth_ref, must_exist=True)

    normalized = dict(obj)
    normalized["manifest_ref"] = manifest_ref
    normalized["ground_truth_ref"] = ground_truth_ref
    normalized["source_hash"] = item["source_hash"]

    return normalized


def validate_scorer_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate scorer output contract (`scorer-result-v1`)."""
    obj = _require_object(payload, context="scorer_result")

    schema = _require_non_empty_str(obj, "lumen_schema", context="scorer_result")
    if schema != SCORER_RESULT_SCHEMA:
        raise ContractValidationError(
            f"scorer_result.lumen_schema must be '{SCORER_RESULT_SCHEMA}', got '{schema}'."
        )

    _require_non_empty_str(obj, "func_id", context="scorer_result")
    task_id = _require_non_empty_str(obj, "task", context="scorer_result")
    condition = _require_non_empty_str(obj, "condition", context="scorer_result")
    _require_non_empty_str(obj, "model_id", context="scorer_result")
    _require_non_empty_str(obj, "response_ref", context="scorer_result")
    _require_non_empty_str(obj, "ground_truth_ref", context="scorer_result")

    if task_id not in TASK_IDS:
        raise ContractValidationError(
            f"scorer_result.task must be one of {TASK_IDS}, got '{task_id}'."
        )
    if condition not in REPRESENTATION_IDS:
        raise ContractValidationError(
            f"scorer_result.condition must be one of {REPRESENTATION_IDS}, got '{condition}'."
        )

    score = obj.get("score")
    if not isinstance(score, (int, float)):
        raise ContractValidationError("scorer_result.score must be numeric.")
    score = float(score)

    status = _require_non_empty_str(obj, "status", context="scorer_result")
    allowed_statuses = {
        "ok",
        "parse_failure",
        "execution_failure",
        "invalid_response",
        "scoring_error",
    }
    if status not in allowed_statuses:
        raise ContractValidationError(
            f"scorer_result.status must be one of {sorted(allowed_statuses)}."
        )

    subscores = obj.get("subscores")
    if subscores is not None and not isinstance(subscores, Mapping):
        raise ContractValidationError("scorer_result.subscores must be an object when set.")

    failure_reason = obj.get("failure_reason")
    if status == "ok":
        if failure_reason is not None:
            raise ContractValidationError(
                "scorer_result.failure_reason must be null when status='ok'."
            )
    else:
        if failure_reason is None:
            raise ContractValidationError(
                "scorer_result.failure_reason is required when status is not 'ok'."
            )
        validate_failure_reason(_require_object(failure_reason, context="scorer_result.failure_reason"))

    if task_id == "T1":
        if not (0.0 <= score <= 1.0):
            raise ContractValidationError("T1 score must be in [0.0, 1.0].")

    if task_id == "T2":
        if score not in {0.0, 1.0, 2.0, 3.0}:
            raise ContractValidationError("T2 score must be in the discrete set {0,1,2,3}.")
        if not isinstance(subscores, Mapping):
            raise ContractValidationError(
                "T2 result requires subscores with location/diagnosis/fix keys."
            )

        for key in ("location", "diagnosis", "fix"):
            value = subscores.get(key)
            if value not in {0, 1}:
                raise ContractValidationError(
                    f"T2 subscores.{key} must be 0 or 1."
                )

        if score != float(subscores["location"] + subscores["diagnosis"] + subscores["fix"]):
            raise ContractValidationError(
                "T2 composite score must equal location + diagnosis + fix."
            )

    if task_id == "T3":
        if not (0.0 <= score <= 1.0):
            raise ContractValidationError("T3 score must be in [0.0, 1.0].")
        if status in {"parse_failure", "execution_failure"} and score != 0.0:
            raise ContractValidationError(
                "T3 parse_failure/execution_failure must report score=0.0."
            )

    return dict(obj)


def load_scorer_input_file(
    scorer_input_ref: str,
    *,
    check_paths: bool = True,
) -> dict[str, Any]:
    """Load and validate scorer-input artifact from disk."""
    payload = _load_json(scorer_input_ref, context="scorer_input file")
    return validate_scorer_input(payload, check_paths=check_paths)


def load_ground_truth_for_scorer_input(
    scorer_input: Mapping[str, Any],
    *,
    check_paths: bool = True,
) -> dict[str, Any]:
    """Load validated task ground truth for a validated scorer input record."""
    normalized = validate_scorer_input(scorer_input, check_paths=check_paths)
    task_id = normalized["task"]
    ground_truth_ref = normalized["ground_truth_ref"]

    payload = _load_json(ground_truth_ref, context=f"{task_id} artifact")
    source_hash = normalized["source_hash"]
    func_id = normalized["func_id"]

    if task_id == "T1":
        return validate_t1_checklist(
            payload,
            expected_func_id=func_id,
            expected_source_hash=source_hash,
        )
    if task_id == "T2":
        return validate_t2_bug_annotation(
            payload,
            expected_func_id=func_id,
            expected_source_hash=source_hash,
            check_paths=check_paths,
        )
    if task_id == "T3":
        return validate_t3_transform_spec(
            payload,
            expected_func_id=func_id,
            expected_source_hash=source_hash,
            check_paths=check_paths,
        )
    raise ContractValidationError(f"Unsupported task id: {task_id}")


def build_scorer_result(
    *,
    func_id: str,
    task: str,
    condition: str,
    model_id: str,
    response_ref: str,
    ground_truth_ref: str,
    score: float,
    status: str = "ok",
    subscores: Mapping[str, Any] | None = None,
    failure_reason: FailureReason | None = None,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build and validate scorer-result payload with canonical failure shape."""
    payload: dict[str, Any] = {
        "lumen_schema": SCORER_RESULT_SCHEMA,
        "func_id": func_id,
        "task": task,
        "condition": condition,
        "model_id": model_id,
        "response_ref": response_ref,
        "ground_truth_ref": ground_truth_ref,
        "score": float(score),
        "status": status,
        "subscores": dict(subscores) if subscores is not None else None,
        "failure_reason": failure_reason.to_dict() if failure_reason is not None else None,
        "evidence": dict(evidence) if evidence is not None else {},
    }
    return validate_scorer_result(payload)
