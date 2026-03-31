"""Tests for the candidate tracker module (src/experiment/candidate_tracker.py).

Follows the repo's unittest.TestCase pattern (see test_experiment_contracts.py).
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from experiment.candidate_tracker import (  # noqa: E402
    ANCHOR_IDS,
    SCHEMA_VERSION,
    TrackerError,
    apply_stage2_result,
    apply_stage3_result,
    default_tracker_path,
    empty_tracker,
    get_candidate,
    load_tracker,
    save_tracker,
    stage2_decision_from_score,
    stage3_decision_from_score,
    summarize_tracker,
    upsert_candidate,
    validate_candidate,
    validate_tracker,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_minimal_row(
    candidate_id: str = "test_func",
    is_anchor: bool = False,
) -> dict:
    """Return a fully valid, Stage-1-only candidate row."""
    return {
        "candidate_id": candidate_id,
        "source": "test",
        "body_line_count": 15,
        "estimated_complexity": "medium",
        "t2_bug_family_draft": "boundary_interaction",
        "t3_transform_family_draft": "invariant_preserving_refactor",
        "stage1_result": "PASS",
        "stage1_exclusion_reason": None,
        "stage2_t2_c1_screen_score": None,
        "stage2_t2_subscores": None,
        "stage2_result": "not_run",
        "stage2_exclusion_reason": None,
        "stage3_t3_c2_screen_score": None,
        "stage3_result": "not_run",
        "final_decision": "DEFER",
        "is_anchor": is_anchor,
        "notes": "",
    }


def _make_stage2_included_row(candidate_id: str = "test_func_hard") -> dict:
    """Return a valid row that has passed Stage 2 screening."""
    row = _make_minimal_row(candidate_id)
    row["stage2_t2_c1_screen_score"] = 2.0
    row["stage2_t2_subscores"] = {"location": 1, "diagnosis": 1, "fix": 0}
    row["stage2_result"] = "INCLUDE"
    row["final_decision"] = "INCLUDE"
    return row


def _make_anchor_row(candidate_id: str = "clamp") -> dict:
    """Return a valid anchor row (as stored in candidates.json)."""
    return {
        "candidate_id": candidate_id,
        "source": "pilot-anchor",
        "body_line_count": 5,
        "estimated_complexity": "trivial",
        "t2_bug_family_draft": "wrong_comparison_operator",
        "t3_transform_family_draft": "precondition_enforcement",
        "stage1_result": "PASS",
        "stage1_exclusion_reason": None,
        "stage2_t2_c1_screen_score": 3.0,
        "stage2_t2_subscores": {"location": 1, "diagnosis": 1, "fix": 1},
        "stage2_result": "EXCLUDE",
        "stage2_exclusion_reason": "Anchor: calibration function.",
        "stage3_t3_c2_screen_score": 1.0,
        "stage3_result": "ceiling_risk",
        "final_decision": "INCLUDE",
        "is_anchor": True,
        "notes": "Pilot anchor.",
    }


def _make_tracker(*rows: dict) -> dict:
    data = empty_tracker()
    for row in rows:
        data["candidates"].append(row)
    return data


# ---------------------------------------------------------------------------
# Schema and enum validation
# ---------------------------------------------------------------------------

class TestValidateCandidate(unittest.TestCase):

    def test_valid_minimal_row_passes(self) -> None:
        """A fully populated, Stage-1-only row should pass without error."""
        validate_candidate(_make_minimal_row())

    def test_valid_stage2_included_row_passes(self) -> None:
        validate_candidate(_make_stage2_included_row())

    def test_valid_anchor_row_passes(self) -> None:
        validate_candidate(_make_anchor_row("clamp"))

    def test_missing_required_field_fails(self) -> None:
        for field in ("candidate_id", "stage1_result", "final_decision", "is_anchor"):
            row = _make_minimal_row()
            del row[field]
            with self.assertRaises(TrackerError, msg=f"missing field: {field}"):
                validate_candidate(row)

    def test_invalid_estimated_complexity_fails(self) -> None:
        row = _make_minimal_row()
        row["estimated_complexity"] = "extreme"
        with self.assertRaises(TrackerError):
            validate_candidate(row)

    def test_invalid_stage1_result_fails(self) -> None:
        row = _make_minimal_row()
        row["stage1_result"] = "MAYBE"
        with self.assertRaises(TrackerError):
            validate_candidate(row)

    def test_invalid_stage2_result_fails(self) -> None:
        row = _make_stage2_included_row()
        row["stage2_result"] = "REJECT"
        with self.assertRaises(TrackerError):
            validate_candidate(row)

    def test_invalid_stage3_result_fails(self) -> None:
        row = _make_stage2_included_row()
        # Add valid stage3 data but wrong enum
        row["stage3_t3_c2_screen_score"] = 0.5
        row["stage3_result"] = "bad_value"
        with self.assertRaises(TrackerError):
            validate_candidate(row)

    def test_invalid_final_decision_fails(self) -> None:
        row = _make_minimal_row()
        row["final_decision"] = "MAYBE"
        with self.assertRaises(TrackerError):
            validate_candidate(row)


# ---------------------------------------------------------------------------
# Anchor policy
# ---------------------------------------------------------------------------

class TestAnchorPolicy(unittest.TestCase):

    def test_is_anchor_true_on_non_anchor_id_fails(self) -> None:
        """is_anchor=True for a non-designated ID must be rejected."""
        row = _make_minimal_row("random_func")
        row["is_anchor"] = True
        with self.assertRaises(TrackerError):
            validate_candidate(row)

    def test_is_anchor_false_on_anchor_id_is_allowed(self) -> None:
        """A row with candidate_id='clamp' but is_anchor=False is valid."""
        row = _make_minimal_row("clamp")
        row["is_anchor"] = False
        validate_candidate(row)  # no exception

    def test_anchor_include_overrides_stage2_exclude(self) -> None:
        """Anchors may have final_decision=INCLUDE even when stage2_result=EXCLUDE."""
        row = _make_anchor_row("clamp")
        validate_candidate(row)  # should not raise

    def test_non_anchor_include_with_stage2_exclude_fails(self) -> None:
        """Non-anchor with stage2_result=EXCLUDE but final_decision=INCLUDE must fail."""
        row = _make_minimal_row("hard_func")
        row["stage2_t2_c1_screen_score"] = 3.0
        row["stage2_t2_subscores"] = {"location": 1, "diagnosis": 1, "fix": 1}
        row["stage2_result"] = "EXCLUDE"
        row["stage2_exclusion_reason"] = "Too easy."
        row["final_decision"] = "INCLUDE"
        with self.assertRaises(TrackerError):
            validate_candidate(row)

    def test_all_three_designated_anchors_accepted(self) -> None:
        for anchor_id in ANCHOR_IDS:
            row = _make_anchor_row(anchor_id)
            row["candidate_id"] = anchor_id
            validate_candidate(row)


# ---------------------------------------------------------------------------
# Stage transition rules
# ---------------------------------------------------------------------------

class TestStageTransitions(unittest.TestCase):

    def test_stage2_without_stage1_pass_fails(self) -> None:
        """Stage 2 fields must not be set unless stage1_result=PASS."""
        row = _make_minimal_row()
        row["stage1_result"] = "EXCLUDE"
        row["stage1_exclusion_reason"] = "Too simple."
        row["stage2_t2_c1_screen_score"] = 2.5
        row["stage2_t2_subscores"] = {"location": 1, "diagnosis": 1, "fix": 0}
        row["stage2_result"] = "INCLUDE"
        row["final_decision"] = "INCLUDE"
        with self.assertRaises(TrackerError):
            validate_candidate(row)

    def test_stage3_without_stage2_include_fails_for_non_anchor(self) -> None:
        """Stage 3 requires Stage 2 INCLUDE for non-anchor rows."""
        row = _make_minimal_row()
        # Stage 2 excluded
        row["stage2_t2_c1_screen_score"] = 3.0
        row["stage2_t2_subscores"] = {"location": 1, "diagnosis": 1, "fix": 1}
        row["stage2_result"] = "EXCLUDE"
        row["stage2_exclusion_reason"] = "Too easy."
        row["final_decision"] = "EXCLUDE"
        # Stage 3 set anyway
        row["stage3_t3_c2_screen_score"] = 0.8
        row["stage3_result"] = "preferred"
        with self.assertRaises(TrackerError):
            validate_candidate(row)

    def test_include_with_stage1_not_pass_fails(self) -> None:
        row = _make_minimal_row()
        row["stage1_result"] = "DEFER"
        row["final_decision"] = "INCLUDE"
        with self.assertRaises(TrackerError):
            validate_candidate(row)

    def test_stage2_score_set_but_result_not_run_fails(self) -> None:
        row = _make_minimal_row()
        row["stage2_t2_c1_screen_score"] = 2.5  # inconsistent
        row["stage2_result"] = "not_run"
        with self.assertRaises(TrackerError):
            validate_candidate(row)

    def test_stage3_score_set_but_result_not_run_fails(self) -> None:
        row = _make_stage2_included_row()
        row["stage3_t3_c2_screen_score"] = 0.8  # inconsistent
        row["stage3_result"] = "not_run"
        with self.assertRaises(TrackerError):
            validate_candidate(row)


# ---------------------------------------------------------------------------
# Duplicate candidate_id
# ---------------------------------------------------------------------------

class TestDuplicateId(unittest.TestCase):

    def test_duplicate_candidate_id_fails(self) -> None:
        row1 = _make_minimal_row("func_a")
        row2 = _make_minimal_row("func_a")  # same id
        data = _make_tracker(row1, row2)
        with self.assertRaises(TrackerError):
            validate_tracker(data)

    def test_unique_ids_pass(self) -> None:
        data = _make_tracker(
            _make_minimal_row("func_a"),
            _make_minimal_row("func_b"),
        )
        validate_tracker(data)  # no exception


# ---------------------------------------------------------------------------
# Stage 2 decision rules
# ---------------------------------------------------------------------------

class TestStage2DecisionFromScore(unittest.TestCase):

    def test_score_3_0_gives_exclude(self) -> None:
        self.assertEqual(stage2_decision_from_score(3.0), "EXCLUDE")

    def test_score_above_3_gives_exclude(self) -> None:
        self.assertEqual(stage2_decision_from_score(3.5), "EXCLUDE")

    def test_score_2_9_gives_include(self) -> None:
        self.assertEqual(stage2_decision_from_score(2.9), "INCLUDE")

    def test_score_2_0_gives_include(self) -> None:
        self.assertEqual(stage2_decision_from_score(2.0), "INCLUDE")

    def test_score_1_0_gives_include(self) -> None:
        self.assertEqual(stage2_decision_from_score(1.0), "INCLUDE")

    def test_score_0_9_gives_defer(self) -> None:
        self.assertEqual(stage2_decision_from_score(0.9), "DEFER")

    def test_score_0_gives_defer(self) -> None:
        self.assertEqual(stage2_decision_from_score(0.0), "DEFER")


class TestApplyStage2Result(unittest.TestCase):

    def test_apply_2_0_sets_include(self) -> None:
        row = _make_minimal_row()
        apply_stage2_result(row, score=2.0, subscores={"location": 1, "diagnosis": 1, "fix": 0})
        self.assertEqual(row["stage2_result"], "INCLUDE")
        self.assertEqual(row["final_decision"], "INCLUDE")
        self.assertEqual(row["stage2_t2_c1_screen_score"], 2.0)
        self.assertEqual(row["stage2_t2_subscores"], {"location": 1, "diagnosis": 1, "fix": 0})

    def test_apply_3_0_sets_exclude(self) -> None:
        row = _make_minimal_row()
        apply_stage2_result(row, score=3.0, subscores={"location": 1, "diagnosis": 1, "fix": 1})
        self.assertEqual(row["stage2_result"], "EXCLUDE")
        self.assertEqual(row["final_decision"], "EXCLUDE")
        self.assertIsNotNone(row["stage2_exclusion_reason"])

    def test_apply_0_sets_defer_preserves_final(self) -> None:
        row = _make_minimal_row()
        row["final_decision"] = "DEFER"
        apply_stage2_result(row, score=0.0, subscores={"location": 0, "diagnosis": 0, "fix": 0})
        self.assertEqual(row["stage2_result"], "DEFER")
        # DEFER leaves final_decision unchanged
        self.assertEqual(row["final_decision"], "DEFER")

    def test_apply_stage2_to_stage1_non_pass_fails(self) -> None:
        row = _make_minimal_row()
        row["stage1_result"] = "EXCLUDE"
        row["stage1_exclusion_reason"] = "trivial"
        with self.assertRaises(TrackerError):
            apply_stage2_result(row, score=2.0, subscores={})

    def test_anchor_keeps_include_despite_score_3(self) -> None:
        row = _make_anchor_row("clamp")
        # Re-apply with overwrite
        apply_stage2_result(row, score=3.0, subscores={"location": 1, "diagnosis": 1, "fix": 1})
        self.assertEqual(row["stage2_result"], "EXCLUDE")
        self.assertEqual(row["final_decision"], "INCLUDE")  # anchor policy preserved


# ---------------------------------------------------------------------------
# Stage 3 decision rules
# ---------------------------------------------------------------------------

class TestStage3DecisionFromScore(unittest.TestCase):

    def test_score_1_0_gives_ceiling_risk(self) -> None:
        self.assertEqual(stage3_decision_from_score(1.0), "ceiling_risk")

    def test_score_0_9_gives_preferred(self) -> None:
        self.assertEqual(stage3_decision_from_score(0.9), "preferred")

    def test_score_0_gives_preferred(self) -> None:
        self.assertEqual(stage3_decision_from_score(0.0), "preferred")


class TestApplyStage3Result(unittest.TestCase):

    def test_apply_0_9_sets_preferred_no_final_change(self) -> None:
        row = _make_stage2_included_row()
        apply_stage3_result(row, score=0.9)
        self.assertEqual(row["stage3_result"], "preferred")
        self.assertEqual(row["stage3_t3_c2_screen_score"], 0.9)
        # Stage 3 must not change final_decision
        self.assertEqual(row["final_decision"], "INCLUDE")

    def test_apply_1_0_sets_ceiling_risk(self) -> None:
        row = _make_stage2_included_row()
        apply_stage3_result(row, score=1.0)
        self.assertEqual(row["stage3_result"], "ceiling_risk")
        self.assertEqual(row["final_decision"], "INCLUDE")  # unchanged


# ---------------------------------------------------------------------------
# Tracker-level operations
# ---------------------------------------------------------------------------

class TestUpsertCandidate(unittest.TestCase):

    def test_append_new_row(self) -> None:
        data = empty_tracker()
        row = _make_minimal_row("func_a")
        upsert_candidate(data, row)
        self.assertEqual(len(data["candidates"]), 1)

    def test_replace_existing_row(self) -> None:
        data = _make_tracker(_make_minimal_row("func_a"))
        updated = _make_minimal_row("func_a")
        updated["notes"] = "updated"
        upsert_candidate(data, updated)
        self.assertEqual(len(data["candidates"]), 1)
        self.assertEqual(data["candidates"][0]["notes"], "updated")

    def test_upsert_invalid_row_fails_before_writing(self) -> None:
        data = empty_tracker()
        row = _make_minimal_row("func_x")
        row["stage1_result"] = "BAD"
        with self.assertRaises(TrackerError):
            upsert_candidate(data, row)
        # Tracker unchanged
        self.assertEqual(len(data["candidates"]), 0)

    def test_unrelated_rows_preserved_after_upsert(self) -> None:
        data = _make_tracker(
            _make_minimal_row("func_a"),
            _make_minimal_row("func_b"),
        )
        updated = _make_minimal_row("func_b")
        updated["notes"] = "changed"
        upsert_candidate(data, updated)
        # func_a unchanged
        func_a = get_candidate(data, "func_a")
        self.assertIsNotNone(func_a)
        self.assertEqual(func_a["notes"], "")  # type: ignore[index]


# ---------------------------------------------------------------------------
# Save / load round-trip
# ---------------------------------------------------------------------------

class TestSaveLoadRoundtrip(unittest.TestCase):

    def test_save_and_reload_produces_identical_data(self) -> None:
        data = _make_tracker(
            _make_minimal_row("func_a"),
            _make_stage2_included_row("func_b"),
            _make_anchor_row("clamp"),
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            save_tracker(data, tmp)
            loaded = load_tracker(tmp)
            self.assertEqual(data, loaded)
        finally:
            tmp.unlink(missing_ok=True)

    def test_load_missing_file_raises_tracker_error(self) -> None:
        with self.assertRaises(TrackerError):
            load_tracker("/nonexistent/path/candidates.json")

    def test_load_wrong_schema_raises_tracker_error(self) -> None:
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as f:
            json.dump({"lumen_schema": "wrong-schema-v99", "candidates": []}, f)
            tmp = Path(f.name)
        try:
            with self.assertRaises(TrackerError):
                load_tracker(tmp)
        finally:
            tmp.unlink(missing_ok=True)

    def test_save_invalid_data_raises_before_writing(self) -> None:
        data = empty_tracker()
        bad_row = _make_minimal_row("func_x")
        bad_row["stage1_result"] = "INVALID"
        data["candidates"].append(bad_row)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
            original_content = ""
        tmp.write_text(original_content)
        try:
            with self.assertRaises(TrackerError):
                save_tracker(data, tmp)
        finally:
            tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Update-from-run: write Stage 2 fields and preserve unrelated rows
# ---------------------------------------------------------------------------

class TestUpdateFromRunStage2Logic(unittest.TestCase):
    """Unit-tests for the Stage 2 application logic (not the CLI)."""

    def test_update_stage2_writes_correct_fields(self) -> None:
        row = _make_minimal_row("func_a")
        apply_stage2_result(
            row,
            score=1.5,
            subscores={"location": 1, "diagnosis": 1, "fix": 0},
        )
        self.assertEqual(row["stage2_t2_c1_screen_score"], 1.5)
        self.assertEqual(row["stage2_t2_subscores"]["fix"], 0)
        self.assertEqual(row["stage2_result"], "INCLUDE")
        self.assertEqual(row["final_decision"], "INCLUDE")

    def test_update_stage2_does_not_affect_other_row(self) -> None:
        row_a = _make_minimal_row("func_a")
        row_b = _make_minimal_row("func_b")
        apply_stage2_result(
            row_a,
            score=2.0,
            subscores={"location": 1, "diagnosis": 1, "fix": 0},
        )
        # row_b completely unchanged
        self.assertEqual(row_b["stage2_result"], "not_run")
        self.assertIsNone(row_b["stage2_t2_c1_screen_score"])

    def test_full_tracker_validates_after_stage2_update(self) -> None:
        data = _make_tracker(_make_minimal_row("func_a"), _make_minimal_row("func_b"))
        row = get_candidate(data, "func_a")
        assert row is not None
        apply_stage2_result(
            row,
            score=2.0,
            subscores={"location": 1, "diagnosis": 1, "fix": 0},
        )
        upsert_candidate(data, row)
        validate_tracker(data)  # must not raise


# ---------------------------------------------------------------------------
# update_candidates_from_run CLI integration (uses real pilot scores)
# ---------------------------------------------------------------------------

class TestUpdateCandidatesFromRunCLI(unittest.TestCase):
    """End-to-end tests that read real pilot score files from the repo."""

    _PILOT_RUN = "pilot_full_gpt54_opus46_02"
    _PILOT_MODEL = "gpt-5.4"

    def _pilot_run_exists(self) -> bool:
        p = ROOT / "results" / "runs" / self._PILOT_RUN / "scores"
        return p.is_dir()

    def test_ingest_stage2_from_pilot_updates_anchor_rows(self) -> None:
        if not self._pilot_run_exists():
            self.skipTest("Pilot run artifacts not present")

        import sys as _sys
        from experiment import update_candidates_from_run as ucr

        # Build a tracker with one anchor that has not yet had Stage 2 applied
        anchor_row = {
            "candidate_id": "clamp",
            "source": "pilot-anchor",
            "body_line_count": 5,
            "estimated_complexity": "trivial",
            "t2_bug_family_draft": "wrong_comparison_operator",
            "t3_transform_family_draft": "precondition_enforcement",
            "stage1_result": "PASS",
            "stage1_exclusion_reason": None,
            "stage2_t2_c1_screen_score": None,
            "stage2_t2_subscores": None,
            "stage2_result": "not_run",
            "stage2_exclusion_reason": None,
            "stage3_t3_c2_screen_score": None,
            "stage3_result": "not_run",
            "final_decision": "DEFER",
            "is_anchor": True,
            "notes": "",
        }
        data = _make_tracker(anchor_row)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            save_tracker(data, tmp)
            ret = ucr.main([
                "--run-id", self._PILOT_RUN,
                "--stage", "2",
                "--model", self._PILOT_MODEL,
                "--path", str(tmp),
            ])
            self.assertEqual(ret, 0)
            updated = load_tracker(tmp)
            clamp_row = get_candidate(updated, "clamp")
            assert clamp_row is not None
            # Pilot clamp T2 score was 3.0
            self.assertEqual(clamp_row["stage2_t2_c1_screen_score"], 3.0)
            self.assertEqual(clamp_row["stage2_result"], "EXCLUDE")
            # Anchor policy: final_decision stays INCLUDE
            self.assertEqual(clamp_row["final_decision"], "INCLUDE")
        finally:
            tmp.unlink(missing_ok=True)

    def test_ingest_stage3_from_pilot_updates_anchor_rows(self) -> None:
        if not self._pilot_run_exists():
            self.skipTest("Pilot run artifacts not present")

        from experiment import update_candidates_from_run as ucr

        # Build a tracker with the anchor that has Stage 2 already applied
        anchor_row = _make_anchor_row("clamp")
        # Reset stage3 fields to not_run so we can test ingestion
        anchor_row["stage3_t3_c2_screen_score"] = None
        anchor_row["stage3_result"] = "not_run"
        data = _make_tracker(anchor_row)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            save_tracker(data, tmp)
            ret = ucr.main([
                "--run-id", self._PILOT_RUN,
                "--stage", "3",
                "--model", self._PILOT_MODEL,
                "--path", str(tmp),
            ])
            self.assertEqual(ret, 0)
            updated = load_tracker(tmp)
            clamp_row = get_candidate(updated, "clamp")
            assert clamp_row is not None
            self.assertEqual(clamp_row["stage3_t3_c2_screen_score"], 1.0)
            self.assertEqual(clamp_row["stage3_result"], "ceiling_risk")
        finally:
            tmp.unlink(missing_ok=True)

    def test_ingest_does_not_overwrite_without_flag(self) -> None:
        if not self._pilot_run_exists():
            self.skipTest("Pilot run artifacts not present")

        from experiment import update_candidates_from_run as ucr

        anchor_row = _make_anchor_row("clamp")  # already has stage2 data
        data = _make_tracker(anchor_row)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            save_tracker(data, tmp)
            ret = ucr.main([
                "--run-id", self._PILOT_RUN,
                "--stage", "2",
                "--model", self._PILOT_MODEL,
                "--path", str(tmp),
            ])
            self.assertEqual(ret, 0)
            updated = load_tracker(tmp)
            clamp_row = get_candidate(updated, "clamp")
            assert clamp_row is not None
            # Should have been skipped, not changed
            self.assertEqual(clamp_row["stage2_exclusion_reason"], anchor_row["stage2_exclusion_reason"])
        finally:
            tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# summarize_tracker helper
# ---------------------------------------------------------------------------

class TestSummarizeTracker(unittest.TestCase):

    def test_empty_tracker_produces_zeros(self) -> None:
        data = empty_tracker()
        s = summarize_tracker(data)
        self.assertEqual(s["total"], 0)
        self.assertEqual(s["anchors"], 0)
        self.assertEqual(s["screened_in_non_anchor"], 0)

    def test_anchor_counted_separately(self) -> None:
        data = _make_tracker(_make_anchor_row("clamp"))
        s = summarize_tracker(data)
        self.assertEqual(s["anchors"], 1)
        self.assertEqual(s["non_anchors"], 0)
        # Anchor is not counted as "screened_in" because it's not a new candidate
        self.assertEqual(s["screened_in_non_anchor"], 0)

    def test_stage2_eligible_ids_populated(self) -> None:
        data = _make_tracker(
            _make_minimal_row("func_a"),
            _make_minimal_row("func_b"),
            _make_stage2_included_row("func_c"),
        )
        s = summarize_tracker(data)
        self.assertEqual(s["stage2_eligible_awaiting"], 2)
        self.assertIn("func_a", s["stage2_eligible_ids"])
        self.assertIn("func_b", s["stage2_eligible_ids"])
        self.assertNotIn("func_c", s["stage2_eligible_ids"])

    def test_screened_in_count_excludes_anchors(self) -> None:
        data = _make_tracker(
            _make_anchor_row("clamp"),       # anchor, not counted
            _make_stage2_included_row("func_a"),  # non-anchor INCLUDE
            _make_stage2_included_row("func_b"),  # non-anchor INCLUDE
        )
        s = summarize_tracker(data)
        self.assertEqual(s["screened_in_non_anchor"], 2)

    def test_t2_family_diversity_counts(self) -> None:
        row_a = _make_stage2_included_row("func_a")
        row_a["t2_bug_family_draft"] = "boundary_interaction"
        row_b = _make_stage2_included_row("func_b")
        row_b["t2_bug_family_draft"] = "boundary_interaction"
        row_c = _make_stage2_included_row("func_c")
        row_c["t2_bug_family_draft"] = "state_mutation_ordering"
        data = _make_tracker(row_a, row_b, row_c)
        s = summarize_tracker(data)
        self.assertEqual(s["t2_family_diversity"]["boundary_interaction"], 2)
        self.assertEqual(s["t2_family_diversity"]["state_mutation_ordering"], 1)


# ---------------------------------------------------------------------------
# End-to-end: init -> add rows -> ingest stage2 -> summarize
# ---------------------------------------------------------------------------

class TestEndToEndFlow(unittest.TestCase):

    def test_init_add_update_summarize(self) -> None:
        """Simulates the full curation lifecycle without touching real artifacts."""
        from experiment import init_candidates

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        tmp.unlink()  # init should create it

        try:
            # Step 1: init with anchors
            ret = init_candidates.main(["--path", str(tmp), "--seed-anchors"])
            self.assertEqual(ret, 0)
            data = load_tracker(tmp)
            self.assertEqual(len(data["candidates"]), 3)
            anchor_ids = {c["candidate_id"] for c in data["candidates"]}
            self.assertEqual(anchor_ids, ANCHOR_IDS)

            # Step 2: add two new candidate rows manually
            new_a = _make_minimal_row("func_hard_a")
            new_b = _make_minimal_row("func_hard_b")
            upsert_candidate(data, new_a)
            upsert_candidate(data, new_b)
            save_tracker(data, tmp)
            self.assertEqual(len(load_tracker(tmp)["candidates"]), 5)

            # Step 3: simulate Stage 2 result for func_hard_a
            data = load_tracker(tmp)
            row = get_candidate(data, "func_hard_a")
            assert row is not None
            apply_stage2_result(
                row,
                score=1.5,
                subscores={"location": 1, "diagnosis": 1, "fix": 0},
            )
            upsert_candidate(data, row)
            save_tracker(data, tmp)

            # Step 4: validate and summarize
            data = load_tracker(tmp)
            validate_tracker(data)
            s = summarize_tracker(data)

            self.assertEqual(s["total"], 5)
            self.assertEqual(s["screened_in_non_anchor"], 1)  # only func_hard_a
            self.assertIn("func_hard_b", s["stage2_eligible_ids"])
            self.assertNotIn("func_hard_a", s["stage2_eligible_ids"])

        finally:
            tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# candidates.json on disk: verify the committed file is valid
# ---------------------------------------------------------------------------

class TestCommittedCandidatesJson(unittest.TestCase):

    def test_committed_candidates_json_is_valid(self) -> None:
        """The checked-in candidates.json must pass full schema validation."""
        p = default_tracker_path()
        if not p.exists():
            self.skipTest(f"candidates.json not found at {p}")
        data = load_tracker(p)
        validate_tracker(data)  # raises if invalid

    def test_committed_anchors_are_present(self) -> None:
        p = default_tracker_path()
        if not p.exists():
            self.skipTest(f"candidates.json not found at {p}")
        data = load_tracker(p)
        present_ids = {c["candidate_id"] for c in data["candidates"]}
        for anchor_id in ANCHOR_IDS:
            self.assertIn(anchor_id, present_ids, f"Anchor '{anchor_id}' missing from tracker")

    def test_committed_anchors_have_is_anchor_true(self) -> None:
        p = default_tracker_path()
        if not p.exists():
            self.skipTest(f"candidates.json not found at {p}")
        data = load_tracker(p)
        for row in data["candidates"]:
            if row["candidate_id"] in ANCHOR_IDS:
                self.assertTrue(
                    row["is_anchor"],
                    f"Anchor '{row['candidate_id']}' has is_anchor=False",
                )


if __name__ == "__main__":
    unittest.main()
