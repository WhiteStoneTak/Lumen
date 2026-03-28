"""Tests for the Lumen pilot experiment runner (src/experiment/runner.py).

Coverage:
1. plan_experiment_items — full pilot count (all 3 funcs × 5 conditions for T1/T2/T3 = 39)
2. plan_experiment_items — filters by func_id
3. plan_experiment_items — filters by task
4. plan_experiment_items — T1/T2/T3 all appear when available
5. slugify_model — safe filename output
6. resolve_representation_artifact — C1 returns raw Python
7. resolve_representation_artifact — C2 returns JSON string with ast-v1 schema
8. resolve_representation_artifact — C4 returns JSON string with ir-v1 schema
9. build_task_prompt — prompt_version constant embedded in T1 prompt
10. build_task_prompt — representation content is embedded
11. build_task_prompt — T2 prompt contains "bug"
12. build_task_prompt — T1 wording is identical across C1 and C2 (only content differs)
13. dispatch_scorer — T1 returns scorer-result-v1 dict
14. dispatch_scorer — T2 returns scorer-result-v1 dict
15. dispatch_scorer — T3 returns scorer-result-v1 dict
16. run_pilot_experiment — dry_run=True produces planned items without error
17. resolve_representation_artifact — T2 non-C1 returns buggy artifact paths
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from experiment.contracts import load_dataset_manifest, repo_root  # noqa: E402
from experiment.runner import (  # noqa: E402
    PROMPT_VERSION,
    build_task_prompt,
    dispatch_scorer,
    plan_experiment_items,
    resolve_representation_artifact,
    run_pilot_experiment,
    slugify_model,
)


# ---------------------------------------------------------------------------
# Planning tests
# ---------------------------------------------------------------------------

class RunnerPlanningTests(unittest.TestCase):

    def setUp(self) -> None:
        self.manifest = load_dataset_manifest(check_paths=True)

    def test_plan_all_pilot_items_not_empty(self) -> None:
        items = plan_experiment_items(self.manifest, models=["test-model"])
        self.assertGreater(len(items), 0)

    def test_plan_all_pilot_items_expected_count(self) -> None:
        # 3 funcs × T1 × 5 conditions = 15
        # 3 funcs × T2 × 5 conditions = 15  (T2 now fully crossed)
        # 3 funcs × T3 × 5 conditions = 15
        # total = 45 per model
        items = plan_experiment_items(self.manifest, models=["test-model"])
        self.assertEqual(len(items), 45)

    def test_plan_two_models_doubles_count(self) -> None:
        items = plan_experiment_items(self.manifest, models=["m1", "m2"])
        self.assertEqual(len(items), 90)

    def test_plan_filters_by_func_id(self) -> None:
        items = plan_experiment_items(
            self.manifest, models=["m"], func_ids=["clamp"]
        )
        self.assertTrue(all(i["func_id"] == "clamp" for i in items))
        self.assertGreater(len(items), 0)

    def test_plan_filters_by_task(self) -> None:
        items = plan_experiment_items(self.manifest, models=["m"], tasks=["T1"])
        self.assertTrue(all(i["task"] == "T1" for i in items))
        self.assertGreater(len(items), 0)

    def test_plan_filters_by_condition(self) -> None:
        items = plan_experiment_items(
            self.manifest, models=["m"], conditions=["C1"]
        )
        self.assertTrue(all(i["condition"] == "C1" for i in items))

    def test_plan_respects_task_availability(self) -> None:
        items = plan_experiment_items(self.manifest, models=["m"])
        tasks = {i["task"] for i in items}
        self.assertIn("T1", tasks)
        self.assertIn("T2", tasks)
        self.assertIn("T3", tasks)

    def test_plan_t2_all_five_conditions(self) -> None:
        items = plan_experiment_items(self.manifest, models=["m"])
        t2_items = [i for i in items if i["task"] == "T2"]
        t2_conditions = {i["condition"] for i in t2_items}
        self.assertEqual(
            t2_conditions,
            {"C1", "C1+", "C2", "C3", "C4"},
            "T2 should be fully crossed with all 5 conditions",
        )

    def test_plan_t2_count_per_func(self) -> None:
        items = plan_experiment_items(self.manifest, models=["m"])
        for func_id in ("clamp", "count_vowels", "is_sorted"):
            t2_func_items = [i for i in items if i["task"] == "T2" and i["func_id"] == func_id]
            self.assertEqual(
                len(t2_func_items), 5,
                f"Expected 5 T2 items for {func_id} (one per condition), got {len(t2_func_items)}",
            )

    def test_plan_item_has_required_keys(self) -> None:
        items = plan_experiment_items(
            self.manifest, models=["m"], func_ids=["clamp"], tasks=["T1"], conditions=["C1"]
        )
        self.assertEqual(len(items), 1)
        item = items[0]
        for key in ("func_id", "task", "condition", "model"):
            self.assertIn(key, item)

    def test_slugify_model_passthrough(self) -> None:
        self.assertEqual(slugify_model("claude-sonnet-4-6"), "claude-sonnet-4-6")

    def test_slugify_model_replaces_slash(self) -> None:
        self.assertEqual(slugify_model("openai/gpt-4"), "openai_gpt-4")

    def test_slugify_model_replaces_colon(self) -> None:
        self.assertEqual(slugify_model("provider:model-v1"), "provider_model-v1")

    def test_slugify_model_replaces_both(self) -> None:
        self.assertEqual(slugify_model("a/b:c"), "a_b_c")


# ---------------------------------------------------------------------------
# Representation resolver tests
# ---------------------------------------------------------------------------

class RunnerRepresentationTests(unittest.TestCase):

    def setUp(self) -> None:
        self.manifest = load_dataset_manifest(check_paths=True)

    def test_resolve_c1_returns_raw_python(self) -> None:
        art = resolve_representation_artifact("clamp", "C1", self.manifest)
        self.assertIsNotNone(art)
        self.assertIn("def clamp", art["content"])

    def test_resolve_c1plus_returns_annotated_text(self) -> None:
        art = resolve_representation_artifact("clamp", "C1+", self.manifest)
        self.assertIsNotNone(art)
        self.assertIn("def clamp", art["content"])

    def test_resolve_c2_returns_json_string(self) -> None:
        art = resolve_representation_artifact("clamp", "C2", self.manifest)
        self.assertIsNotNone(art)
        parsed = json.loads(art["content"])
        self.assertEqual(parsed.get("lumen_schema"), "ast-v1")

    def test_resolve_c3_returns_typed_ast_json(self) -> None:
        art = resolve_representation_artifact("clamp", "C3", self.manifest)
        self.assertIsNotNone(art)
        parsed = json.loads(art["content"])
        self.assertEqual(parsed.get("lumen_schema"), "typed_ast-v1")

    def test_resolve_c4_returns_ir_json(self) -> None:
        art = resolve_representation_artifact("clamp", "C4", self.manifest)
        self.assertIsNotNone(art)
        parsed = json.loads(art["content"])
        self.assertEqual(parsed.get("lumen_schema"), "ir-v1")

    def test_resolve_t2_c1_returns_buggy_source(self) -> None:
        art = resolve_representation_artifact("clamp", "C1", self.manifest, task="T2")
        self.assertIsNotNone(art)
        self.assertEqual(art.get("note"), "buggy_source")
        # Buggy source should contain a bug — 'value < hi' instead of 'value > hi'
        self.assertIn("def clamp", art["content"])

    def test_resolve_t2_c1plus_returns_buggy_annotated_text(self) -> None:
        art = resolve_representation_artifact("clamp", "C1+", self.manifest, task="T2")
        self.assertIsNotNone(art, "T2/C1+ should return a buggy annotated text artifact")
        self.assertEqual(art.get("note"), "buggy_source")
        self.assertIn("data/functions/annotated_text/clamp_buggy.py", art["path"])
        self.assertIn("def clamp", art["content"])

    def test_resolve_t2_c2_returns_buggy_ast_json(self) -> None:
        art = resolve_representation_artifact("clamp", "C2", self.manifest, task="T2")
        self.assertIsNotNone(art, "T2/C2 should return a buggy AST artifact")
        self.assertEqual(art.get("note"), "buggy_source")
        self.assertIn("clamp_buggy.json", art["path"])
        parsed = json.loads(art["content"])
        self.assertEqual(parsed.get("lumen_schema"), "ast-v1")

    def test_resolve_t2_c3_returns_buggy_typed_ast_json(self) -> None:
        art = resolve_representation_artifact("clamp", "C3", self.manifest, task="T2")
        self.assertIsNotNone(art, "T2/C3 should return a buggy typed AST artifact")
        self.assertEqual(art.get("note"), "buggy_source")
        self.assertIn("clamp_buggy.json", art["path"])
        parsed = json.loads(art["content"])
        self.assertEqual(parsed.get("lumen_schema"), "typed_ast-v1")

    def test_resolve_t2_c4_returns_buggy_ir_json(self) -> None:
        art = resolve_representation_artifact("clamp", "C4", self.manifest, task="T2")
        self.assertIsNotNone(art, "T2/C4 should return a buggy IR artifact")
        self.assertEqual(art.get("note"), "buggy_source")
        self.assertIn("clamp_buggy.json", art["path"])
        parsed = json.loads(art["content"])
        self.assertEqual(parsed.get("lumen_schema"), "ir-v1")

    def test_resolve_t2_c4_uses_correct_contracts(self) -> None:
        """C4 buggy IR must carry correct reviewed contracts (specification)."""
        art = resolve_representation_artifact("clamp", "C4", self.manifest, task="T2")
        self.assertIsNotNone(art)
        parsed = json.loads(art["content"])
        contracts = parsed.get("contracts", {})
        self.assertGreater(len(contracts.get("postconditions", [])), 0,
                           "C4 buggy IR must have non-empty postconditions (correct contracts)")

    def test_resolve_t2_non_c1_all_funcs(self) -> None:
        """All 3 pilot functions return non-None for T2 non-C1 conditions."""
        for func_id in ("clamp", "count_vowels", "is_sorted"):
            for cond in ("C1+", "C2", "C3", "C4"):
                art = resolve_representation_artifact(func_id, cond, self.manifest, task="T2")
                self.assertIsNotNone(
                    art,
                    f"Expected artifact for T2/{cond}/{func_id}, got None",
                )

    def test_resolve_c2_content_is_valid_json(self) -> None:
        for func_id in ("clamp", "count_vowels", "is_sorted"):
            art = resolve_representation_artifact(func_id, "C2", self.manifest)
            self.assertIsNotNone(art)
            # Should not raise
            json.loads(art["content"])


# ---------------------------------------------------------------------------
# Prompt builder tests
# ---------------------------------------------------------------------------

class RunnerPromptTests(unittest.TestCase):

    def setUp(self) -> None:
        self.manifest = load_dataset_manifest(check_paths=True)
        self.c1_art = resolve_representation_artifact("clamp", "C1", self.manifest)
        self.c2_art = resolve_representation_artifact("clamp", "C2", self.manifest)
        self.c1_content = self.c1_art["content"]
        self.c2_content = self.c2_art["content"]

    def test_t1_prompt_contains_prompt_version(self) -> None:
        p = build_task_prompt("clamp", "T1", "C1", self.c1_content, {})
        self.assertIn(PROMPT_VERSION, p)

    def test_t1_prompt_contains_representation_content(self) -> None:
        p = build_task_prompt("clamp", "T1", "C1", self.c1_content, {})
        self.assertIn("def clamp", p)

    def test_t1_prompt_structure_invariant_across_c1_c2(self) -> None:
        p1 = build_task_prompt("clamp", "T1", "C1", self.c1_content, {})
        p2 = build_task_prompt("clamp", "T1", "C2", self.c2_content, {})
        # Both must embed the prompt_version constant
        self.assertIn(PROMPT_VERSION, p1)
        self.assertIn(PROMPT_VERSION, p2)
        # Strip representation block — leading+trailing wording must match
        # (Simplest structural invariant: same prompt template, different fill)
        def _strip_rep_block(text: str) -> str:
            lines = text.splitlines()
            # Remove lines between the '---' markers (the representation block)
            result, inside = [], False
            for line in lines:
                if line.strip() == "---":
                    inside = not inside
                    result.append("---")
                elif not inside:
                    result.append(line)
            return "\n".join(result)

        self.assertEqual(_strip_rep_block(p1), _strip_rep_block(p2))

    def test_t2_prompt_contains_bug_word(self) -> None:
        p = build_task_prompt("clamp", "T2", "C1", self.c1_content, {})
        self.assertIn("bug", p.lower())

    def test_t2_prompt_contains_representation_content(self) -> None:
        art = resolve_representation_artifact("clamp", "C1", self.manifest, task="T2")
        p = build_task_prompt("clamp", "T2", "C1", art["content"], {})
        self.assertIn("def clamp", p)

    def test_t3_prompt_contains_transform_instruction(self) -> None:
        # Load the real transform instruction for clamp
        manifest_item = next(
            i for i in self.manifest["items"] if i["func_id"] == "clamp"
        )
        import json as _json
        gt_path = (repo_root() / manifest_item["tasks"]["T3"]["ground_truth_ref"]).resolve()
        truth = _json.loads(gt_path.read_text(encoding="utf-8"))
        instruction = truth["instruction"]

        p = build_task_prompt(
            "clamp", "T3", "C1", self.c1_content,
            {"transform_instruction": instruction},
        )
        self.assertIn(instruction, p)
        self.assertIn("def clamp", p)

    def test_prompt_version_constant_is_pilot_v1(self) -> None:
        self.assertEqual(PROMPT_VERSION, "pilot-v1")


# ---------------------------------------------------------------------------
# Scorer dispatcher tests
# ---------------------------------------------------------------------------

class RunnerScorerDispatchTests(unittest.TestCase):

    def _item(self, task: str) -> dict:
        return {"func_id": "clamp", "task": task, "condition": "C1", "model": "test-model"}

    def test_dispatch_t1_returns_scorer_result_v1(self) -> None:
        item = self._item("T1")
        result = dispatch_scorer(
            item,
            "clamp takes value, lo, hi and returns a float clamped to [lo, hi].",
            "results/raw/placeholder.json",
        )
        self.assertEqual(result.get("lumen_schema"), "scorer-result-v1")
        self.assertEqual(result.get("task"), "T1")

    def test_dispatch_t1_score_in_unit_interval(self) -> None:
        item = self._item("T1")
        result = dispatch_scorer(item, "some response", "results/raw/placeholder.json")
        self.assertGreaterEqual(result["score"], 0.0)
        self.assertLessEqual(result["score"], 1.0)

    def test_dispatch_t2_returns_scorer_result_v1(self) -> None:
        item = self._item("T2")
        result = dispatch_scorer(
            item,
            "The bug is on line 8: `value < hi` should be `value > hi`.\n"
            "The comparison operator is wrong.\n",
            "results/raw/placeholder.json",
        )
        self.assertEqual(result.get("lumen_schema"), "scorer-result-v1")
        self.assertEqual(result.get("task"), "T2")

    def test_dispatch_t2_has_subscores(self) -> None:
        item = self._item("T2")
        result = dispatch_scorer(item, "some response text", "results/raw/placeholder.json")
        self.assertIn("subscores", result)
        self.assertIn("location", result["subscores"])
        self.assertIn("diagnosis", result["subscores"])
        self.assertIn("fix", result["subscores"])

    def test_dispatch_t3_returns_scorer_result_v1(self) -> None:
        item = self._item("T3")
        result = dispatch_scorer(
            item,
            "```python\ndef clamp(value, lo, hi):\n    if lo > hi:\n        raise ValueError\n    return value\n```",
            "results/raw/placeholder.json",
        )
        self.assertEqual(result.get("lumen_schema"), "scorer-result-v1")
        self.assertEqual(result.get("task"), "T3")

    def test_dispatch_routes_by_task(self) -> None:
        for task in ("T1", "T2", "T3"):
            item = {"func_id": "clamp", "task": task, "condition": "C1", "model": "m"}
            result = dispatch_scorer(item, "some response text", "results/raw/placeholder.json")
            self.assertEqual(result["task"], task, f"Wrong task in result for {task}")


# ---------------------------------------------------------------------------
# Dry-run smoke test
# ---------------------------------------------------------------------------

class RunnerDryRunTests(unittest.TestCase):

    def test_dry_run_clamp_t1_c1(self) -> None:
        summary = run_pilot_experiment(
            models=["test-model"],
            func_ids=["clamp"],
            tasks=["T1"],
            conditions=["C1"],
            dry_run=True,
        )
        self.assertIn("run_id", summary)
        self.assertIn("items", summary)
        self.assertEqual(len(summary["items"]), 1)
        item = summary["items"][0]
        self.assertEqual(item["func_id"], "clamp")
        self.assertEqual(item["task"], "T1")
        self.assertEqual(item["condition"], "C1")
        self.assertEqual(item["status"], "planned")

    def test_dry_run_produces_index_json(self) -> None:
        import tempfile, shutil  # noqa: E401, PLC0415
        from experiment.contracts import repo_root as _root  # noqa: PLC0415

        summary = run_pilot_experiment(
            models=["test-model"],
            func_ids=["clamp"],
            tasks=["T1"],
            conditions=["C1"],
            dry_run=True,
        )
        run_id = summary["run_id"]
        index_path = _root() / "results" / "runs" / run_id / "index.json"
        self.assertTrue(index_path.exists(), f"index.json not found at {index_path}")
        loaded = json.loads(index_path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["run_id"], run_id)
        self.assertEqual(loaded["prompt_version"], PROMPT_VERSION)

    def test_dry_run_does_not_create_prompts_dir(self) -> None:
        from experiment.contracts import repo_root as _root  # noqa: PLC0415

        summary = run_pilot_experiment(
            models=["test-model"],
            func_ids=["clamp"],
            tasks=["T1"],
            conditions=["C1"],
            dry_run=True,
        )
        run_id = summary["run_id"]
        prompts_dir = _root() / "results" / "runs" / run_id / "prompts"
        self.assertFalse(
            prompts_dir.exists(),
            "dry_run should not create prompts directory",
        )

    def test_dry_run_t2_c2_is_planned(self) -> None:
        summary = run_pilot_experiment(
            models=["test-model"],
            func_ids=["clamp"],
            tasks=["T2"],
            conditions=["C2"],
            dry_run=True,
        )
        # T2/C2 is now a valid combination with buggy AST artifact
        self.assertEqual(len(summary["items"]), 1)
        item = summary["items"][0]
        self.assertEqual(item["func_id"], "clamp")
        self.assertEqual(item["task"], "T2")
        self.assertEqual(item["condition"], "C2")
        self.assertEqual(item["status"], "planned")


if __name__ == "__main__":
    unittest.main(verbosity=2)
