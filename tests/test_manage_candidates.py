"""Tests for manage_candidates.py and the Phase 2B tracker additions.

Covers:
  - manage_candidates add / update-stage1 / list / show / validate
  - is_stage2_ready detection
  - workflow_state labels
  - workflow_summary breakdown
  - summary output reflects workflow distinctions
  - excluded rows are preserved (not deleted)
  - candidate_id vs anchor conflicts
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
    TrackerError,
    default_tracker_path,
    empty_tracker,
    get_candidate,
    is_stage2_ready,
    load_tracker,
    save_tracker,
    upsert_candidate,
    workflow_state,
    workflow_summary,
)
from experiment import manage_candidates  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _blank_row(cid: str = "test_func") -> dict:
    """Minimal unreviewed (pending) row — the default after 'add'."""
    return {
        "candidate_id": cid,
        "source": "test",
        "body_line_count": 12,
        "estimated_complexity": "medium",
        "t2_bug_family_draft": "boundary_interaction",
        "t3_transform_family_draft": "invariant_preserving_refactor",
        "stage1_result": "DEFER",
        "stage1_exclusion_reason": None,
        "stage2_t2_c1_screen_score": None,
        "stage2_t2_subscores": None,
        "stage2_result": "not_run",
        "stage2_exclusion_reason": None,
        "stage3_t3_c2_screen_score": None,
        "stage3_result": "not_run",
        "final_decision": "DEFER",
        "is_anchor": False,
        "notes": "",
    }


def _pass_row(cid: str = "test_func") -> dict:
    row = _blank_row(cid)
    row["stage1_result"] = "PASS"
    return row


def _excluded_row(cid: str = "trivial_func") -> dict:
    row = _blank_row(cid)
    row["stage1_result"] = "EXCLUDE"
    row["stage1_exclusion_reason"] = "Single operator flip; too easy."
    row["final_decision"] = "EXCLUDE"
    return row


def _anchor_row(cid: str = "clamp") -> dict:
    return {
        "candidate_id": cid,
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
        "stage2_exclusion_reason": "Anchor: calibration.",
        "stage3_t3_c2_screen_score": 1.0,
        "stage3_result": "ceiling_risk",
        "final_decision": "INCLUDE",
        "is_anchor": True,
        "notes": "",
    }


def _tracker_with(*rows: dict) -> dict:
    data = empty_tracker()
    for r in rows:
        data["candidates"].append(r)
    return data


def _write_tracker(data: dict, tmp: Path) -> None:
    save_tracker(data, tmp)


def _minimal_manifest(func_ids_with_t2: list[str]) -> dict:
    """Build a minimal manifest dict for testing is_stage2_ready."""
    items = []
    for fid in func_ids_with_t2:
        items.append({
            "func_id": fid,
            "tasks": {"T2": {"available": True}},
        })
    return {"lumen_schema": "dataset-manifest-v1", "items": items}


def _write_manifest(manifest: dict, tmp: Path) -> None:
    tmp.write_text(json.dumps(manifest), encoding="utf-8")


# ---------------------------------------------------------------------------
# is_stage2_ready
# ---------------------------------------------------------------------------

class TestIsStage2Ready(unittest.TestCase):

    def test_in_manifest_with_t2_available(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mp = Path(f.name)
        try:
            _write_manifest(_minimal_manifest(["my_func"]), mp)
            ready, reason = is_stage2_ready("my_func", mp)
            self.assertTrue(ready)
            self.assertIn("T2 available", reason)
        finally:
            mp.unlink(missing_ok=True)

    def test_not_in_manifest(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mp = Path(f.name)
        try:
            _write_manifest(_minimal_manifest(["other_func"]), mp)
            ready, reason = is_stage2_ready("my_func", mp)
            self.assertFalse(ready)
            self.assertIn("not in functions_manifest", reason)
        finally:
            mp.unlink(missing_ok=True)

    def test_in_manifest_but_t2_not_available(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mp = Path(f.name)
        try:
            manifest = {
                "lumen_schema": "dataset-manifest-v1",
                "items": [{"func_id": "my_func", "tasks": {"T2": {"available": False}}}],
            }
            _write_manifest(manifest, mp)
            ready, reason = is_stage2_ready("my_func", mp)
            self.assertFalse(ready)
            self.assertIn("T2 not available", reason)
        finally:
            mp.unlink(missing_ok=True)

    def test_manifest_file_missing(self) -> None:
        ready, reason = is_stage2_ready("my_func", "/nonexistent/path/manifest.json")
        self.assertFalse(ready)
        self.assertIn("not found", reason)

    def test_manifest_not_valid_json(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write("this is not json {{{{")
            mp = Path(f.name)
        try:
            ready, reason = is_stage2_ready("my_func", mp)
            self.assertFalse(ready)
            self.assertIn("not valid JSON", reason)
        finally:
            mp.unlink(missing_ok=True)

    def test_real_manifest_contains_pilot_funcs(self) -> None:
        """The real repo manifest should have all 3 pilot functions as stage2-ready."""
        mp = ROOT / "data" / "dataset" / "functions_manifest.json"
        if not mp.exists():
            self.skipTest("functions_manifest.json not found")
        for fid in ("clamp", "count_vowels", "is_sorted"):
            ready, reason = is_stage2_ready(fid, mp)
            self.assertTrue(ready, f"{fid}: {reason}")


# ---------------------------------------------------------------------------
# workflow_state
# ---------------------------------------------------------------------------

class TestWorkflowState(unittest.TestCase):

    def _state(self, row: dict, manifest_path=None) -> str:
        return workflow_state(row, manifest_path)

    def test_anchor_row(self) -> None:
        self.assertEqual(self._state(_anchor_row("clamp")), "anchor")

    def test_pending_row(self) -> None:
        """DEFER with no reason = pending (just added, not yet reviewed)."""
        row = _blank_row()
        row["stage1_result"] = "DEFER"
        row["stage1_exclusion_reason"] = None
        self.assertEqual(self._state(row), "pending")

    def test_deferred_with_reason(self) -> None:
        row = _blank_row()
        row["stage1_result"] = "DEFER"
        row["stage1_exclusion_reason"] = "Need to recount lines."
        self.assertEqual(self._state(row), "deferred")

    def test_excluded_row(self) -> None:
        self.assertEqual(self._state(_excluded_row()), "excluded")

    def test_pass_blocked_when_manifest_missing(self) -> None:
        """Stage 1 PASS but manifest not found → pass-blocked."""
        row = _pass_row()
        state = workflow_state(row, "/nonexistent/manifest.json")
        self.assertEqual(state, "pass-blocked")

    def test_pass_ready_when_in_manifest(self) -> None:
        row = _pass_row("my_func")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mp = Path(f.name)
        try:
            _write_manifest(_minimal_manifest(["my_func"]), mp)
            self.assertEqual(workflow_state(row, mp), "pass-ready")
        finally:
            mp.unlink(missing_ok=True)

    def test_pass_blocked_when_not_in_manifest(self) -> None:
        row = _pass_row("unknown_func")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mp = Path(f.name)
        try:
            _write_manifest(_minimal_manifest(["other_func"]), mp)
            self.assertEqual(workflow_state(row, mp), "pass-blocked")
        finally:
            mp.unlink(missing_ok=True)

    def test_stage2_screened_overrides_pass_ready(self) -> None:
        """Once stage2_result is set, state is stage2-screened regardless."""
        row = _pass_row()
        row["stage2_t2_c1_screen_score"] = 2.0
        row["stage2_t2_subscores"] = {"location": 1, "diagnosis": 1, "fix": 0}
        row["stage2_result"] = "INCLUDE"
        row["final_decision"] = "INCLUDE"
        self.assertEqual(self._state(row), "stage2-screened")


# ---------------------------------------------------------------------------
# workflow_summary
# ---------------------------------------------------------------------------

class TestWorkflowSummary(unittest.TestCase):

    def test_empty_tracker(self) -> None:
        data = empty_tracker()
        ws = workflow_summary(data)
        self.assertEqual(ws["total"], 0)
        self.assertEqual(ws["pass_blocked"], [])
        self.assertEqual(ws["pass_ready_ids"], [])

    def test_anchor_counted_as_anchor(self) -> None:
        data = _tracker_with(_anchor_row("clamp"))
        ws = workflow_summary(data)
        self.assertEqual(ws["state_counts"].get("anchor", 0), 1)
        self.assertEqual(ws["pass_blocked"], [])

    def test_pending_row_counted(self) -> None:
        data = _tracker_with(_blank_row("func_a"))
        ws = workflow_summary(data)
        self.assertEqual(ws["state_counts"].get("pending", 0), 1)

    def test_pass_blocked_appears_in_list(self) -> None:
        """Stage 1 PASS but not in manifest → appears in pass_blocked list."""
        row = _pass_row("func_x")
        data = _tracker_with(row)
        # No manifest path given; defaults to repo manifest (func_x won't be there)
        ws = workflow_summary(data)
        # func_x is not in the real manifest
        blocked_ids = [b["candidate_id"] for b in ws["pass_blocked"]]
        self.assertIn("func_x", blocked_ids)

    def test_pass_ready_appears_in_list(self) -> None:
        row = _pass_row("my_func")
        data = _tracker_with(row)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mp = Path(f.name)
        try:
            _write_manifest(_minimal_manifest(["my_func"]), mp)
            ws = workflow_summary(data, mp)
            self.assertIn("my_func", ws["pass_ready_ids"])
            # Should NOT appear in blocked list
            blocked_ids = [b["candidate_id"] for b in ws["pass_blocked"]]
            self.assertNotIn("my_func", blocked_ids)
        finally:
            mp.unlink(missing_ok=True)

    def test_excluded_row_counted(self) -> None:
        data = _tracker_with(_excluded_row("bad_func"))
        ws = workflow_summary(data)
        self.assertEqual(ws["state_counts"].get("excluded", 0), 1)
        self.assertEqual(ws["pass_blocked"], [])


# ---------------------------------------------------------------------------
# manage_candidates add
# ---------------------------------------------------------------------------

class TestManageCandidatesAdd(unittest.TestCase):

    def _run(self, args: list[str], tracker_path: Path) -> int:
        return manage_candidates.main(["--path", str(tracker_path)] + args)

    def test_add_valid_candidate(self) -> None:
        data = empty_tracker()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            save_tracker(data, tmp)
            ret = self._run([
                "add", "--id", "my_func",
                "--source", "authored",
                "--lines", "14",
                "--complexity", "medium",
                "--t2-family", "boundary_interaction",
                "--t3-family", "invariant_preserving_refactor",
            ], tmp)
            self.assertEqual(ret, 0)
            loaded = load_tracker(tmp)
            row = get_candidate(loaded, "my_func")
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row["stage1_result"], "DEFER")
            self.assertIsNone(row["stage1_exclusion_reason"])
            self.assertEqual(row["is_anchor"], False)
            self.assertEqual(row["source"], "authored")
            self.assertEqual(row["body_line_count"], 14)
        finally:
            tmp.unlink(missing_ok=True)

    def test_add_duplicate_id_fails(self) -> None:
        data = _tracker_with(_blank_row("existing_func"))
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            save_tracker(data, tmp)
            ret = self._run([
                "add", "--id", "existing_func", "--source", "authored",
            ], tmp)
            self.assertNotEqual(ret, 0)
            # Tracker unchanged
            loaded = load_tracker(tmp)
            self.assertEqual(len(loaded["candidates"]), 1)
        finally:
            tmp.unlink(missing_ok=True)

    def test_add_anchor_id_fails(self) -> None:
        data = empty_tracker()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            save_tracker(data, tmp)
            for anchor_id in ANCHOR_IDS:
                ret = self._run([
                    "add", "--id", anchor_id, "--source", "authored",
                ], tmp)
                self.assertNotEqual(ret, 0, f"Should have rejected anchor: {anchor_id}")
        finally:
            tmp.unlink(missing_ok=True)

    def test_add_invalid_complexity_fails(self) -> None:
        data = empty_tracker()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            save_tracker(data, tmp)
            ret = self._run([
                "add", "--id", "my_func", "--source", "authored",
                "--complexity", "extreme",
            ], tmp)
            self.assertNotEqual(ret, 0)
        finally:
            tmp.unlink(missing_ok=True)

    def test_add_default_state_is_pending(self) -> None:
        data = empty_tracker()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            save_tracker(data, tmp)
            self._run(["add", "--id", "pending_func", "--source", "authored"], tmp)
            loaded = load_tracker(tmp)
            row = get_candidate(loaded, "pending_func")
            assert row is not None
            self.assertEqual(workflow_state(row), "pending")
        finally:
            tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# manage_candidates update-stage1
# ---------------------------------------------------------------------------

class TestManageCandidatesUpdateStage1(unittest.TestCase):

    def _run(self, args: list[str], tracker_path: Path) -> int:
        return manage_candidates.main(["--path", str(tracker_path)] + args)

    def _tmp_tracker(self, *rows: dict):
        data = _tracker_with(*rows)
        f = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp = Path(f.name)
        f.close()
        save_tracker(data, tmp)
        return tmp

    def test_update_to_pass(self) -> None:
        tmp = self._tmp_tracker(_blank_row("func_a"))
        try:
            ret = self._run(["update-stage1", "func_a", "--result", "PASS"], tmp)
            self.assertEqual(ret, 0)
            row = get_candidate(load_tracker(tmp), "func_a")
            assert row is not None
            self.assertEqual(row["stage1_result"], "PASS")
            self.assertIsNone(row["stage1_exclusion_reason"])
        finally:
            tmp.unlink(missing_ok=True)

    def test_update_to_exclude_with_reason(self) -> None:
        tmp = self._tmp_tracker(_blank_row("func_b"))
        try:
            ret = self._run([
                "update-stage1", "func_b",
                "--result", "EXCLUDE",
                "--reason", "Single operator flip — pilot family",
            ], tmp)
            self.assertEqual(ret, 0)
            row = get_candidate(load_tracker(tmp), "func_b")
            assert row is not None
            self.assertEqual(row["stage1_result"], "EXCLUDE")
            self.assertIn("Single operator flip", row["stage1_exclusion_reason"])
        finally:
            tmp.unlink(missing_ok=True)

    def test_exclude_without_reason_fails(self) -> None:
        tmp = self._tmp_tracker(_blank_row("func_c"))
        try:
            ret = self._run(["update-stage1", "func_c", "--result", "EXCLUDE"], tmp)
            self.assertNotEqual(ret, 0)
            # Stage 1 result must not have changed
            row = get_candidate(load_tracker(tmp), "func_c")
            assert row is not None
            self.assertEqual(row["stage1_result"], "DEFER")
        finally:
            tmp.unlink(missing_ok=True)

    def test_defer_with_reason(self) -> None:
        tmp = self._tmp_tracker(_blank_row("func_d"))
        try:
            ret = self._run([
                "update-stage1", "func_d",
                "--result", "DEFER",
                "--reason", "Revisit after checking body line count",
            ], tmp)
            self.assertEqual(ret, 0)
            row = get_candidate(load_tracker(tmp), "func_d")
            assert row is not None
            self.assertEqual(row["stage1_result"], "DEFER")
            self.assertIsNotNone(row["stage1_exclusion_reason"])
            self.assertEqual(workflow_state(row), "deferred")
        finally:
            tmp.unlink(missing_ok=True)

    def test_defer_without_reason_stays_pending(self) -> None:
        tmp = self._tmp_tracker(_blank_row("func_e"))
        try:
            ret = self._run(["update-stage1", "func_e", "--result", "DEFER"], tmp)
            self.assertEqual(ret, 0)
            row = get_candidate(load_tracker(tmp), "func_e")
            assert row is not None
            self.assertEqual(workflow_state(row), "pending")
        finally:
            tmp.unlink(missing_ok=True)

    def test_invalid_result_enum_fails(self) -> None:
        tmp = self._tmp_tracker(_blank_row("func_f"))
        try:
            ret = self._run([
                "update-stage1", "func_f", "--result", "MAYBE",
            ], tmp)
            self.assertNotEqual(ret, 0)
        finally:
            tmp.unlink(missing_ok=True)

    def test_unknown_candidate_id_fails(self) -> None:
        tmp = self._tmp_tracker(_blank_row("func_g"))
        try:
            ret = self._run([
                "update-stage1", "nonexistent", "--result", "PASS",
            ], tmp)
            self.assertNotEqual(ret, 0)
        finally:
            tmp.unlink(missing_ok=True)

    def test_excluded_row_preserved_not_deleted(self) -> None:
        """After exclusion, the row must still be in the tracker."""
        tmp = self._tmp_tracker(_blank_row("func_h"), _blank_row("func_i"))
        try:
            self._run([
                "update-stage1", "func_h",
                "--result", "EXCLUDE",
                "--reason", "Too trivial.",
            ], tmp)
            loaded = load_tracker(tmp)
            self.assertIsNotNone(get_candidate(loaded, "func_h"))
            self.assertIsNotNone(get_candidate(loaded, "func_i"))
        finally:
            tmp.unlink(missing_ok=True)

    def test_pass_clears_prior_exclusion_reason(self) -> None:
        """When a candidate is set to PASS, exclusion reason should be cleared."""
        row = _blank_row("func_j")
        row["stage1_result"] = "DEFER"
        row["stage1_exclusion_reason"] = "Was deferred: check again."
        tmp = self._tmp_tracker(row)
        try:
            ret = self._run(["update-stage1", "func_j", "--result", "PASS"], tmp)
            self.assertEqual(ret, 0)
            loaded = load_tracker(tmp)
            updated = get_candidate(loaded, "func_j")
            assert updated is not None
            self.assertEqual(updated["stage1_result"], "PASS")
            self.assertIsNone(updated["stage1_exclusion_reason"])
        finally:
            tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# manage_candidates list
# ---------------------------------------------------------------------------

class TestManageCandidatesList(unittest.TestCase):

    def _run(self, args: list[str], tracker_path: Path) -> int:
        return manage_candidates.main(["--path", str(tracker_path)] + args)

    def test_list_all_returns_zero(self) -> None:
        data = _tracker_with(
            _blank_row("func_a"),
            _pass_row("func_b"),
            _excluded_row("func_c"),
            _anchor_row("clamp"),
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            save_tracker(data, tmp)
            ret = self._run(["list"], tmp)
            self.assertEqual(ret, 0)
        finally:
            tmp.unlink(missing_ok=True)

    def test_list_state_excluded(self) -> None:
        data = _tracker_with(
            _blank_row("func_a"),
            _excluded_row("func_b"),
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            save_tracker(data, tmp)
            ret = self._run(["list", "--state", "excluded"], tmp)
            self.assertEqual(ret, 0)
        finally:
            tmp.unlink(missing_ok=True)

    def test_list_state_pending(self) -> None:
        data = _tracker_with(
            _blank_row("func_a"),
            _pass_row("func_b"),
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            save_tracker(data, tmp)
            ret = self._run(["list", "--state", "pending"], tmp)
            self.assertEqual(ret, 0)
        finally:
            tmp.unlink(missing_ok=True)

    def test_list_empty_state_returns_zero(self) -> None:
        data = empty_tracker()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            save_tracker(data, tmp)
            ret = self._run(["list", "--state", "excluded"], tmp)
            self.assertEqual(ret, 0)
        finally:
            tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# manage_candidates show
# ---------------------------------------------------------------------------

class TestManageCandidatesShow(unittest.TestCase):

    def _run(self, args: list[str], tracker_path: Path) -> int:
        return manage_candidates.main(["--path", str(tracker_path)] + args)

    def test_show_existing_candidate_returns_zero(self) -> None:
        data = _tracker_with(_blank_row("func_a"))
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            save_tracker(data, tmp)
            ret = self._run(["show", "func_a"], tmp)
            self.assertEqual(ret, 0)
        finally:
            tmp.unlink(missing_ok=True)

    def test_show_nonexistent_candidate_fails(self) -> None:
        data = empty_tracker()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            save_tracker(data, tmp)
            ret = self._run(["show", "nonexistent"], tmp)
            self.assertNotEqual(ret, 0)
        finally:
            tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# manage_candidates validate
# ---------------------------------------------------------------------------

class TestManageCandidatesValidate(unittest.TestCase):

    def _run(self, args: list[str], tracker_path: Path) -> int:
        return manage_candidates.main(["--path", str(tracker_path)] + args)

    def test_validate_valid_tracker(self) -> None:
        data = _tracker_with(
            _blank_row("func_a"),
            _pass_row("func_b"),
            _anchor_row("clamp"),
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            save_tracker(data, tmp)
            ret = self._run(["validate"], tmp)
            self.assertEqual(ret, 0)
        finally:
            tmp.unlink(missing_ok=True)

    def test_validate_committed_tracker(self) -> None:
        """The checked-in candidates.json must pass validation."""
        p = default_tracker_path()
        if not p.exists():
            self.skipTest("candidates.json not found")
        ret = manage_candidates.main(["validate"])
        self.assertEqual(ret, 0)


# ---------------------------------------------------------------------------
# Workflow state and summary consistency
# ---------------------------------------------------------------------------

class TestWorkflowConsistency(unittest.TestCase):

    def test_workflow_summary_counts_match_total(self) -> None:
        data = _tracker_with(
            _anchor_row("clamp"),
            _blank_row("func_a"),           # pending
            _excluded_row("func_b"),         # excluded
            _pass_row("func_c"),             # pass-blocked (not in real manifest)
        )
        ws = workflow_summary(data)
        state_total = sum(ws["state_counts"].values())
        self.assertEqual(state_total, ws["total"])

    def test_pending_and_deferred_are_distinct(self) -> None:
        """DEFER with no reason = pending; DEFER with reason = deferred."""
        r_pending = _blank_row("func_p")
        r_deferred = _blank_row("func_d")
        r_deferred["stage1_exclusion_reason"] = "Check later"
        data = _tracker_with(r_pending, r_deferred)
        ws = workflow_summary(data)
        self.assertEqual(ws["state_counts"].get("pending", 0), 1)
        self.assertEqual(ws["state_counts"].get("deferred", 0), 1)

    def test_anchor_not_in_pass_blocked(self) -> None:
        data = _tracker_with(_anchor_row("clamp"))
        ws = workflow_summary(data)
        blocked_ids = [b["candidate_id"] for b in ws["pass_blocked"]]
        self.assertNotIn("clamp", blocked_ids)

    def test_excluded_not_in_pass_blocked(self) -> None:
        data = _tracker_with(_excluded_row("bad_func"))
        ws = workflow_summary(data)
        blocked_ids = [b["candidate_id"] for b in ws["pass_blocked"]]
        self.assertNotIn("bad_func", blocked_ids)


# ---------------------------------------------------------------------------
# End-to-end: add -> stage1-pass -> show -> workflow state
# ---------------------------------------------------------------------------

class TestEndToEndManage(unittest.TestCase):

    def test_full_intake_lifecycle(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        tmp.unlink()

        # Step 1: init
        from experiment import init_candidates
        ret = init_candidates.main(["--path", str(tmp), "--seed-anchors"])
        self.assertEqual(ret, 0)

        # Step 2: add a candidate
        ret = manage_candidates.main([
            "--path", str(tmp),
            "add", "--id", "hard_func",
            "--source", "authored",
            "--lines", "18",
            "--complexity", "medium",
            "--t2-family", "state_mutation_ordering",
        ])
        self.assertEqual(ret, 0)
        data = load_tracker(tmp)
        row = get_candidate(data, "hard_func")
        assert row is not None
        self.assertEqual(row["stage1_result"], "DEFER")
        self.assertEqual(workflow_state(row), "pending")

        # Step 3: exclude a different function
        ret = manage_candidates.main([
            "--path", str(tmp),
            "add", "--id", "trivial_func", "--source", "stdlib",
        ])
        self.assertEqual(ret, 0)
        ret = manage_candidates.main([
            "--path", str(tmp),
            "update-stage1", "trivial_func",
            "--result", "EXCLUDE",
            "--reason", "Single operator flip",
        ])
        self.assertEqual(ret, 0)
        # Excluded row still exists
        data = load_tracker(tmp)
        excl = get_candidate(data, "trivial_func")
        assert excl is not None
        self.assertEqual(excl["stage1_result"], "EXCLUDE")

        # Step 4: pass the hard_func
        ret = manage_candidates.main([
            "--path", str(tmp),
            "update-stage1", "hard_func", "--result", "PASS",
        ])
        self.assertEqual(ret, 0)
        data = load_tracker(tmp)
        row = get_candidate(data, "hard_func")
        assert row is not None
        self.assertEqual(row["stage1_result"], "PASS")
        # Still blocked: hard_func is not in the real manifest
        self.assertIn(workflow_state(row), ("pass-blocked", "pass-ready"))

        # Step 5: validate whole tracker
        ret = manage_candidates.main(["--path", str(tmp), "validate"])
        self.assertEqual(ret, 0)

        tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
