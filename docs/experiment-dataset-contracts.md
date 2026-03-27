# Dataset And Scorer Contracts (Route A Pilot)

This document defines the bounded protocol-first contracts added for the current
pilot foundation. It does not define runner orchestration or analysis scripts.

## 1. Function-Centric Dataset Manifest

Manifest path:

- `data/dataset/functions_manifest.json`

Schema ID:

- `dataset-manifest-v1`

Each `items[]` entry is one function dataset unit and includes:

- `func_id`
- `source_hash` (SHA-256 of `data/functions/raw/{func_id}.py`)
- `inclusion_status` (`included | excluded | deferred`)
- `dataset_tier` (`pilot | full`)
- `eligibility.non_recursive` and `eligibility.single_function`
- `artifacts` refs for raw source and derived representations
- `representations` availability flags for `C1`, `C1+`, `C2`, `C3`, `C4`
- `tasks` availability and task ground-truth references
- `lineage` source-hash alignment fields across artifacts

Pilot seeds currently wired:

- `clamp`
- `count_vowels`
- `is_sorted`

Current task availability in pilot manifest:

- `T1`: available (checklists present for all 3 pilot functions)
- `T2`: **active** (t2-bug-v1 annotations, buggy source files, and test suites authored for all 3 pilot functions; see §2 T2 below)
- `T3`: unavailable (manual transform specs/tests pending)

## 2. Ground-Truth Artifact Schemas

Validation code lives in `src/experiment/contracts.py`.

### T1 Checklist

- Schema: `t1-checklist-v1`
- Path pattern: `data/ground_truth/checklists/{func_id}.json`
- Contract: factual property checklist, representation-independent.

### T2 Bug Annotation

- Schema: `t2-bug-v1`
- Canonical bug label set:
  - `off_by_one`
  - `wrong_comparison_operator`
  - `missing_boundary_check`
  - `incorrect_variable_reference`
  - `swapped_arguments`
- Required fields include:
  - exactly one bug (`bug_id` + one `location` object)
  - exact location (`path`, `start_line`, `end_line`)
  - canonical category label (`bug_category`)
  - `reference_fix` span + replacement
  - `test_suite_ref` linkage

Template (manual authoring starter, not active truth):

- `data/ground_truth/bugs/TEMPLATE.t2-bug-v1.json`

Active T2 pilot artifacts (authored 2026-03-27):

| func_id | bug_id | bug_category | buggy line |
|---|---|---|---|
| `clamp` | `clamp.B01` | `wrong_comparison_operator` | line 8: `value < hi` instead of `value > hi` |
| `count_vowels` | `count_vowels.B01` | `off_by_one` | line 9: `count += 2` instead of `count += 1` |
| `is_sorted` | `is_sorted.B01` | `wrong_comparison_operator` | line 7: `>=` instead of `>` |

Buggy source files: `data/ground_truth/bugs/{func_id}_buggy.py`
Test suites: `data/ground_truth/tests/{func_id}_t2_test.py`

Intentionally deferred for T2: `score_t2.py` scorer implementation, experiment runner integration.

### T3 Transformation Spec

- Schema: `t3-transform-v1`
- Required fields include:
  - `transform_id`
  - natural-language `instruction`
  - `test_suite_ref` linkage for post-transform evaluation

Template (manual authoring starter, not active truth):

- `data/ground_truth/transforms/TEMPLATE.t3-transform-v1.json`

## 3. Scorer Contracts

Validation code: `src/experiment/contracts.py`.

### Scorer Input

- Schema: `scorer-input-v1`
- Required fields:
  - `func_id`, `task`, `condition`, `model_id`, `response_ref`
- Optional:
  - `manifest_ref` (defaults to `data/dataset/functions_manifest.json`)
- Loader helper:
  - `load_scorer_input_file(...)`
  - `validate_scorer_input(...)`

Input validation resolves manifest/task references deterministically and fails if
requested task truth is unavailable for the function.

### Scorer Output

- Schema: `scorer-result-v1`
- Standardized failure shape:
  - `failure_reason = { code, message, details? }`
- Helper:
  - `build_scorer_result(...)`
  - `validate_scorer_result(...)`

Task-specific enforced scoring constraints:

- `T1`: score in `[0.0, 1.0]`
- `T2`: composite score in `{0,1,2,3}` and equals `location + diagnosis + fix`
- `T3`: score in `[0.0, 1.0]`; `parse_failure` and `execution_failure` require
  `score = 0.0`

## 4. Validation Command

Run full manifest + artifact validation:

```bash
PYTHONPATH=src python -m experiment.validate_dataset_contracts
```

Run validation plus malformed-sample demo failures:

```bash
PYTHONPATH=src python -m experiment.validate_dataset_contracts --demo-malformed
```

## 5. Intentionally Deferred

The following are intentionally not implemented in this block:

- experiment runner orchestration
- task scorer implementations (`score_t1_checklist.py`, `score_t2.py`, `score_t3.py`)
- analysis scripts and statistical reporting
- manual authoring of T3 pilot truth content (T2 is now active)
