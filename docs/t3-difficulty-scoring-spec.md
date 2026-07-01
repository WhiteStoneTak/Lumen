# T3 difficulty-adjusted / ceiling-free scoring specification (EXPLORATORY)

Backlog: **W-04**. Status: **exploratory** measurement-design instrument, reported
*alongside* the frozen `passed / total`. It never mutates or re-runs `score_t3.py`
or `analyze_confirmatory.py`, and is **not** for confirmatory inference until
Constitution v0.3 (R3). Implementation: `src/experiment/score_t3_difficulty.py`;
hidden/metamorphic layer: `data/ground_truth/t3_hidden/`.

## 0. The problem is *difficulty*, not granularity

On `full_t3_confirmatory_v1`, **239 / 255 ok records (93.7 %) score exactly 1.0** —
both frozen models pass *every* authored test. The frozen scorer already emits a
fine-grained `passed/total` (53 attainable values); the ceiling is not a
granularity defect. It is a **difficulty** ceiling: re-weighting or partial-credit
over suites everyone already passes keeps a perfect score perfect. The only way to
de-saturate is to add checks the passing solutions can **fail**.

## 1. The instrument

For each candidate, a difficulty-weighted quality score over three check tiers:

1. **base / edge** — the *existing* authored suite, scored **per test**, tiered by
   a deterministic method-name heuristic (`_EDGE_KEYWORDS`: empty, boundary,
   raise, large, negative, … → edge; else base).
2. **adversarial** — the hidden + metamorphic layer authored for a subset
   (`data/ground_truth/t3_hidden/{func}.py`): held-out inputs differential-tested
   against a reference implementation, plus oracle-free metamorphic invariants.
   This is the tier a "passes everything visible" solution can fail.

```
quality = Σ_tier w · passed / Σ_tier w · total ,   w = {base:1, edge:2, adversarial:3}
```

Weights are documented and tunable (`TIER_WEIGHTS`). The unweighted visible pass
fraction (`frozen_equiv_fraction`, reproducing the frozen T3 score) is reported
alongside. Execution is fenced in a child process with a 15 s wall-clock timeout.

### Hidden-module contract (`{func_id}.py`)
- `reference(*args)` — a correct transformed implementation (differential oracle);
  must pass the visible `{func}_t3_test.py` suite.
- `HIDDEN_INPUTS: list[list]` — held-out adversarial argument lists,
  differential-tested (equal return, or same exception type).
- `METAMORPHIC: list[callable]` — `rel(candidate) -> bool` invariants that hold for
  any correct transform (verified against `reference` in the test suite).

## 2. Subset (7 in-run + 3 extra)

Authored, type-diverse, all validated (reference passes its visible suite; every
metamorphic relation holds for the reference):

- **In `full_t3_confirmatory_v1`** (drive the de-saturation re-analysis):
  `dense_rank`, `group_and_aggregate`, `max_subarray_bounds`, `merge_intervals`,
  `rle_encode`, `rotate_list`, `strided_windows`.
- **Extra coverage / fixtures** (not in that run): `clamp`, `count_vowels`,
  `is_sorted`.

**Extending to all 26/29:** author one module per function following the contract;
no scorer change is needed (auto-discovered). Full authoring is deferred — it
brushes the Constitution's "no new data collection" gate and is an R3/v0.3
decision.

## 3. What the instrument shows (honest)

**It has teeth (controlled proof).** A `strided_windows` candidate that reverses
correctly but ignores `include_partial` passes the **entire** visible suite
(`frozen_equiv_fraction = 1.0`) yet scores `difficulty_quality ≈ 0.94`, because a
hidden input probes `include_partial=True` — behaviour the visible suite never
tests. This is a candidate the frozen scorer rates perfect (it would sit inside
the 93.7 %) that the instrument de-saturates. Encoded in
`tests/test_score_t3_difficulty.py::TestControlledDeSaturation`.

**On real data it does not over-claim.** Re-analysing the subset (69 records):

| Metric (subset) | distinct | tied-pair fraction |
|---|---|---|
| frozen score | 5 | 0.6927 |
| difficulty quality | 5 | 0.6927 |

- Of 57 frozen-**perfect** subset records, **0** were pulled below 1.0 — the models
  that pass the visible suite here are *genuinely* correct (they also pass the
  hidden + metamorphic layer). An honest true-negative: no fake de-saturation.
- Where wrongness exists, the adversarial tier shifts the score and can penalise
  *more* than the visible suite: `max_subarray_bounds` frozen 0.917 → quality
  **0.814** (hidden/metamorphic caught wrongness the visible suite under-scored).

**Interpretation for R5.** That harder hidden/metamorphic probing does **not**
reveal hidden C4-vs-C1+ differences among the passing solutions refines R5's
"T3 needs a harder dataset": on these transforms the ceiling reflects genuine
model competence, not (mainly) test blindness. Testing the C4 > C1+ prediction on
T3 needs harder **tasks**, not merely harder tests on easy tasks. The instrument is
built so that, on those harder tasks, a pass-everything-visible candidate can no
longer reach 1.0 unexamined.

## 4. Reproduce

```
PYTHONPATH=src python -m experiment.score_t3_difficulty --reanalyze full_t3_confirmatory_v1
```

Output (labelled `exploratory: true`):
`results/analysis/exploratory/t3_difficulty_full_t3_confirmatory_v1/exploratory_difficulty_quality.json`.
Tests: `tests/test_score_t3_difficulty.py`.

`git diff` shows **no** change to `score_t3.py`, `analyze_confirmatory.py`, frozen
datasets, or `results/runs/*`; only the new `data/ground_truth/t3_hidden/` layer.
