"""Candidate function tracker for Lumen dataset expansion.

Manages data/dataset/candidates.json — a flat-file tracker for candidate
functions undergoing staged screening before truth authoring begins.

Stage flow (enforced here):
  Stage 0/1  manual: researcher assigns stage1_result (PASS / EXCLUDE / DEFER)
  Stage 2    automated: T2 C1 screening — the primary difficulty gate
  Stage 3    automated, advisory: T3 C2 screening
  final_decision: INCLUDE / EXCLUDE / DEFER

Stage 2 decision rules (from the expanded dataset spec):
  score = 3.0        -> EXCLUDE  (too easy: frontier model trivially solves on raw source)
  score = 2.0 – 2.9  -> INCLUDE
  score = 1.0 – 1.9  -> INCLUDE  (high-priority: harder)
  score < 1.0 (= 0)  -> DEFER   (may be malformed rather than hard; re-examine)

Stage 3 decision rules (advisory):
  score = 1.0 on C2  -> ceiling_risk  (T3 easy even from AST-only)
  score < 1.0 on C2  -> preferred     (representation-dependent difficulty)

Anchor policy:
  The three pilot functions (clamp, count_vowels, is_sorted) are calibration
  anchors.  Their final_decision stays INCLUDE regardless of stage2_result.
  is_anchor=True may only be set for those three IDs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "candidate-tracker-v1"

ANCHOR_IDS: frozenset[str] = frozenset({"clamp", "count_vowels", "is_sorted"})

COMPLEXITY_VALUES: frozenset[str] = frozenset({"trivial", "low", "medium", "high"})
STAGE1_VALUES: frozenset[str] = frozenset({"PASS", "EXCLUDE", "DEFER"})
STAGE2_VALUES: frozenset[str] = frozenset({"INCLUDE", "EXCLUDE", "DEFER", "not_run"})
STAGE3_VALUES: frozenset[str] = frozenset(
    {"preferred", "acceptable", "ceiling_risk", "not_run"}
)
FINAL_DECISION_VALUES: frozenset[str] = frozenset({"INCLUDE", "EXCLUDE", "DEFER"})

REQUIRED_FIELDS: tuple[str, ...] = (
    "candidate_id",
    "source",
    "body_line_count",
    "estimated_complexity",
    "t2_bug_family_draft",
    "t3_transform_family_draft",
    "stage1_result",
    "stage1_exclusion_reason",
    "stage2_t2_c1_screen_score",
    "stage2_t2_subscores",
    "stage2_result",
    "stage2_exclusion_reason",
    "stage3_t3_c2_screen_score",
    "stage3_result",
    "final_decision",
    "is_anchor",
    "notes",
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TrackerError(ValueError):
    """Raised when the tracker is in an inconsistent or invalid state."""


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_tracker_path() -> Path:
    return _repo_root() / "data" / "dataset" / "candidates.json"


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------


def load_tracker(path: Path | str | None = None) -> dict[str, Any]:
    """Load and return the tracker dict.  Raises TrackerError on any problem."""
    p = Path(path) if path else default_tracker_path()
    if not p.exists():
        raise TrackerError(f"Tracker file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TrackerError(f"Tracker file is not valid JSON ({p}): {exc}") from exc
    if data.get("lumen_schema") != SCHEMA_VERSION:
        raise TrackerError(
            f"Unexpected tracker schema '{data.get('lumen_schema')}'; "
            f"expected '{SCHEMA_VERSION}'"
        )
    return data


def save_tracker(data: dict[str, Any], path: Path | str | None = None) -> None:
    """Validate *data* then write it to disk as formatted JSON."""
    p = Path(path) if path else default_tracker_path()
    validate_tracker(data)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def empty_tracker() -> dict[str, Any]:
    """Return a valid, empty tracker dict."""
    return {"lumen_schema": SCHEMA_VERSION, "candidates": []}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_candidate(row: dict[str, Any]) -> None:
    """Raise TrackerError if *row* violates the schema or business rules."""
    cid = row.get("candidate_id", "<missing>")

    # --- Required fields present -----------------------------------------
    for field in REQUIRED_FIELDS:
        if field not in row:
            raise TrackerError(f"[{cid}] missing required field: {field!r}")

    # --- Enum checks -------------------------------------------------------
    if row["estimated_complexity"] not in COMPLEXITY_VALUES:
        raise TrackerError(
            f"[{cid}] invalid estimated_complexity: {row['estimated_complexity']!r}; "
            f"allowed: {sorted(COMPLEXITY_VALUES)}"
        )
    if row["stage1_result"] not in STAGE1_VALUES:
        raise TrackerError(
            f"[{cid}] invalid stage1_result: {row['stage1_result']!r}; "
            f"allowed: {sorted(STAGE1_VALUES)}"
        )
    if row["stage2_result"] not in STAGE2_VALUES:
        raise TrackerError(
            f"[{cid}] invalid stage2_result: {row['stage2_result']!r}; "
            f"allowed: {sorted(STAGE2_VALUES)}"
        )
    if row["stage3_result"] not in STAGE3_VALUES:
        raise TrackerError(
            f"[{cid}] invalid stage3_result: {row['stage3_result']!r}; "
            f"allowed: {sorted(STAGE3_VALUES)}"
        )
    if row["final_decision"] not in FINAL_DECISION_VALUES:
        raise TrackerError(
            f"[{cid}] invalid final_decision: {row['final_decision']!r}; "
            f"allowed: {sorted(FINAL_DECISION_VALUES)}"
        )

    # --- Anchor policy: is_anchor only for designated IDs ------------------
    if row["is_anchor"] and cid not in ANCHOR_IDS:
        raise TrackerError(
            f"[{cid}] is_anchor=True but '{cid}' is not a designated anchor "
            f"(anchors: {sorted(ANCHOR_IDS)})"
        )

    # --- Stage gate: Stage 2 requires Stage 1 PASS -------------------------
    if row["stage2_result"] != "not_run" and row["stage1_result"] != "PASS":
        raise TrackerError(
            f"[{cid}] stage2_result='{row['stage2_result']}' but "
            f"stage1_result='{row['stage1_result']}' "
            "(Stage 2 requires Stage 1 PASS)"
        )

    # --- Stage gate: Stage 3 only after Stage 2 INCLUDE (for non-anchors) --
    if (
        row["stage3_result"] != "not_run"
        and row["stage2_result"] not in {"INCLUDE", "not_run"}
        and not row["is_anchor"]
    ):
        raise TrackerError(
            f"[{cid}] stage3_result='{row['stage3_result']}' but "
            f"stage2_result='{row['stage2_result']}' "
            "(Stage 3 is advisory; only run after Stage 2 INCLUDE)"
        )

    # --- final_decision consistency ----------------------------------------
    if row["final_decision"] == "INCLUDE":
        if row["stage1_result"] != "PASS":
            raise TrackerError(
                f"[{cid}] final_decision=INCLUDE but stage1_result='{row['stage1_result']}'"
            )
        # Non-anchors: INCLUDE requires stage2 INCLUDE or not_run (not yet screened)
        if (
            not row["is_anchor"]
            and row["stage2_result"] not in {"INCLUDE", "not_run"}
        ):
            raise TrackerError(
                f"[{cid}] final_decision=INCLUDE but stage2_result='{row['stage2_result']}' "
                "(only designated anchors may override a Stage 2 EXCLUDE)"
            )

    # --- Null consistency for Stage 2 fields --------------------------------
    if row["stage2_result"] == "not_run":
        if row["stage2_t2_c1_screen_score"] is not None:
            raise TrackerError(
                f"[{cid}] stage2_t2_c1_screen_score is set but stage2_result='not_run'"
            )
        if row["stage2_t2_subscores"] is not None:
            raise TrackerError(
                f"[{cid}] stage2_t2_subscores is set but stage2_result='not_run'"
            )
    else:
        if not isinstance(row["stage2_t2_c1_screen_score"], (int, float)):
            raise TrackerError(
                f"[{cid}] stage2_result='{row['stage2_result']}' but "
                "stage2_t2_c1_screen_score is not a number"
            )
        if not isinstance(row["stage2_t2_subscores"], dict):
            raise TrackerError(
                f"[{cid}] stage2_result='{row['stage2_result']}' but "
                "stage2_t2_subscores is not a dict"
            )

    # --- Null consistency for Stage 3 fields --------------------------------
    if row["stage3_result"] == "not_run":
        if row["stage3_t3_c2_screen_score"] is not None:
            raise TrackerError(
                f"[{cid}] stage3_t3_c2_screen_score is set but stage3_result='not_run'"
            )
    else:
        if not isinstance(row["stage3_t3_c2_screen_score"], (int, float)):
            raise TrackerError(
                f"[{cid}] stage3_result='{row['stage3_result']}' but "
                "stage3_t3_c2_screen_score is not a number"
            )


def validate_tracker(data: dict[str, Any]) -> None:
    """Validate the full tracker dict: schema, uniqueness, and every row."""
    if data.get("lumen_schema") != SCHEMA_VERSION:
        raise TrackerError(
            f"Unexpected tracker schema: '{data.get('lumen_schema')}'"
        )
    if "candidates" not in data:
        raise TrackerError("Tracker missing 'candidates' list")
    if not isinstance(data["candidates"], list):
        raise TrackerError("'candidates' must be a list")

    seen_ids: set[str] = set()
    for row in data["candidates"]:
        cid = row.get("candidate_id", "<missing>")
        if cid in seen_ids:
            raise TrackerError(f"Duplicate candidate_id: {cid!r}")
        seen_ids.add(cid)
        validate_candidate(row)


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


def get_candidate(
    data: dict[str, Any], candidate_id: str
) -> dict[str, Any] | None:
    """Return the row matching *candidate_id*, or None if not found."""
    for row in data["candidates"]:
        if row["candidate_id"] == candidate_id:
            return row
    return None


def upsert_candidate(data: dict[str, Any], new_row: dict[str, Any]) -> None:
    """Add or replace a candidate row.  Validates the row before writing.

    If a row with the same candidate_id already exists, it is replaced in-place.
    Otherwise the new row is appended.
    """
    validate_candidate(new_row)
    cid = new_row["candidate_id"]
    for i, row in enumerate(data["candidates"]):
        if row["candidate_id"] == cid:
            data["candidates"][i] = new_row
            return
    data["candidates"].append(new_row)


# ---------------------------------------------------------------------------
# Stage 2 application
# ---------------------------------------------------------------------------


def stage2_decision_from_score(score: float) -> str:
    """Return the Stage 2 decision string for a given T2 C1 composite score.

    Rules (from expanded dataset spec):
      score >= 3.0  -> EXCLUDE
      score >= 1.0  -> INCLUDE
      score < 1.0   -> DEFER
    """
    if score >= 3.0:
        return "EXCLUDE"
    if score >= 1.0:
        return "INCLUDE"
    return "DEFER"


def apply_stage2_result(
    row: dict[str, Any],
    score: float,
    subscores: dict[str, int],
    exclusion_reason: str | None = None,
) -> None:
    """Update *row* in-place with Stage 2 T2 C1 screening results.

    Raises TrackerError if the row is not eligible (stage1_result != PASS).
    For non-anchor rows: also updates final_decision to match the Stage 2
    decision (INCLUDE or EXCLUDE).  DEFER leaves final_decision unchanged
    for the researcher to resolve manually.
    For anchor rows: final_decision is always kept as INCLUDE.
    """
    cid = row.get("candidate_id", "<missing>")
    if row["stage1_result"] != "PASS":
        raise TrackerError(
            f"[{cid}] Cannot apply Stage 2 result: "
            f"stage1_result='{row['stage1_result']}' (requires PASS)"
        )

    decision = stage2_decision_from_score(score)
    row["stage2_t2_c1_screen_score"] = score
    row["stage2_t2_subscores"] = dict(subscores)
    row["stage2_result"] = decision

    if decision == "EXCLUDE":
        row["stage2_exclusion_reason"] = (
            exclusion_reason
            or f"T2 C1 score={score:.1f} (>= 3.0; too easy for discriminative T2)"
        )
    else:
        row["stage2_exclusion_reason"] = exclusion_reason

    # Propagate final_decision
    if row.get("is_anchor"):
        row["final_decision"] = "INCLUDE"  # anchors always stay
    elif decision == "INCLUDE":
        row["final_decision"] = "INCLUDE"
    elif decision == "EXCLUDE":
        row["final_decision"] = "EXCLUDE"
    # DEFER: leave final_decision unchanged; researcher resolves manually


# ---------------------------------------------------------------------------
# Stage 3 application
# ---------------------------------------------------------------------------


def stage3_decision_from_score(score: float) -> str:
    """Return the Stage 3 advisory decision string for a given T3 C2 score."""
    if score >= 1.0:
        return "ceiling_risk"
    return "preferred"


def apply_stage3_result(row: dict[str, Any], score: float) -> None:
    """Update *row* in-place with Stage 3 T3 C2 screening results (advisory).

    Does NOT modify final_decision — Stage 3 is informational only.
    """
    row["stage3_t3_c2_screen_score"] = score
    row["stage3_result"] = stage3_decision_from_score(score)


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------


def summarize_tracker(data: dict[str, Any]) -> dict[str, Any]:
    """Return a summary dict describing the current tracker state."""
    candidates = data.get("candidates", [])
    anchors = [c for c in candidates if c.get("is_anchor")]
    non_anchors = [c for c in candidates if not c.get("is_anchor")]

    screened_in = [c for c in non_anchors if c["stage2_result"] == "INCLUDE"]
    stage2_eligible = [
        c
        for c in non_anchors
        if c["stage1_result"] == "PASS" and c["stage2_result"] == "not_run"
    ]
    stage3_eligible = [
        c
        for c in non_anchors
        if c["stage2_result"] == "INCLUDE" and c["stage3_result"] == "not_run"
    ]

    return {
        "total": len(candidates),
        "anchors": len(anchors),
        "non_anchors": len(non_anchors),
        "stage1_counts": _count_by(candidates, "stage1_result"),
        "stage2_counts": _count_by(candidates, "stage2_result"),
        "stage3_counts": _count_by(non_anchors, "stage3_result"),
        "final_decision_counts": _count_by(candidates, "final_decision"),
        "screened_in_non_anchor": len(screened_in),
        "stage2_eligible_awaiting": len(stage2_eligible),
        "stage2_eligible_ids": [c["candidate_id"] for c in stage2_eligible],
        "stage3_eligible_awaiting": len(stage3_eligible),
        "stage3_eligible_ids": [c["candidate_id"] for c in stage3_eligible],
        "t2_family_diversity": _count_by(screened_in, "t2_bug_family_draft"),
        "t3_family_diversity": _count_by(screened_in, "t3_transform_family_draft"),
    }


def _count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        val = str(row.get(key, "missing"))
        counts[val] = counts.get(val, 0) + 1
    return dict(sorted(counts.items()))


# ---------------------------------------------------------------------------
# Stage-2-ready detection
# ---------------------------------------------------------------------------

_MANIFEST_FILENAME = "functions_manifest.json"


def _default_manifest_path() -> Path:
    return _repo_root() / "data" / "dataset" / _MANIFEST_FILENAME


def is_stage2_ready(
    candidate_id: str,
    manifest_path: Path | str | None = None,
) -> tuple[bool, str]:
    """Return (ready, reason) for a Stage-1-PASS candidate.

    "Ready" means the candidate_id appears in functions_manifest.json with
    tasks.T2.available == True.  This mirrors exactly what the runner checks
    before executing a T2 item.

    A Stage 1 PASS candidate is NOT necessarily ready.  Truth authoring
    (raw source, manifest entry, T2 bug annotation, test suite) must be
    completed first.

    Returns:
        (True,  "in manifest, T2 available")
        (False, "not in functions_manifest.json")
        (False, "in manifest but T2 not available")
        (False, "functions_manifest.json not found at <path>")
        (False, "functions_manifest.json is not valid JSON")
    """
    p = Path(manifest_path) if manifest_path else _default_manifest_path()
    if not p.exists():
        return False, f"functions_manifest.json not found at {p}"
    try:
        manifest = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False, "functions_manifest.json is not valid JSON"
    for item in manifest.get("items", []):
        if item.get("func_id") == candidate_id:
            if item.get("tasks", {}).get("T2", {}).get("available"):
                return True, "in manifest, T2 available"
            return False, "in manifest but T2 not available"
    return False, "not in functions_manifest.json"


# ---------------------------------------------------------------------------
# Workflow state
# ---------------------------------------------------------------------------

# Ordered labels used across list/summary output.
WORKFLOW_STATES = (
    "anchor",
    "pending",     # DEFER, no reason — added but not yet reviewed
    "deferred",    # DEFER with reason — intentionally held
    "excluded",    # EXCLUDE
    "pass-blocked",  # PASS but not yet stage2-ready
    "pass-ready",    # PASS and stage2-ready (in manifest, T2 available)
    "stage2-screened",  # stage2_result has been set
)


def workflow_state(
    row: dict[str, Any],
    manifest_path: Path | str | None = None,
) -> str:
    """Return a human-readable workflow state label for *row*.

    States (in lifecycle order):
      anchor         — one of the three pilot calibration anchors
      pending        — added to tracker, Stage 1 not yet reviewed
      deferred       — Stage 1 set to DEFER with a stated reason
      excluded       — Stage 1 set to EXCLUDE
      pass-blocked   — Stage 1 PASS, but prerequisites for Stage 2 not met
      pass-ready     — Stage 1 PASS AND in manifest with T2 available
      stage2-screened — Stage 2 has been run (INCLUDE / EXCLUDE / DEFER)

    Note: pass-blocked and pass-ready are both subsets of "Stage 1 PASS".
    Being pass-ready requires candidate_id to be present in
    functions_manifest.json with T2 available.  That does NOT happen
    automatically from a Stage 1 PASS decision — the researcher must
    complete truth-authoring prerequisites first.
    """
    if row.get("is_anchor"):
        return "anchor"
    if row["stage2_result"] != "not_run":
        return "stage2-screened"
    if row["stage1_result"] == "EXCLUDE":
        return "excluded"
    if row["stage1_result"] == "DEFER":
        # Distinguish "just added" from "intentionally deferred"
        if row.get("stage1_exclusion_reason"):
            return "deferred"
        return "pending"
    # stage1_result == "PASS"
    ready, _reason = is_stage2_ready(row["candidate_id"], manifest_path)
    return "pass-ready" if ready else "pass-blocked"


def workflow_summary(
    data: dict[str, Any],
    manifest_path: Path | str | None = None,
) -> dict[str, Any]:
    """Return a workflow-state breakdown of all candidates.

    Unlike summarize_tracker (which counts by raw field values), this
    function classifies each candidate by its workflow_state() label and
    also surfaces the blocking reason for every pass-blocked candidate.

    This function reads the manifest to determine pass-ready vs pass-blocked,
    so it has a filesystem side-effect.  Pass None for manifest_path to skip
    ready-checking (all PASS rows will be reported as pass-blocked).
    """
    candidates = data.get("candidates", [])

    state_counts: dict[str, int] = {s: 0 for s in WORKFLOW_STATES}
    pass_blocked: list[dict[str, str]] = []   # [{candidate_id, reason}]
    pass_ready: list[str] = []

    for row in candidates:
        state = workflow_state(row, manifest_path)
        state_counts[state] = state_counts.get(state, 0) + 1

        if state == "pass-blocked":
            _ready, reason = is_stage2_ready(row["candidate_id"], manifest_path)
            pass_blocked.append({"candidate_id": row["candidate_id"], "reason": reason})
        elif state == "pass-ready":
            pass_ready.append(row["candidate_id"])

    return {
        "state_counts": state_counts,
        "pass_blocked": pass_blocked,
        "pass_ready_ids": pass_ready,
        "total": len(candidates),
    }
