# T2 continuous / ceiling-free scoring specification (EXPLORATORY)

Backlog: **W-04** (location sub-score ceiling), continuing **R1-1** (WOV-235) and
**R1-2** (WOV-236). Status: **exploratory** measurement-design instruments,
reported *alongside* the frozen 0–3 composite. They never mutate or re-run
`score_t2.py` or `analyze_confirmatory.py`, and are **not** for confirmatory
inference until Constitution v0.3 (R3) adopts them.

Implementations:
- `src/experiment/score_t2_continuous.py` — location (line-IoU + AST distance).
- `src/experiment/score_t2_patch.py` — patch correctness + semantic equivalence.
- `src/experiment/diff_sampling.py` — deterministic input sampler (shared).

## 0. Why (recap)

The frozen integer T2 composite (0–3) saturated at 2; the binary *location*
sub-score was 0 for all 300 confirmatory records (zero variance), collapsing the
effective Wilcoxon *n* (§5.3). R1-1 fixed location with a continuous line-IoU
metric; R1-2 kept diagnosis/fix **binary**, explicitly parking a test-pass
fraction and a semantic-equivalence metric as *conditional follow-ups* pending
(a) the R1-4 sandbox and (b) evidence they were needed. W-04 reopens those parked
items for the prediction test battery, which presumes a continuous metric.

## 1. Location — line-IoU (R1-1) + AST distance (W-04)

Two orthogonal continuous signals in `[0, 1]`, both anchored to the buggy-source
coordinate system (`truth["location"]["path"]`), reported side by side:

- **`location_iou`** (unchanged from R1-1): predicted line set `P` vs truth set
  `T` → `IoU(P,T)` on overlap, else a length-normalised proximity ramp capped at
  `PROX_WEIGHT = 0.5`, else 0.0.
- **`location_ast`** (W-04, `ast_location_distance_score`): map the truth and
  predicted lines to their smallest enclosing AST nodes and score by normalised
  tree distance through the lowest common ancestor (exact node → 1.0). Returns
  `None` → `not_applicable` when the source does not parse (never a silent 0).

**Empirical de-saturation** (`--reanalyze full_t2_confirmatory_v2`, 300 records):

| Location signal | distinct values | tied-pair fraction |
|---|---|---|
| binary (frozen) | 1 | 1.0000 |
| line-IoU (R1-1) | 37 | 0.1422 |
| AST distance (W-04) | 7 | 0.8532 |

**Honest reading.** Line-IoU remains the primary de-saturator. AST distance is an
*orthogonal diagnostic*: on this dataset the functions have shallow ASTs (few
distinct tree distances), so it is coarser than IoU here; its advantage is for
span-level / deeply-nested bugs where two predictions at equal line distance sit
in structurally different places. It is reported, not substituted.

## 2. Patch correctness — continuous test-pass fraction (W-04)

`patch_pass_fraction` applies the model's extracted fix (`score_t2._extract_best_
fix_line` + `_apply_fix_to_source`, reused read-only) to the buggy source and runs
the linked T2 suite in a **sandboxed subprocess** (`score_t3.run_t3_tests_
sandboxed`) → `passed / total ∈ [0,1]`, versus the frozen all-or-nothing 0/1.
Distinct non-scoring statuses (`no_candidate`, `exec_error`, `timeout`,
`zero_tests`) are preserved, never pooled as an honest 0.

**Empirical** (300 records):

| Fix signal | distinct values | tied-pair fraction | n |
|---|---|---|---|
| binary fix (frozen) | 2 | 0.7395 | 300 |
| patch pass fraction (W-04) | 12 | 0.7792 | 288 |

**Honest reading.** The continuous metric lifts distinct fix values 2 → 12 and
recovers *partial* patches the binary scorer flattens (e.g. a `camel_to_snake`
patch scoring frozen fix = 0 but pass-fraction 0.44). Tie mass stays high because
T2 seeds a **single** defect, so most patches are genuinely all-or-nothing — R1-2
§3 predicted exactly this. Patch correctness adds resolution but is not, for T2,
as powerful a de-saturator as location; its main role is cross-checking and
feeding the prediction battery.

## 3. Semantic equivalence — differential + structural (W-04)

Both computed against the canonical reference (`data/functions/raw/{func}.py`):

- **`behavioral_agreement`** (primary): the patched function and the reference are
  run over a deterministic, type-driven input battery (`diff_sampling`, seeded);
  score = output-agreement rate (same return under `math.isclose`, or the same
  raised exception type). Signatures with an unsupported parameter (e.g. a
  callable) → `not_applicable`.
- **`structural_equivalence`** (secondary diagnostic): normalized-AST equality
  (docstrings stripped) + a node-sequence similarity ratio. Near-binary; a
  diagnostic, not the primary signal.

**Empirical** (300 records): `behavioral_agreement` 5 distinct values, tie 0.8323,
n = 248, with **30 records `not_applicable`** (callable-parameter functions)
correctly excluded rather than scored 0. Like patch correctness, it is near-binary
for single-bug T2 by design; it becomes the primary de-saturator for the
multi-behaviour T3 transforms (see `docs/t3-difficulty-scoring-spec.md`).

## 4. Reproduce

```
PYTHONPATH=src python -m experiment.score_t2_continuous --reanalyze full_t2_confirmatory_v2
PYTHONPATH=src python -m experiment.score_t2_patch       --reanalyze full_t2_confirmatory_v2
```

Outputs (all fields labelled `exploratory: true`):
`results/analysis/exploratory/t2_continuous_location_full_t2_confirmatory_v2/…`
`results/analysis/exploratory/t2_patch_semantic_full_t2_confirmatory_v2/…`

Tests: `tests/test_score_t2_continuous.py`, `tests/test_score_t2_patch.py`,
`tests/test_diff_sampling.py`.

## 5. Guarantees

`git diff` shows **no** change to `score_t2.py`, `score_t3.py`,
`analyze_confirmatory.py`, frozen datasets, or `results/runs/*`. These metrics are
candidates for Constitution v0.3 (R3); they are not pooled into or substituted for
the frozen confirmatory composite.
