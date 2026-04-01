"""Tests for the automation/ orchestration scaffold.

Covers:
- Schema files: valid JSON, required fields present
- Template files: required placeholders present, load without error
- State I/O: session save/load round-trip, archive function
- Template rendering: placeholder substitution, no crash on partial context
- Controller commands: plan/prompt/review/handoff/next/ingest run without crashing
  (using LUMEN_EXECUTOR=mock so no API keys are required)
- Executor mock mode: returns stub response
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

# Make automation/ importable
AUTO_DIR = Path(__file__).resolve().parent.parent / "automation"
if str(AUTO_DIR) not in sys.path:
    sys.path.insert(0, str(AUTO_DIR))

import executor
import lumen


SCHEMAS_DIR = AUTO_DIR / "schemas"
TEMPLATES_DIR = AUTO_DIR / "templates"

REQUIRED_SCHEMAS = [
    "task_brief.json",
    "structure_design.json",
    "execution_prompt.json",
    "execution_result.json",
    "next_steps.json",
    "handoff_summary.json",
]

REQUIRED_TEMPLATES = [
    "plan.md",
    "prompt.md",
    "review.md",
    "next.md",
    "handoff.md",
]

# Placeholder keys that must appear in each template
TEMPLATE_REQUIRED_KEYS: dict[str, list[str]] = {
    "plan.md":    ["{task_brief}", "{repo_context}", "{date}", "{session_id}"],
    "prompt.md":  ["{task_brief}", "{structure_design}", "{target_model}", "{date}"],
    "review.md":  ["{execution_result}", "{task_brief}", "{date}", "{session_id}"],
    "next.md":    ["{task_brief}", "{structure_design}", "{date}"],
    "handoff.md": ["{session_id}", "{task_brief}", "{date}", "{current_phase}"],
}


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestSchemas(unittest.TestCase):

    def test_all_required_schemas_exist(self) -> None:
        for name in REQUIRED_SCHEMAS:
            path = SCHEMAS_DIR / name
            self.assertTrue(path.exists(), f"Missing schema: {path}")

    def test_all_schemas_are_valid_json(self) -> None:
        for name in REQUIRED_SCHEMAS:
            path = SCHEMAS_DIR / name
            if not path.exists():
                self.skipTest(f"Schema missing: {name}")
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                self.fail(f"Schema {name} is not valid JSON: {e}")
            self.assertIsInstance(data, dict, f"Schema {name} top level must be a dict")

    def test_schemas_have_schema_id(self) -> None:
        for name in REQUIRED_SCHEMAS:
            path = SCHEMAS_DIR / name
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("schema_id", data, f"Schema {name} missing 'schema_id'")

    def test_task_brief_has_blank_template(self) -> None:
        path = SCHEMAS_DIR / "task_brief.json"
        if not path.exists():
            self.skipTest("task_brief.json not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("blank_template", data,
                      "task_brief.json must have 'blank_template' for cmd_init")
        self.assertIsInstance(data["blank_template"], str)
        self.assertGreater(len(data["blank_template"]), 10)


# ---------------------------------------------------------------------------
# Template tests
# ---------------------------------------------------------------------------

class TestTemplates(unittest.TestCase):

    def test_all_required_templates_exist(self) -> None:
        for name in REQUIRED_TEMPLATES:
            path = TEMPLATES_DIR / name
            self.assertTrue(path.exists(), f"Missing template: {path}")

    def test_templates_are_non_empty(self) -> None:
        for name in REQUIRED_TEMPLATES:
            path = TEMPLATES_DIR / name
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            self.assertGreater(len(content.strip()), 50,
                               f"Template {name} is suspiciously short")

    def test_template_required_placeholders_present(self) -> None:
        for name, keys in TEMPLATE_REQUIRED_KEYS.items():
            path = TEMPLATES_DIR / name
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            for key in keys:
                self.assertIn(key, content,
                              f"Template {name} missing placeholder {key}")

    def test_load_template_success(self) -> None:
        for name in REQUIRED_TEMPLATES:
            stem = Path(name).stem
            path = TEMPLATES_DIR / name
            if not path.exists():
                continue
            try:
                text = lumen.load_template(stem)
            except Exception as e:
                self.fail(f"load_template({stem!r}) raised: {e}")
            self.assertIsInstance(text, str)
            self.assertGreater(len(text), 0)

    def test_load_template_missing_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            lumen.load_template("nonexistent_template_xyz")


# ---------------------------------------------------------------------------
# Template rendering tests
# ---------------------------------------------------------------------------

class TestRendering(unittest.TestCase):

    def test_render_substitutes_placeholders(self) -> None:
        template = "Hello {name}, today is {date}."
        result = lumen.render(template, {"name": "World", "date": "2026-01-01"})
        self.assertEqual(result, "Hello World, today is 2026-01-01.")

    def test_render_leaves_missing_keys_as_is(self) -> None:
        template = "Value: {present} and {missing}."
        result = lumen.render(template, {"present": "yes"})
        self.assertIn("yes", result)
        self.assertIn("{missing}", result)

    def test_render_safe_with_braces_in_content(self) -> None:
        # JSON-like content in a task brief must not break rendering
        template = "{task_brief}"
        content = '{"key": "value", "list": [1, 2, 3]}'
        result = lumen.render(template, {"task_brief": content})
        self.assertEqual(result, content)

    def test_render_plan_template_no_crash(self) -> None:
        path = TEMPLATES_DIR / "plan.md"
        if not path.exists():
            self.skipTest("plan.md not found")
        template = path.read_text(encoding="utf-8")
        ctx = {
            "task_brief": "Test task",
            "repo_context": "Repo: Test",
            "session_id": "test_session",
            "date": "2026-01-01",
            "constraints": "None",
            "previous_decisions": "None",
        }
        result = lumen.render(template, ctx)
        self.assertIsInstance(result, str)
        self.assertNotIn("{task_brief}", result)

    def test_render_handoff_template_no_crash(self) -> None:
        path = TEMPLATES_DIR / "handoff.md"
        if not path.exists():
            self.skipTest("handoff.md not found")
        template = path.read_text(encoding="utf-8")
        ctx = {
            "session_id": "test_123",
            "created": "2026-01-01T00:00:00Z",
            "date": "2026-01-01",
            "current_phase": "review",
            "task_history_count": "3",
            "history_artifact_count": "12",
            "task_brief": "Test brief",
            "structure_design": "Test design",
            "execution_result": "Test result",
            "next_steps": "Test next",
            "constraints": "None",
            "repo_context": "Repo: Test",
        }
        result = lumen.render(template, ctx)
        self.assertIsInstance(result, str)
        self.assertNotIn("{session_id}", result)


# ---------------------------------------------------------------------------
# State I/O tests
# ---------------------------------------------------------------------------

class TestStateIO(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_save_load_json_roundtrip(self) -> None:
        path = self.tmp_path / "test.json"
        data = {"a": 1, "b": [1, 2, 3], "c": {"nested": True}}
        lumen.save_json(path, data)
        loaded = lumen.load_json(path)
        self.assertEqual(loaded, data)

    def test_load_json_missing_returns_empty(self) -> None:
        path = self.tmp_path / "does_not_exist.json"
        result = lumen.load_json(path)
        self.assertEqual(result, {})

    def test_save_load_text_roundtrip(self) -> None:
        path = self.tmp_path / "test.md"
        content = "# Hello\n\nThis is a test.\n"
        lumen.save_text(path, content)
        loaded = lumen.load_text(path)
        self.assertEqual(loaded, content)

    def test_load_text_missing_returns_empty_string(self) -> None:
        path = self.tmp_path / "does_not_exist.md"
        result = lumen.load_text(path)
        self.assertEqual(result, "")

    def test_save_json_creates_parent_dirs(self) -> None:
        path = self.tmp_path / "deep" / "nested" / "file.json"
        lumen.save_json(path, {"x": 1})
        self.assertTrue(path.exists())

    def test_save_text_creates_parent_dirs(self) -> None:
        path = self.tmp_path / "deep" / "nested" / "file.md"
        lumen.save_text(path, "content")
        self.assertTrue(path.exists())

    def test_archive_writes_timestamped_file(self) -> None:
        # Temporarily redirect HISTORY_DIR
        original = lumen.HISTORY_DIR
        lumen.HISTORY_DIR = self.tmp_path / "history"
        try:
            dest = lumen.archive("sess_001", "test.md", "Hello archive")
            self.assertTrue(dest.exists())
            self.assertIn("test.md", dest.name)
            self.assertEqual(dest.read_text(encoding="utf-8"), "Hello archive")
        finally:
            lumen.HISTORY_DIR = original

    def test_extract_title_h1(self) -> None:
        path = self.tmp_path / "brief.md"
        path.write_text("# My Task Title\n\nSome content.\n")
        self.assertEqual(lumen.extract_title(path), "My Task Title")

    def test_extract_title_first_line(self) -> None:
        path = self.tmp_path / "brief.md"
        path.write_text("Plain first line\n\nMore content.\n")
        self.assertEqual(lumen.extract_title(path), "Plain first line")

    def test_extract_title_missing_file(self) -> None:
        path = self.tmp_path / "missing.md"
        self.assertEqual(lumen.extract_title(path), "unnamed")


# ---------------------------------------------------------------------------
# Executor tests
# ---------------------------------------------------------------------------

class TestExecutorMock(unittest.TestCase):

    def test_mock_mode_returns_string(self) -> None:
        result = executor.call("test prompt", model_id="sonnet", mode="mock")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_mock_mode_contains_marker(self) -> None:
        result = executor.call("test prompt", model_id="sonnet", mode="mock")
        self.assertIn("mock mode", result.lower())

    def test_mock_mode_includes_model_id(self) -> None:
        result = executor.call("test prompt", model_id="claude-sonnet-4-6", mode="mock")
        self.assertIn("claude-sonnet-4-6", result)

    def test_mock_mode_via_env_var(self) -> None:
        original = os.environ.get("LUMEN_EXECUTOR")
        os.environ["LUMEN_EXECUTOR"] = "mock"
        try:
            result = executor.call("test prompt", model_id="opus")
            self.assertIn("mock", result.lower())
        finally:
            if original is None:
                os.environ.pop("LUMEN_EXECUTOR", None)
            else:
                os.environ["LUMEN_EXECUTOR"] = original

    def test_resolve_model_id_key(self) -> None:
        result = executor._resolve_model_id("sonnet")
        # Should resolve to the model_id string (not crash if config exists)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_resolve_model_id_bare(self) -> None:
        result = executor._resolve_model_id("claude-sonnet-4-6")
        self.assertEqual(result, "claude-sonnet-4-6")

    def test_invalid_mode_raises(self) -> None:
        with self.assertRaises(ValueError):
            executor.call("test", model_id="sonnet", mode="invalid_mode_xyz")


# ---------------------------------------------------------------------------
# Controller command tests (all using mock executor)
# ---------------------------------------------------------------------------

class TestControllerCommands(unittest.TestCase):
    """Test that CLI commands run to completion in a temporary state directory."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

        # Redirect state and history to temp dirs
        self._orig_state = lumen.STATE_DIR
        self._orig_history = lumen.HISTORY_DIR
        lumen.STATE_DIR = self.tmp_path / "state"
        lumen.HISTORY_DIR = self.tmp_path / "history"
        lumen.STATE_DIR.mkdir(parents=True)
        lumen.HISTORY_DIR.mkdir(parents=True)

        # Force mock execution mode
        self._orig_executor = os.environ.get("LUMEN_EXECUTOR")
        os.environ["LUMEN_EXECUTOR"] = "mock"

    def tearDown(self) -> None:
        lumen.STATE_DIR = self._orig_state
        lumen.HISTORY_DIR = self._orig_history
        if self._orig_executor is None:
            os.environ.pop("LUMEN_EXECUTOR", None)
        else:
            os.environ["LUMEN_EXECUTOR"] = self._orig_executor
        self.tmp.cleanup()

    def _init_session(self) -> None:
        """Run init with force to create a clean session."""
        import argparse
        args = argparse.Namespace(force=True)
        lumen.cmd_init(args)

    def test_init_creates_session_json(self) -> None:
        self._init_session()
        session_file = lumen.STATE_DIR / "session.json"
        self.assertTrue(session_file.exists())
        data = json.loads(session_file.read_text())
        self.assertIn("session_id", data)
        self.assertEqual(data["phase"], "intake")

    def test_init_creates_task_brief(self) -> None:
        self._init_session()
        brief = lumen.STATE_DIR / "task_brief.md"
        self.assertTrue(brief.exists())
        content = brief.read_text(encoding="utf-8")
        self.assertIn("Task Brief", content)

    def test_status_no_session(self) -> None:
        import argparse
        import io
        args = argparse.Namespace()
        # Should not crash; should print helpful message
        with unittest.mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            lumen.cmd_status(args)
            output = mock_out.getvalue()
        self.assertIn("No active session", output)

    def test_plan_renders_to_state(self) -> None:
        self._init_session()
        import argparse, io
        args = argparse.Namespace(execute=False, model=None)
        with unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            lumen.cmd_plan(args)
        plan_prompt = lumen.STATE_DIR / "plan_prompt.md"
        self.assertTrue(plan_prompt.exists())
        content = plan_prompt.read_text(encoding="utf-8")
        self.assertGreater(len(content), 50)

    def test_plan_advances_phase(self) -> None:
        self._init_session()
        import argparse, io
        args = argparse.Namespace(execute=False, model=None)
        with unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            lumen.cmd_plan(args)
        session = lumen.load_session()
        self.assertEqual(session["phase"], "planning")

    def test_plan_execute_mock_saves_structure_design(self) -> None:
        self._init_session()
        import argparse, io
        args = argparse.Namespace(execute=True, model="sonnet")
        with unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            lumen.cmd_plan(args)
        design = lumen.STATE_DIR / "structure_design.md"
        self.assertTrue(design.exists())
        content = design.read_text(encoding="utf-8")
        self.assertIn("mock", content.lower())

    def test_prompt_renders_to_state(self) -> None:
        self._init_session()
        import argparse, io
        args = argparse.Namespace(execute=False, model="sonnet")
        with unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            lumen.cmd_prompt(args)
        out = lumen.STATE_DIR / "prompt_prompt.md"
        self.assertTrue(out.exists())

    def test_ingest_saves_result(self) -> None:
        self._init_session()
        result_file = self.tmp_path / "result.md"
        result_file.write_text("# Execution Result\n\nAll done.\n", encoding="utf-8")
        import argparse, io
        args = argparse.Namespace(file=str(result_file))
        with unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            lumen.cmd_ingest(args)
        saved = lumen.STATE_DIR / "execution_result.md"
        self.assertTrue(saved.exists())
        self.assertIn("All done.", saved.read_text(encoding="utf-8"))

    def test_ingest_advances_phase(self) -> None:
        self._init_session()
        result_file = self.tmp_path / "result.md"
        result_file.write_text("done\n", encoding="utf-8")
        import argparse, io
        args = argparse.Namespace(file=str(result_file))
        with unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            lumen.cmd_ingest(args)
        self.assertEqual(lumen.load_session()["phase"], "result_ingest")

    def test_review_renders_to_state(self) -> None:
        self._init_session()
        import argparse, io
        args = argparse.Namespace(execute=False, model=None)
        with unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            lumen.cmd_review(args)
        out = lumen.STATE_DIR / "review_prompt.md"
        self.assertTrue(out.exists())

    def test_review_execute_mock_saves_review(self) -> None:
        self._init_session()
        import argparse, io
        args = argparse.Namespace(execute=True, model="sonnet")
        with unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            lumen.cmd_review(args)
        review = lumen.STATE_DIR / "review.md"
        self.assertTrue(review.exists())

    def test_next_renders_to_state(self) -> None:
        self._init_session()
        import argparse, io
        args = argparse.Namespace(execute=False, model=None)
        with unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            lumen.cmd_next(args)
        out = lumen.STATE_DIR / "next_prompt.md"
        self.assertTrue(out.exists())

    def test_handoff_renders_to_state(self) -> None:
        self._init_session()
        import argparse, io
        args = argparse.Namespace(execute=False, model=None)
        with unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            lumen.cmd_handoff(args)
        out = lumen.STATE_DIR / "handoff_prompt.md"
        self.assertTrue(out.exists())

    def test_handoff_execute_mock_saves_summary(self) -> None:
        self._init_session()
        import argparse, io
        args = argparse.Namespace(execute=True, model="sonnet")
        with unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            lumen.cmd_handoff(args)
        out = lumen.STATE_DIR / "handoff_summary.md"
        self.assertTrue(out.exists())

    def test_history_archives_are_created(self) -> None:
        self._init_session()
        session = lumen.load_session()
        sid = session["session_id"]
        import argparse, io
        args = argparse.Namespace(execute=False, model=None)
        with unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            lumen.cmd_plan(args)
        history_dir = lumen.HISTORY_DIR / sid
        self.assertTrue(history_dir.exists())
        files = list(history_dir.glob("*"))
        self.assertGreater(len(files), 0)

    def test_require_session_raises_without_session(self) -> None:
        with self.assertRaises(SystemExit):
            lumen.require_session()


# ---------------------------------------------------------------------------
# End-to-end minimal loop test
# ---------------------------------------------------------------------------

class TestEndToEndLoop(unittest.TestCase):
    """Verify that the full plan → prompt → ingest → review → next loop
    runs cleanly in mock mode and produces all expected state artifacts."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self._orig_state = lumen.STATE_DIR
        self._orig_history = lumen.HISTORY_DIR
        lumen.STATE_DIR = self.tmp_path / "state"
        lumen.HISTORY_DIR = self.tmp_path / "history"
        lumen.STATE_DIR.mkdir(parents=True)
        lumen.HISTORY_DIR.mkdir(parents=True)
        self._orig_executor = os.environ.get("LUMEN_EXECUTOR")
        os.environ["LUMEN_EXECUTOR"] = "mock"

    def tearDown(self) -> None:
        lumen.STATE_DIR = self._orig_state
        lumen.HISTORY_DIR = self._orig_history
        if self._orig_executor is None:
            os.environ.pop("LUMEN_EXECUTOR", None)
        else:
            os.environ["LUMEN_EXECUTOR"] = self._orig_executor
        self.tmp.cleanup()

    def test_full_loop_plan_to_handoff(self) -> None:
        import argparse
        import io
        import unittest.mock

        null_out = io.StringIO()

        # 1. init
        with unittest.mock.patch("sys.stdout", null_out):
            lumen.cmd_init(argparse.Namespace(force=True))
        self.assertTrue((lumen.STATE_DIR / "session.json").exists())

        # Write a task brief
        lumen.save_text(
            lumen.STATE_DIR / "task_brief.md",
            "# Add T1 checklists for wave2 functions\n\n"
            "## Goal\nCreate T1 property checklists for the 10 wave2 functions.\n",
        )

        # 2. plan (execute=True, mock)
        with unittest.mock.patch("sys.stdout", null_out):
            lumen.cmd_plan(argparse.Namespace(execute=True, model="sonnet"))
        self.assertTrue((lumen.STATE_DIR / "structure_design.md").exists())

        # 3. prompt (execute=True, mock)
        with unittest.mock.patch("sys.stdout", null_out):
            lumen.cmd_prompt(argparse.Namespace(execute=True, model="sonnet"))
        self.assertTrue((lumen.STATE_DIR / "execution_prompt.md").exists())

        # 4. ingest a synthetic result
        result_file = self.tmp_path / "result.md"
        result_file.write_text(
            "# Execution Result\n\n"
            "Created 10 T1 checklists. All match t1-checklist-v1 schema.\n",
            encoding="utf-8",
        )
        with unittest.mock.patch("sys.stdout", null_out):
            lumen.cmd_ingest(argparse.Namespace(file=str(result_file)))
        self.assertTrue((lumen.STATE_DIR / "execution_result.md").exists())

        # 5. review (execute=True, mock)
        with unittest.mock.patch("sys.stdout", null_out):
            lumen.cmd_review(argparse.Namespace(execute=True, model="sonnet"))
        self.assertTrue((lumen.STATE_DIR / "review.md").exists())

        # 6. next (execute=True, mock)
        with unittest.mock.patch("sys.stdout", null_out):
            lumen.cmd_next(argparse.Namespace(execute=True, model="sonnet"))
        self.assertTrue((lumen.STATE_DIR / "next_steps.md").exists())

        # 7. handoff (execute=True, mock)
        with unittest.mock.patch("sys.stdout", null_out):
            lumen.cmd_handoff(argparse.Namespace(execute=True, model="sonnet"))
        self.assertTrue((lumen.STATE_DIR / "handoff_summary.md").exists())

        # Verify session history has one completed task
        session = lumen.load_session()
        self.assertEqual(len(session["task_history"]), 1)
        self.assertEqual(session["phase"], "handoff")

        # Verify history dir has artifacts
        sid = session["session_id"]
        history_files = list((lumen.HISTORY_DIR / sid).glob("*"))
        self.assertGreaterEqual(len(history_files), 5,
                                f"Expected ≥5 history files, got {len(history_files)}")


# ---------------------------------------------------------------------------
# Model config tests
# ---------------------------------------------------------------------------

class TestModelConfig(unittest.TestCase):

    def test_models_json_exists(self) -> None:
        path = AUTO_DIR / "config" / "models.json"
        self.assertTrue(path.exists(), "automation/config/models.json must exist")

    def test_models_json_valid(self) -> None:
        path = AUTO_DIR / "config" / "models.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("defaults", data)
        self.assertIn("models", data)

    def test_all_model_keys_have_model_id(self) -> None:
        path = AUTO_DIR / "config" / "models.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for key, entry in data.get("models", {}).items():
            self.assertIn("model_id", entry, f"Model '{key}' missing 'model_id'")
            self.assertIsInstance(entry["model_id"], str)

    def test_default_roles_point_to_valid_keys(self) -> None:
        path = AUTO_DIR / "config" / "models.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        models = data.get("models", {})
        for role, key in data.get("defaults", {}).items():
            self.assertIn(key, models,
                          f"defaults.{role} = '{key}' but '{key}' not in models")

    def test_resolve_model_id_via_lumen(self) -> None:
        cfg = lumen.load_model_config()
        resolved = lumen.resolve_model_id("sonnet", cfg)
        self.assertIsNotNone(resolved)
        self.assertIn("claude", resolved)

    def test_resolve_bare_model_id(self) -> None:
        cfg = lumen.load_model_config()
        resolved = lumen.resolve_model_id("claude-opus-4-6", cfg)
        self.assertEqual(resolved, "claude-opus-4-6")


if __name__ == "__main__":
    # Allow running directly: python tests/test_automation.py
    import unittest
    unittest.main()
