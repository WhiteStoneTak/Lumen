# T3 hidden / metamorphic layer (EXPLORATORY — W-04)

**Status:** exploratory measurement-design instrument. **Not** frozen ground
truth and **not** part of the confirmatory regime. Consumed only by
`src/experiment/score_t3_difficulty.py`.

## Why this exists

The frozen T3 scorer (`score_t3.py`) scores `passed / total` over the authored
suite in `data/ground_truth/tests/{func}_t3_test.py`. On `full_t3_confirmatory_v1`
**93.7 % of records score exactly 1.0** — both frozen models pass *every* test.
This is a **difficulty** ceiling: re-weighting or partial-credit over suites that
everyone already passes keeps a perfect score perfect. Only checks the passing
solutions can *fail* can de-saturate the measurement. This directory supplies
those checks for a representative subset.

## Per-function module contract (`{func_id}.py`)

Each module is imported in a sandboxed subprocess and must define:

- `reference(*args)` — a **correct** implementation of the transformed function
  (the differential oracle). It must pass the existing `{func}_t3_test.py` suite.
- `HIDDEN_INPUTS: list[list]` — held-out adversarial / edge argument lists.
  Each is differential-tested: `candidate(*args)` must match `reference(*args)`
  (equal return, or the same exception type). These are *hidden* — they are not
  shown to the model and are harder than the visible suite.
- `METAMORPHIC: list[callable]` — oracle-free invariant checks `rel(candidate) ->
  bool`. Each relation must hold for *any* correct transform (verified against
  `reference` in `tests/test_score_t3_difficulty.py`). A relation returning
  `False` (or raising) means the candidate violated an invariant the visible
  suite did not probe.

## Subset (7 functions, type-diverse)

`clamp`, `count_vowels`, `is_sorted`, `rotate_list`, `merge_intervals`,
`rle_encode`, `dense_rank`.

## Extending to all 29

Author one module per remaining function following the contract above; no scorer
change is needed — `score_t3_difficulty.py` auto-discovers `{func_id}.py` here.
Full 29-function authoring is deferred (it brushes the Constitution's
"no new data collection" gate and is an R3/v0.3 decision).
