"""Protocol-first deterministic T1 checklist scorer for Lumen Route A.

T1 scores a model's ability to identify and correctly describe properties of a
function (inputs, outputs, behavior, edge cases). The score is the fraction of
checklist properties that are clearly identified in the response.

Scoring shape:
  score = matched_properties / total_properties  ∈ [0.0, 1.0]

Matching is deterministic keyword/phrase-based — no external model is used.
Each property is scored 0 or 1 based on key term presence in the normalized
response, with simple negation detection to avoid false positives.

See: docs/experiment-dataset-contracts.md §2 T1, docs/experimental-protocol.md §4.6
"""

from __future__ import annotations

import json
import re
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
    validate_t1_checklist,
)

# ── failure-reason codes ────────────────────────────────────────────────────

FR_MISSING_RESPONSE = "missing_response_text"
FR_EMPTY_RESPONSE = "empty_response"
FR_SCORING_ERROR = "scoring_error"

# Words to exclude when extracting key terms from property statements.
# Kept conservative: we want to preserve domain terms (float, int, bool,
# str, list, value, lo, hi, items, etc.).
_STOP_WORDS: frozenset[str] = frozenset({
    "the", "a", "an", "of", "in", "is", "it", "to", "be", "as", "at",
    "by", "or", "if", "on", "up", "so", "do", "my", "we", "he", "she",
    "they", "that", "this", "with", "from", "have", "has", "had", "are",
    "was", "were", "will", "can", "may", "all", "any", "but", "not",
    "and", "for", "its", "his", "her", "our", "you", "your",
    "each", "both", "only", "also", "must", "does", "when", "what",
    "which", "where", "how", "than", "more", "less", "such", "been",
    "being", "into", "onto", "over", "under", "about", "after",
    "before", "since", "while", "should", "would", "could", "might",
    "just", "then", "them", "their", "these", "those", "some", "same",
    "make", "made", "take", "taken", "give", "given", "however",
    "always", "never", "either", "neither", "whether",
    # common prose filler
    "function", "parameter", "parameters",
})

# Negation indicators for contradiction detection.
# NOTE: "false" is intentionally excluded — it frequently appears as a
# legitimate return value description (e.g., "Returns False if …") and
# would create false positives in negation detection.
_NEGATION_WORDS: tuple[str, ...] = (
    "not ", "never", "incorrect", "wrong", "doesn't", "does not",
    "cannot", "can't", "isn't", "aren't", "wasn't", "weren't",
    "inaccurate", "untrue",
)


# ---------------------------------------------------------------------------
# Key term extraction
# ---------------------------------------------------------------------------

def _extract_key_terms(statement: str) -> list[str]:
    """Extract meaningful key terms from a property statement.

    Returns lower-cased tokens that carry semantic weight: numbers,
    parameter names, type names, domain vocabulary. Filters stop words.
    Minimum token length: 2 chars (to keep short but meaningful terms
    like 'lo', 'hi', 'or').
    """
    normalized = statement.lower()
    # Keep alphanumerics and underscores; map other chars to space
    normalized = re.sub(r'[^a-z0-9_ ]', ' ', normalized)
    tokens = normalized.split()

    # Filter: remove stop words, keep length >= 2
    key_terms = [t for t in tokens if len(t) >= 2 and t not in _STOP_WORDS]

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for t in key_terms:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


# ---------------------------------------------------------------------------
# Negation detection
# ---------------------------------------------------------------------------

def _has_nearby_negation(term: str, normalized_response: str) -> bool:
    """Return True if a negation word appears within ~2-3 words directly before `term`.

    Uses a tight 15-char window to avoid false positives where a "not" in one
    part of the response bleeds into negation detection for an unrelated term
    elsewhere in the same response (e.g., "is not enforced" should not suppress
    a later match on "lo" 40+ chars away).

    Term positions are located at word boundaries to avoid substring matches.
    """
    pattern = re.compile(r'\b' + re.escape(term) + r'\b')
    for m in pattern.finditer(normalized_response):
        pos = m.start()
        # Extract up to 15 chars before the term (~2-3 words)
        context = normalized_response[max(0, pos - 15):pos]
        for neg in _NEGATION_WORDS:
            if neg in context:
                return True
    return False


# ---------------------------------------------------------------------------
# Per-property scorer
# ---------------------------------------------------------------------------

def score_t1_property(
    property_dict: dict[str, Any],
    normalized_response: str,
) -> dict[str, Any]:
    """Score one T1 checklist property against a normalized model response.

    Returns a dict with:
      - matched: 0 or 1
      - evidence: key terms found in the response (list[str])
      - note: reason for decision (for audit)
    """
    statement = property_dict.get("statement", "")
    key_terms = _extract_key_terms(statement)

    if not key_terms:
        return {
            "matched": 0,
            "evidence": [],
            "note": "No key terms extractable from statement",
        }

    # Find which key terms appear in the response.
    # Use word-boundary matching to prevent short tokens like "lo" or "hi"
    # from matching inside longer words (e.g., "float", "this", "which").
    found_terms = [
        t for t in key_terms
        if re.search(r'\b' + re.escape(t) + r'\b', normalized_response)
    ]

    # Require at least 2 key terms to match (or all key terms if <= 2 available)
    min_required = min(2, len(key_terms))

    if len(found_terms) < min_required:
        return {
            "matched": 0,
            "evidence": found_terms,
            "note": (
                f"Only {len(found_terms)}/{len(key_terms)} key terms found "
                f"(need {min_required})"
            ),
        }

    # Check for negation around the primary matching terms (first 2 found)
    primary_terms = found_terms[:2]
    for term in primary_terms:
        if _has_nearby_negation(term, normalized_response):
            return {
                "matched": 0,
                "evidence": found_terms,
                "note": f"Negation detected near matched term '{term}'",
            }

    return {
        "matched": 1,
        "evidence": found_terms,
        "note": f"Matched {len(found_terms)}/{len(key_terms)} key terms",
    }


# ---------------------------------------------------------------------------
# Response normalization
# ---------------------------------------------------------------------------

def normalize_t1_response(response_text: str) -> str:
    """Normalize a model's T1 response for property matching.

    Applies: lowercase, whitespace collapse, light punctuation stripping.
    Preserves: numbers, operators, code-like terms.
    Does NOT: paraphrase, summarize, or semantically rewrite.
    """
    text = response_text.lower()
    # Replace common punctuation that doesn't carry semantic weight.
    # Keep: alphanumerics, spaces, =, <, >, !, ?, -, _, .
    text = re.sub(r'[^\w\s=<>!?\-_.]', ' ', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ---------------------------------------------------------------------------
# Context loader
# ---------------------------------------------------------------------------

def load_t1_scoring_context(scorer_input: dict[str, Any]) -> dict[str, Any]:
    """Load and validate T1 scoring context from scorer input.

    Returns a dict with keys:
        truth            - validated t1-checklist-v1 dict
        func_id          - str
        ground_truth_ref - repo-relative path str
    """
    normalized = validate_scorer_input(scorer_input, check_paths=False)
    func_id = normalized["func_id"]
    task_id = normalized["task"]
    if task_id != "T1":
        raise ContractValidationError(
            f"score_t1_checklist requires task=T1, got {task_id!r}"
        )

    manifest = load_dataset_manifest(check_paths=True)
    item = get_manifest_item(manifest, func_id)

    task_info = item["tasks"]["T1"]
    if not task_info["available"]:
        raise ContractValidationError(f"T1 is not available for {func_id!r}")

    gt_ref = task_info["ground_truth_ref"]
    gt_path = (repo_root() / gt_ref).resolve()
    truth_raw = json.loads(gt_path.read_text(encoding="utf-8"))
    truth = validate_t1_checklist(truth_raw, expected_func_id=func_id)

    return {
        "truth": truth,
        "func_id": func_id,
        "ground_truth_ref": gt_ref,
    }


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def score_t1_checklist(
    scorer_input_payload: dict[str, Any],
    response_text: str,
) -> dict[str, Any]:
    """Score a T1 model response and return a validated scorer-result-v1 dict.

    Parameters
    ----------
    scorer_input_payload:
        A scorer-input-v1 dict (must include func_id, task='T1', condition,
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
        ctx = load_t1_scoring_context(scorer_input_payload)
    except ContractValidationError as exc:
        return build_scorer_result(
            func_id=func_id or "unknown",
            task="T1",
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
    ground_truth_ref = ctx["ground_truth_ref"]

    # Handle missing/non-string response
    if not isinstance(response_text, str):
        return build_scorer_result(
            func_id=func_id,
            task="T1",
            condition=condition,
            model_id=model_id,
            response_ref=response_ref,
            ground_truth_ref=ground_truth_ref,
            score=0.0,
            status="invalid_response",
            failure_reason=FailureReason(
                code=FR_MISSING_RESPONSE,
                message="Response text is missing or not a string",
            ),
            evidence={},
        )

    stripped = response_text.strip()
    if not stripped:
        return build_scorer_result(
            func_id=func_id,
            task="T1",
            condition=condition,
            model_id=model_id,
            response_ref=response_ref,
            ground_truth_ref=ground_truth_ref,
            score=0.0,
            status="invalid_response",
            failure_reason=FailureReason(
                code=FR_EMPTY_RESPONSE,
                message="Response text is empty",
            ),
            evidence={},
        )

    # Normalize response for matching
    normalized = normalize_t1_response(stripped)

    # Score each property
    properties = truth.get("properties", [])
    total = len(properties)

    if total == 0:
        return build_scorer_result(
            func_id=func_id,
            task="T1",
            condition=condition,
            model_id=model_id,
            response_ref=response_ref,
            ground_truth_ref=ground_truth_ref,
            score=0.0,
            status="scoring_error",
            failure_reason=FailureReason(
                code=FR_SCORING_ERROR,
                message="T1 checklist has no properties",
            ),
            evidence={},
        )

    property_results: list[dict[str, Any]] = []
    matched_count = 0

    for prop in properties:
        result = score_t1_property(prop, normalized)
        matched_count += result["matched"]
        property_results.append({
            "property_id": prop["property_id"],
            "category": prop["category"],
            "required": prop["required"],
            "matched": result["matched"],
            "evidence": result["evidence"],
            "note": result["note"],
        })

    score = matched_count / total

    evidence: dict[str, Any] = {
        "matched": matched_count,
        "total": total,
        "properties": property_results,
    }

    # status="ok" for any score when scoring ran successfully.
    # Invalid responses were handled above; failure_reason must be None with status="ok".
    return build_scorer_result(
        func_id=func_id,
        task="T1",
        condition=condition,
        model_id=model_id,
        response_ref=response_ref,
        ground_truth_ref=ground_truth_ref,
        score=score,
        status="ok",
        evidence=evidence,
    )
