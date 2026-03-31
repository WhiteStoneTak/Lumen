"""Narrow, protocol-first T2 scorer for the Lumen Route A experiment.

Reads the frozen T2 truth layer (t2-bug-v1 artifacts) and produces valid
scorer-result-v1 outputs.

Module structure
----------------
load_t2_scoring_context   - load truth from manifest
extract_t2_claims         - parse model response into structured claims
score_t2_location         - score location (0 or 1)
score_t2_diagnosis        - score diagnosis (0 or 1) with pilot caveats
score_t2_fix              - score fix via test execution (0 or 1)
score_t2                  - main entrypoint
"""

from __future__ import annotations

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
    DEFAULT_MANIFEST_REF,
    FailureReason,
    build_scorer_result,
    get_manifest_item,
    load_dataset_manifest,
    repo_root,
    validate_t2_bug_annotation,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_json_from_repo(path_ref: str) -> dict[str, Any]:
    """Read JSON from a repo-relative path."""
    full = (repo_root() / path_ref).resolve()
    return json.loads(full.read_text(encoding="utf-8"))


def _read_buggy_source(location_path: str) -> str:
    """Return the text of the buggy source file."""
    full = (repo_root() / location_path).resolve()
    return full.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Context loader
# ---------------------------------------------------------------------------

def load_t2_scoring_context(
    scorer_input: dict[str, Any],
    *,
    manifest_ref: str = DEFAULT_MANIFEST_REF,
) -> dict[str, Any]:
    """Load and validate T2 truth from the manifest for *scorer_input*.

    Returns a dict with keys:
        truth       - validated t2-bug-v1 annotation
        buggy_source - text of the buggy source file
        func_id     - str
        manifest_item - the manifest item dict
    """
    func_id: str = scorer_input["func_id"]
    task: str = scorer_input.get("task", "T2")
    if task != "T2":
        raise ContractValidationError(
            f"load_t2_scoring_context called with task='{task}' (expected 'T2')."
        )

    manifest = load_dataset_manifest(manifest_ref, check_paths=True)
    item = get_manifest_item(manifest, func_id)

    task_info = item["tasks"]["T2"]
    if not task_info["available"]:
        raise ContractValidationError(
            f"T2 task is not available for func_id '{func_id}' in manifest."
        )

    gt_ref: str = task_info["ground_truth_ref"]
    truth_payload = _load_json_from_repo(gt_ref)
    truth = validate_t2_bug_annotation(
        truth_payload,
        expected_func_id=func_id,
        expected_source_hash=item["source_hash"],
        check_paths=True,
    )

    buggy_source = _read_buggy_source(truth["location"]["path"])

    return {
        "truth": truth,
        "buggy_source": buggy_source,
        "func_id": func_id,
        "manifest_item": item,
    }


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

def extract_t2_claims(response_text: str) -> dict[str, Any]:
    """Parse a free-form model response and extract T2 claims.

    Returns a dict with keys:
        line_numbers  - list[int]  : all line numbers mentioned
        quoted_code   - list[str]  : code fragments quoted in the response
        diagnosis_text - str       : full response text (for keyword search)
        fix_lines      - list[str] : candidate fix code lines extracted
    """
    text = response_text or ""

    # Extract line numbers (e.g. "line 8", "line 9", "at line 7")
    line_numbers: list[int] = []
    for m in re.finditer(r"\bline\s+(\d+)\b", text, re.IGNORECASE):
        line_numbers.append(int(m.group(1)))
    # Also bare numbers like "#8" or "L8"
    for m in re.finditer(r"(?:^|[^a-z\d])(?:#|L)(\d+)\b", text, re.IGNORECASE):
        line_numbers.append(int(m.group(1)))

    # Extract code fragments from fenced code blocks
    quoted_code: list[str] = []
    for m in re.finditer(r"```(?:[a-z]*)?\n?(.*?)```", text, re.DOTALL):
        for line in m.group(1).splitlines():
            stripped = line.strip()
            if stripped:
                quoted_code.append(stripped)
    # Also backtick-quoted inline snippets
    for m in re.finditer(r"`([^`]+)`", text):
        quoted_code.append(m.group(1).strip())

    # Extract candidate fix lines: lines that look like Python code with
    # comparison operators or assignment, especially inside code blocks.
    fix_lines: list[str] = []
    for m in re.finditer(r"```(?:[a-z]*)?\n?(.*?)```", text, re.DOTALL):
        for line in m.group(1).splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                fix_lines.append(line.rstrip())  # preserve indentation

    # Also look for bare if-statement-like lines in prose (last resort)
    if not fix_lines:
        for line in text.splitlines():
            stripped = line.strip()
            if re.match(
                r"(if\s+.+:|count\s*\+=\s*\d|return\s+\w)",
                stripped,
            ):
                fix_lines.append(line.rstrip())

    return {
        "line_numbers": line_numbers,
        "quoted_code": quoted_code,
        "diagnosis_text": text,
        "fix_lines": fix_lines,
    }


# ---------------------------------------------------------------------------
# Location scorer
# ---------------------------------------------------------------------------

def score_t2_location(claims: dict[str, Any], truth: dict[str, Any]) -> int:
    """Score location (0 or 1).

    Award 1 if:
    - The correct bug line number appears in the response, OR
    - The response quotes the buggy code pattern clearly enough that
      the scorer can identify the right location without a line number.

    Award 0 otherwise.
    """
    start_line: int = truth["location"]["start_line"]
    end_line: int = truth["location"]["end_line"]

    # Check explicit line numbers
    for ln in claims["line_numbers"]:
        if start_line <= ln <= end_line:
            return 1

    # Check if the buggy code pattern is quoted
    func_id: str = truth["func_id"]
    buggy_patterns = _get_buggy_code_patterns(func_id, truth)
    response_lower = claims["diagnosis_text"].lower()

    for pattern in buggy_patterns:
        if pattern.lower() in response_lower:
            return 1

    return 0


def _get_buggy_code_patterns(func_id: str, truth: dict[str, Any]) -> list[str]:
    """Return patterns that identify the buggy line for a given function."""
    if func_id == "clamp":
        # Bug: `value < hi` instead of `value > hi`
        return ["value < hi", "< hi", "value<hi"]
    if func_id == "count_vowels":
        # Bug: `count += 2` instead of `count += 1`
        return ["count += 2", "count+=2", "+= 2"]
    if func_id == "is_sorted":
        # Bug: `>=` instead of `>`
        return [
            "items[i] >= items[i + 1]",
            "items[i] >= items[i+1]",
            ">= items[i",
            ">= items[i + 1]",
        ]
    # Generic fallback: look for anything from the bug description
    return []


# ---------------------------------------------------------------------------
# Diagnosis scorer
# ---------------------------------------------------------------------------

# Diagnosis indicators per function, derived from truth bug_description + fix.
# Each entry is a list of pattern groups; at least one hit per group is needed
# to earn Diagnosis=1. Using a simple "any pattern from any group" approach
# with function-specific logic for the known pilot caveats.

_CLAMP_DIAGNOSIS_PATTERNS: list[str] = [
    # Core: identifies wrong comparison operator at hi guard
    r"\bvalue\s*<\s*hi\b",
    r"<\s*hi\b",
    r"wrong\s+(?:comparison|operator)",
    r"incorrect\s+(?:comparison|operator)",
    r"should\s+be\s+(?:value\s+)?>",
    r"\bvalue\s*>\s*hi\b",        # mentions correct form
    r">`.*`hi",
    r"`?\bvalue\s*<\s*hi`?",
    r"less\s+than\s+hi",
    r"upper.{0,20}(?:guard|bound|clamp).{0,20}(?:<|less)",
    r"(?:<|less).{0,20}(?:upper|hi|high|bound)",
    r"value < hi instead of value > hi",
    r"value < hi.*value > hi",
    r"value > hi.*correct",
    r"< hi.*> hi",
]

_COUNT_VOWELS_DIAGNOSIS_PATTERNS: list[str] = [
    # Core: identifies increment of 2 instead of 1
    # NOTE: must NOT require "off by one" — see pilot caveat
    r"\bcount\s*\+=\s*2\b",
    r"\+= 2\b",
    r"\bincrement.{0,30}\b2\b",
    r"\badd.{0,20}\b2\b",
    r"\bdouble",
    r"\bdoubl",
    r"\btwice\b",
    r"\b2 instead of 1\b",
    r"\binstead of 1\b",
    r"\bshould be 1\b",
    r"\bshould increment by 1\b",
    r"\bby 2\b",
    r"\badds 2\b",
    r"\bincrements.{0,15}2\b",
    r"\bcount \+= 2",
]

_IS_SORTED_DIAGNOSIS_PATTERNS: list[str] = [
    # Core: identifies >= instead of >
    r"\b>=\b",
    r"\bgreater.{0,10}than.{0,10}or.{0,10}equal\b",
    r"\bequal.{0,20}element",
    r"\bequal.{0,20}adjacent",
    r"\badjacent.{0,20}equal",
    r"\bduplicate.{0,20}element",
    r"\b>= instead of >\b",
    r"\bshould be >\b",
    r"\bshould use >\b",
    r"\bonly >\b",
    r"\bstrict.{0,15}greater",
    r"items\[i\]\s*>=",
    r"`>= `",
    r"wrong.{0,15}operator",
    r"incorrect.{0,15}operator",
    r"\bsorted.*equal.*false",
    r"\bequal.*sorted.*false",
]

_DIAGNOSIS_PATTERNS: dict[str, list[str]] = {
    "clamp": _CLAMP_DIAGNOSIS_PATTERNS,
    "count_vowels": _COUNT_VOWELS_DIAGNOSIS_PATTERNS,
    "is_sorted": _IS_SORTED_DIAGNOSIS_PATTERNS,
}


def score_t2_diagnosis(claims: dict[str, Any], truth: dict[str, Any]) -> int:
    """Score diagnosis (0 or 1).

    Uses keyword matching focused on the actual bug content. Explicitly handles
    the pilot caveats:
    - count_vowels: does NOT require "off by one" — accepts "increments by 2" etc.
    - clamp: does NOT require exact match to bug_description text.
    """
    func_id: str = truth["func_id"]
    patterns = _DIAGNOSIS_PATTERNS.get(func_id)

    if patterns is None:
        # Fallback for unknown functions: check against bug_category label and
        # key phrases from bug_description.
        return _score_diagnosis_generic(claims, truth)

    text = claims["diagnosis_text"]
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return 1

    return 0


def _score_diagnosis_generic(claims: dict[str, Any], truth: dict[str, Any]) -> int:
    """Generic diagnosis scoring for functions not in the pilot set."""
    bug_category: str = truth["bug_category"]
    bug_description: str = truth.get("bug_description", "")
    text: str = claims["diagnosis_text"]

    # Check the canonical category label (allow word-boundary matches)
    category_words = bug_category.replace("_", " ").split()
    if all(w.lower() in text.lower() for w in category_words):
        return 1

    # Extract the first ~10 words of bug_description and check for overlap
    description_words = bug_description.lower().split()[:10]
    hits = sum(1 for w in description_words if len(w) > 3 and w in text.lower())
    if hits >= 3:
        return 1

    return 0


# ---------------------------------------------------------------------------
# Fix scorer
# ---------------------------------------------------------------------------

def _apply_fix_to_source(
    buggy_source: str,
    reference_fix: dict[str, Any],
    model_fix_line: str,
) -> str:
    """Apply model's fix to the buggy source at the reference_fix line span.

    reference_fix uses 1-based inclusive line numbers.

    If the model_fix_line has no leading whitespace but the original buggy line
    does, the original indentation is preserved so the patched source remains
    syntactically valid Python.
    """
    lines = buggy_source.splitlines(keepends=True)
    start = reference_fix["start_line"] - 1   # 0-indexed
    end = reference_fix["end_line"]            # exclusive (1-indexed end + 1 - 1 = end)

    if "\n" in model_fix_line:
        # Multi-line fix: the caller has already produced correctly indented lines.
        # Apply them all verbatim without single-line re-indentation.
        fix_parts = model_fix_line.rstrip("\n").split("\n")
        replacement_lines = [p + "\n" for p in fix_parts]
        fixed_lines = lines[:start] + replacement_lines + lines[end:]
        return "".join(fixed_lines)

    # Normalize indentation: strip any leading whitespace the model may have
    # included in its fix snippet and re-apply the exact indentation of the
    # original buggy line.  This makes the patched source syntactically valid
    # regardless of whether the model used 0, 3, or any other indent width.
    original_line = lines[start] if start < len(lines) else ""
    original_indent = len(original_line) - len(original_line.lstrip())
    fix_stripped = model_fix_line.lstrip()
    if original_indent > 0:
        model_fix_line = " " * original_indent + fix_stripped

    # Preserve the trailing newline on the replacement line
    replacement = model_fix_line.rstrip("\n") + "\n"
    fixed_lines = lines[:start] + [replacement] + lines[end:]
    return "".join(fixed_lines)


def _run_tests_against_patched_source(
    patched_source: str,
    func_id: str,
    test_suite_ref: str,
) -> tuple[bool, str]:
    """Load patched function and run the T2 test suite.

    Returns (passed: bool, failure_detail: str).

    The test files load source via ``_load_func(_SOURCE)`` at module import
    time. We load the patched function from a temp file, then load the test
    module fresh and monkey-patch ``func_id`` in it before running.
    """
    # Write patched source to a temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(patched_source)
        tmp_path = f.name

    try:
        # Load function from temp file
        spec = importlib.util.spec_from_file_location(f"_patched_{func_id}", tmp_path)
        if spec is None or spec.loader is None:
            return False, "could not create module spec from temp file"
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        patched_fn = getattr(mod, func_id, None)
        if patched_fn is None:
            return False, f"patched module has no attribute '{func_id}'"

        # Load test module fresh (use a unique name to avoid caching)
        test_path = (repo_root() / test_suite_ref).resolve()
        unique_name = f"_t2_test_{func_id}_{os.getpid()}"
        test_spec = importlib.util.spec_from_file_location(unique_name, test_path)
        if test_spec is None or test_spec.loader is None:
            return False, f"could not load test module from {test_suite_ref}"
        test_mod = importlib.util.module_from_spec(test_spec)
        # Execute the test module (this will call _load_func(_SOURCE) internally,
        # loading the default correct source — we then overwrite it below)
        test_spec.loader.exec_module(test_mod)  # type: ignore[union-attr]

        # Monkey-patch the function the test module is using
        setattr(test_mod, func_id, patched_fn)
        # Also patch the module-level variable in all test class methods'
        # globals (they close over the module namespace via the class body)
        for attr_name in dir(test_mod):
            obj = getattr(test_mod, attr_name)
            if isinstance(obj, type) and issubclass(obj, unittest.TestCase):
                obj_dict = obj.__dict__
                # Patch test method globals that reference the function
                for method_name in obj_dict:
                    method = getattr(obj, method_name, None)
                    if callable(method) and hasattr(method, "__func__"):
                        # Replace in the function's global scope
                        if func_id in method.__func__.__globals__:
                            method.__func__.__globals__[func_id] = patched_fn

        # Run tests
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_mod)
        buf = io.StringIO()
        runner = unittest.TextTestRunner(verbosity=0, stream=buf, failfast=False)
        result = runner.run(suite)

        if result.wasSuccessful():
            return True, ""
        else:
            failures = [str(tc) for tc, _ in result.failures + result.errors]
            return (
                False,
                f"{len(result.failures)} failure(s), {len(result.errors)} error(s): "
                f"{failures[:3]}",
            )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _extract_best_fix_line(
    claims: dict[str, Any],
    truth: dict[str, Any],
) -> str | None:
    """Extract the best candidate fix line from the claims.

    Priority:
    1. Code block lines that match the reference_fix line style
    2. Any code block lines that look like the fix pattern
    3. None if nothing usable found
    """
    fix_lines = claims["fix_lines"]
    if not fix_lines:
        return None

    reference_replacement: str = truth["reference_fix"]["replacement"]

    # Try to find a line that looks semantically similar to the reference fix
    ref_stripped = reference_replacement.strip()

    # Exact match first
    for line in fix_lines:
        if line.strip() == ref_stripped:
            return line

    func_id: str = truth["func_id"]

    if func_id == "clamp":
        # Looking for `if value > hi:` (or equivalent)
        for line in fix_lines:
            stripped = line.strip()
            if re.search(r"if\s+value\s*>\s*hi\s*:", stripped):
                return line
        # Also accept anything with `value > hi`
        for line in fix_lines:
            if re.search(r"value\s*>\s*hi", line):
                return line

    elif func_id == "count_vowels":
        # Looking for `count += 1`
        for line in fix_lines:
            stripped = line.strip()
            if re.search(r"count\s*\+=\s*1\b", stripped):
                return line

    elif func_id == "is_sorted":
        # Looking for `if items[i] > items[i + 1]:`
        for line in fix_lines:
            stripped = line.strip()
            if re.search(r"if\s+items\[i\]\s*>\s*items\[i\s*\+\s*1\]\s*:", stripped):
                return line
        # Also accept `items[i] > items[i + 1]` without requiring full if statement
        for line in fix_lines:
            if re.search(r"items\[i\]\s*>\s*items\[i", line):
                return line

    elif func_id == "count_true_segments":
        # The fix requires replacing the entire for-loop block (for header + if/elif body).
        # Look for the model's proposed fix block which starts with `for flag in flags:`.
        # The model typically shows the loop at base indent inside a code fence; we
        # re-indent each line by +4 spaces to match the actual function-body context.
        for i, line in enumerate(fix_lines):
            if re.search(r"for\s+flag\s+in\s+flags\s*:", line.strip()):
                base_indent = len(line) - len(line.lstrip())
                block: list[str] = [line]
                for subsequent in fix_lines[i + 1:]:
                    if not subsequent.strip():
                        break
                    subsequent_indent = len(subsequent) - len(subsequent.lstrip())
                    if subsequent_indent <= base_indent:
                        break
                    block.append(subsequent)
                if len(block) >= 2:
                    # Re-indent by +4 to place the for loop in function-body context
                    reindented = ["    " + ln for ln in block]
                    return "\n".join(reindented)

    # Generic fallback: return first non-trivial code block line
    for line in fix_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return line

    return None


def score_t2_fix(
    claims: dict[str, Any],
    truth: dict[str, Any],
    buggy_source: str,
) -> tuple[int, str]:
    """Score fix (0 or 1) via test execution.

    Returns (score: int, detail: str).
    """
    model_fix_line = _extract_best_fix_line(claims, truth)
    if model_fix_line is None:
        return 0, "no_fix_found: no candidate fix line extracted from response"

    patched_source = _apply_fix_to_source(buggy_source, truth["reference_fix"], model_fix_line)

    passed, failure_detail = _run_tests_against_patched_source(
        patched_source,
        func_id=truth["func_id"],
        test_suite_ref=truth["test_suite_ref"],
    )

    if passed:
        return 1, ""
    else:
        return 0, f"test_failure: {failure_detail}"


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def score_t2(
    scorer_input_payload: dict[str, Any],
    response_text: str,
) -> dict[str, Any]:
    """Score a T2 response and return a valid scorer-result-v1 dict.

    Parameters
    ----------
    scorer_input_payload:
        A scorer-input-v1 dict (must include func_id, task='T2', condition,
        model_id, response_ref, ground_truth_ref).
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

    # resolve ground_truth_ref from scorer_input if present, else derive from manifest
    ground_truth_ref: str = scorer_input_payload.get("ground_truth_ref", "")
    if not ground_truth_ref:
        # Load from manifest
        manifest_ref = scorer_input_payload.get("manifest_ref", DEFAULT_MANIFEST_REF)
        try:
            manifest = load_dataset_manifest(manifest_ref, check_paths=True)
            item = get_manifest_item(manifest, func_id)
            ground_truth_ref = item["tasks"]["T2"]["ground_truth_ref"]
        except ContractValidationError as exc:
            return build_scorer_result(
                func_id=func_id or "unknown",
                task="T2",
                condition=condition or "C1",
                model_id=model_id or "unknown",
                response_ref=response_ref or "unknown",
                ground_truth_ref="unknown",
                score=0.0,
                status="scoring_error",
                subscores={"location": 0, "diagnosis": 0, "fix": 0},
                failure_reason=FailureReason(
                    code="manifest_error",
                    message=str(exc),
                ),
            )

    # Load scoring context
    try:
        context = load_t2_scoring_context(
            scorer_input_payload,
            manifest_ref=scorer_input_payload.get("manifest_ref", DEFAULT_MANIFEST_REF),
        )
    except ContractValidationError as exc:
        return build_scorer_result(
            func_id=func_id or "unknown",
            task="T2",
            condition=condition or "C1",
            model_id=model_id or "unknown",
            response_ref=response_ref or "unknown",
            ground_truth_ref=ground_truth_ref or "unknown",
            score=0.0,
            status="scoring_error",
            subscores={"location": 0, "diagnosis": 0, "fix": 0},
            failure_reason=FailureReason(
                code="context_load_error",
                message=str(exc),
            ),
        )

    truth = context["truth"]
    buggy_source = context["buggy_source"]

    # Parse response
    claims = extract_t2_claims(response_text)

    # Sub-scores
    loc_score = score_t2_location(claims, truth)
    diag_score = score_t2_diagnosis(claims, truth)
    fix_score, fix_detail = score_t2_fix(claims, truth, buggy_source)

    composite = loc_score + diag_score + fix_score
    subscores = {
        "location": loc_score,
        "diagnosis": diag_score,
        "fix": fix_score,
    }

    # Build evidence
    evidence: dict[str, Any] = {
        "line_numbers_found": claims["line_numbers"],
        "quoted_code_snippets": claims["quoted_code"][:5],  # trim for storage
        "fix_lines_tried": [_extract_best_fix_line(claims, truth)],
    }
    if fix_detail:
        evidence["fix_failure_detail"] = fix_detail

    # Determine status
    if fix_detail and fix_detail.startswith("no_fix_found"):
        status = "parse_failure"
        failure_reason: FailureReason | None = FailureReason(
            code="no_fix_found",
            message="No candidate fix line could be extracted from the response.",
        )
    elif fix_detail and fix_detail.startswith("test_failure"):
        status = "execution_failure"
        failure_reason = FailureReason(
            code="fix_test_failure",
            message=fix_detail,
        )
    else:
        status = "ok"
        failure_reason = None

    # For T2 the composite score must still be the sum; partial failures
    # (parse_failure on fix) still allow location/diagnosis points.
    # Only use "ok" if all three sub-scorers completed without infrastructure
    # errors. If fix was 0 due to bad code (test_failure), that's still "ok"
    # from a scorer perspective — the model simply didn't produce a passing fix.
    # However if there was no fix to attempt at all, status = parse_failure.
    if fix_score == 0 and fix_detail and fix_detail.startswith("test_failure"):
        # Tests ran but failed — scorer ran correctly
        status = "ok"
        failure_reason = None

    return build_scorer_result(
        func_id=func_id,
        task="T2",
        condition=condition,
        model_id=model_id,
        response_ref=response_ref,
        ground_truth_ref=ground_truth_ref,
        score=float(composite),
        status=status,
        subscores=subscores,
        failure_reason=failure_reason,
        evidence=evidence,
    )
