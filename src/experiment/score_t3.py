"""Protocol-first T3 scorer for Lumen Route A.

T3 scores a model's ability to correctly transform a function according to
a natural-language transformation spec. The score is the fraction of linked
post-transform tests that pass against the candidate implementation.

Scoring shape:
  score = passed_tests / total_tests  ∈ [0.0, 1.0]
  parse_failure / execution_failure   → score = 0.0

See: docs/experiment-dataset-contracts.md §2 T3, docs/experimental-protocol.md §4.8
"""

from __future__ import annotations

import ast
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from experiment.contracts import (
    ContractValidationError,
    FailureReason,
    build_scorer_result,
    get_manifest_item,
    load_dataset_manifest,
    repo_root,
    validate_scorer_input,
    validate_t3_transform_spec,
)

# ── failure-reason codes ────────────────────────────────────────────────────
FR_NO_CODE_CANDIDATE = "no_code_candidate"
FR_SYNTAX_ERROR = "syntax_error"
FR_WRONG_FUNCTION_NAME = "wrong_function_name"
FR_MISSING_TARGET_FUNCTION = "missing_target_function"
FR_MODULE_LOAD_FAILURE = "module_load_failure"
FR_TEST_EXECUTION_FAILURE = "test_execution_failure"
FR_ZERO_TOTAL_TESTS = "zero_total_tests"


# ---------------------------------------------------------------------------
# Context loader
# ---------------------------------------------------------------------------

def load_t3_scoring_context(scorer_input: dict[str, Any]) -> dict[str, Any]:
    """Load and validate T3 scoring context from scorer input."""
    normalized = validate_scorer_input(scorer_input, check_paths=False)
    func_id = normalized["func_id"]
    task_id = normalized["task"]
    if task_id != "T3":
        raise ContractValidationError(f"score_t3 requires task=T3, got {task_id!r}")

    manifest = load_dataset_manifest(check_paths=True)
    item = get_manifest_item(manifest, func_id)

    task_info = item["tasks"]["T3"]
    if not task_info["available"]:
        raise ContractValidationError(f"T3 is not available for {func_id!r}")

    gt_ref = task_info["ground_truth_ref"]
    gt_path = (repo_root() / gt_ref).resolve()
    truth_raw = json.loads(gt_path.read_text(encoding="utf-8"))
    truth = validate_t3_transform_spec(truth_raw, expected_func_id=func_id, check_paths=True)

    test_suite_path = (repo_root() / truth["test_suite_ref"]).resolve()

    return {
        "truth": truth,
        "func_id": func_id,
        "test_suite_path": test_suite_path,
    }


# ---------------------------------------------------------------------------
# Code extraction
# ---------------------------------------------------------------------------

def extract_t3_code_candidate(response_text: str, func_id: str) -> str | None:
    """Extract the best Python code candidate from a model response.

    Extraction order:
    1. Fenced Python code block (```python ... ```)
    2. Fenced code block without language tag (``` ... ```)
    3. Top-level def {func_id}(...) found in prose
    4. None if no candidate found

    If multiple blocks exist, prefer the one containing def {func_id}(.
    """
    # Try fenced code blocks first
    python_blocks = re.findall(r'```python\s*\n(.*?)```', response_text, re.DOTALL)
    generic_blocks = re.findall(r'```(?!python)\s*\n(.*?)```', response_text, re.DOTALL)

    all_blocks = python_blocks + generic_blocks

    # Among all blocks, prefer those containing the target function
    target_pattern = f"def {func_id}("
    preferred = [b for b in all_blocks if target_pattern in b]
    if preferred:
        return preferred[0].strip()
    if all_blocks:
        return all_blocks[0].strip()

    # Fallback: extract def block from prose
    pattern = rf'(def\s+{re.escape(func_id)}\s*\(.*?)(?=\ndef\s|\Z)'
    match = re.search(pattern, response_text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return None


# ---------------------------------------------------------------------------
# Parse/validation
# ---------------------------------------------------------------------------

def parse_t3_candidate(code_text: str, func_id: str) -> tuple[bool, str]:
    """Parse extracted code and check it contains the expected function.

    Returns (is_valid, error_message). error_message is empty string on success.
    """
    try:
        tree = ast.parse(code_text)
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc}"

    func_names = [
        node.name for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    ]

    if not func_names:
        return False, f"No function definition found in candidate code"

    if func_id not in func_names:
        return False, f"Expected function {func_id!r} not found; found: {func_names}"

    return True, ""


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def run_t3_tests(
    code_text: str,
    func_id: str,
    test_suite_path: Path,
) -> tuple[int, int, str]:
    """Load candidate function, inject into T3 test module, run tests.

    Returns (passed_count, total_count, error_message).
    error_message is non-empty on harness failure.
    """
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code_text)
            tmp_path = f.name

        unique_id = os.urandom(4).hex()

        # Load candidate module
        cand_spec = importlib.util.spec_from_file_location(
            f"_t3_cand_{func_id}_{unique_id}", tmp_path
        )
        if cand_spec is None or cand_spec.loader is None:
            return 0, 0, "Could not create module spec from candidate temp file"
        cand_mod = importlib.util.module_from_spec(cand_spec)
        try:
            cand_spec.loader.exec_module(cand_mod)  # type: ignore[union-attr]
        except Exception as exc:
            return 0, 0, f"Candidate module load failed: {exc}"

        candidate_fn = getattr(cand_mod, func_id, None)
        if candidate_fn is None:
            return 0, 0, f"Function {func_id!r} not found in loaded candidate"

        # Load test module fresh (unique name prevents caching)
        test_spec = importlib.util.spec_from_file_location(
            f"_t3_suite_{func_id}_{unique_id}", str(test_suite_path)
        )
        if test_spec is None or test_spec.loader is None:
            return 0, 0, f"Could not load test module from {test_suite_path}"
        test_mod = importlib.util.module_from_spec(test_spec)
        try:
            test_spec.loader.exec_module(test_mod)  # type: ignore[union-attr]
        except Exception as exc:
            return 0, 0, f"Test module load failed: {exc}"

        # Inject candidate function
        setattr(test_mod, func_id, candidate_fn)

        # Also patch method globals so TestCase methods see the injected function
        for attr_name in dir(test_mod):
            obj = getattr(test_mod, attr_name)
            if isinstance(obj, type) and issubclass(obj, unittest.TestCase):
                for method_name in obj.__dict__:
                    method = getattr(obj, method_name, None)
                    if callable(method) and hasattr(method, "__func__"):
                        if func_id in method.__func__.__globals__:
                            method.__func__.__globals__[func_id] = candidate_fn

        # Run tests
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_mod)
        buf = io.StringIO()
        runner = unittest.TextTestRunner(verbosity=0, stream=buf, failfast=False)
        result = runner.run(suite)

        total = result.testsRun
        failed = len(result.failures) + len(result.errors)
        passed = total - failed
        return passed, total, ""

    finally:
        if tmp_path is not None and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def score_t3(
    scorer_input_payload: dict[str, Any],
    response_text: str,
) -> dict[str, Any]:
    """Score a T3 model response and return a validated scorer-result-v1 dict.

    Parameters
    ----------
    scorer_input_payload:
        A scorer-input-v1 dict (must include func_id, task='T3', condition,
        model_id, response_ref).
    response_text:
        Free-form model response to score.

    Returns
    -------
    A validated scorer-result-v1 dict.
    """
    func_id: str = scorer_input_payload.get("func_id", "")
    condition: str = scorer_input_payload.get("condition", "")
    model_id: str = scorer_input_payload.get("model_id", "")
    response_ref: str = scorer_input_payload.get("response_ref", "")

    # Load context (raises ContractValidationError on bad input)
    try:
        ctx = load_t3_scoring_context(scorer_input_payload)
    except ContractValidationError as exc:
        return build_scorer_result(
            func_id=func_id or "unknown",
            task="T3",
            condition=condition or "C1",
            model_id=model_id or "unknown",
            response_ref=response_ref or "unknown",
            ground_truth_ref="unknown",
            score=0.0,
            status="scoring_error",
            failure_reason=FailureReason(
                code="context_load_error",
                message=str(exc),
            ),
        )

    func_id = ctx["func_id"]
    truth = ctx["truth"]
    test_suite_path = ctx["test_suite_path"]
    ground_truth_ref = truth["test_suite_ref"]

    # Extract code candidate
    candidate_code = extract_t3_code_candidate(response_text, func_id)
    if candidate_code is None:
        return build_scorer_result(
            func_id=func_id,
            task="T3",
            condition=condition,
            model_id=model_id,
            response_ref=response_ref,
            ground_truth_ref=ground_truth_ref,
            score=0.0,
            status="parse_failure",
            failure_reason=FailureReason(
                code=FR_NO_CODE_CANDIDATE,
                message="No Python code candidate found in response",
            ),
            evidence={"response_length": len(response_text)},
        )

    # Validate parse + function presence
    valid, parse_error = parse_t3_candidate(candidate_code, func_id)
    if not valid:
        if "SyntaxError" in parse_error:
            fr_code = FR_SYNTAX_ERROR
        elif "not found; found:" in parse_error:
            fr_code = FR_WRONG_FUNCTION_NAME
        else:
            fr_code = FR_MISSING_TARGET_FUNCTION
        return build_scorer_result(
            func_id=func_id,
            task="T3",
            condition=condition,
            model_id=model_id,
            response_ref=response_ref,
            ground_truth_ref=ground_truth_ref,
            score=0.0,
            status="parse_failure",
            failure_reason=FailureReason(code=fr_code, message=parse_error),
            evidence={"candidate_length": len(candidate_code)},
        )

    # Run tests
    passed, total, harness_error = run_t3_tests(candidate_code, func_id, test_suite_path)

    if harness_error:
        return build_scorer_result(
            func_id=func_id,
            task="T3",
            condition=condition,
            model_id=model_id,
            response_ref=response_ref,
            ground_truth_ref=ground_truth_ref,
            score=0.0,
            status="execution_failure",
            failure_reason=FailureReason(code=FR_MODULE_LOAD_FAILURE, message=harness_error),
            evidence={"candidate_length": len(candidate_code)},
        )

    if total == 0:
        return build_scorer_result(
            func_id=func_id,
            task="T3",
            condition=condition,
            model_id=model_id,
            response_ref=response_ref,
            ground_truth_ref=ground_truth_ref,
            score=0.0,
            status="scoring_error",
            failure_reason=FailureReason(
                code=FR_ZERO_TOTAL_TESTS,
                message="Test suite ran 0 tests; cannot compute pass rate",
            ),
            evidence={},
        )

    score = passed / total

    # status="ok" regardless of pass rate (code ran successfully)
    # failure_reason must be None when status="ok" per contract
    return build_scorer_result(
        func_id=func_id,
        task="T3",
        condition=condition,
        model_id=model_id,
        response_ref=response_ref,
        ground_truth_ref=ground_truth_ref,
        score=score,
        status="ok",
        evidence={"passed": passed, "total": total},
    )
