# W-04 — Ceiling-free measurement battery (reproducibility note)

Backlog **W-04**; continues R1-1 (WOV-235) / R1-2 (WOV-236). Status: **exploratory**
measurement-design instruments reported *alongside* the frozen regime. The frozen
scorers (`score_t2.py`, `score_t3.py`) and `analyze_confirmatory.py` are untouched;
these metrics are **not** for confirmatory inference until Constitution v0.3 (R3).

Full definitions: `docs/t2-continuous-scoring-spec.md`,
`docs/t3-difficulty-scoring-spec.md`.

## 1. What and why

The prediction test battery presumes a continuous, ceiling-free metric. R1 did the
minimum-sufficient location fix and parked the rest; W-04 builds the full battery:

| Instrument | Module | Frozen problem it addresses |
|---|---|---|
| T2 location: AST-node distance | `score_t2_continuous.py` (+) | binary location ≡ 0 (R1-1 parked AST) |
| T2 patch correctness (test-pass fraction) | `score_t2_patch.py` | binary fix 0/1 (R1-2 parked) |
| T2 semantic equivalence (differential + structural) | `score_t2_patch.py` | no equivalence check (R1-2 parked) |
| T3 difficulty-adjusted quality (+ hidden/metamorphic) | `score_t3_difficulty.py` | 93.7 % all-pass difficulty ceiling |
| shared type-driven input sampler | `diff_sampling.py` | — |

## 2. Empirical de-saturation (reproduce)

```
PYTHONPATH=src python -m experiment.score_t2_continuous --reanalyze full_t2_confirmatory_v2
PYTHONPATH=src python -m experiment.score_t2_patch       --reanalyze full_t2_confirmatory_v2
PYTHONPATH=src python -m experiment.score_t3_difficulty  --reanalyze full_t3_confirmatory_v1
```

**T2 location (300 records):** binary 1 distinct / tie 1.0000 → line-IoU **37 /
0.1422** (R1-1, primary), AST distance 7 / 0.8532 (orthogonal diagnostic; coarser
on this shallow-AST dataset).

**T2 fix (300 records):** binary 2 distinct / tie 0.7395 → patch-pass-fraction
**12 / 0.7792** (recovers partial patches; near-binary tie mass is inherent to
single-bug T2, per R1-2 §3). Behavioral equivalence 5 / 0.8323 over n = 248, with
30 callable-parameter records `not_applicable` (never faked as 0).

**T3 (subset, 69 records):** frozen 5 distinct / tie 0.6927; difficulty quality
5 / 0.6927. **Controlled proof of teeth:** a `strided_windows` candidate that
ignores `include_partial` passes the whole visible suite (frozen = 1.0) but scores
quality ≈ 0.94 — a "perfect" frozen score the instrument de-saturates via a hidden
input. On the *actual* responses, 0/57 frozen-perfect subset records were pulled
below 1.0 (honest true-negative: those solutions are genuinely correct);
`max_subarray_bounds` frozen 0.917 → quality 0.814 where wrongness existed.

## 3. Anti-saturation is *checked*, not asserted

Every re-analysis reports realised distinct-value counts and tied-pair fractions
(above). Non-applicable cases (unparseable source, callable-parameter signatures)
are flagged as an explicit status, never scored 0, so they cannot manufacture fake
saturation or fake signal.

## 4. Guarantees

- `git diff` shows no change to `score_t2.py`, `score_t3.py`, `score_t1*.py`,
  `analyze_confirmatory.py`, frozen datasets, or `results/runs/*`.
- New surface only: `src/experiment/{diff_sampling,score_t2_patch,score_t3_difficulty}.py`,
  an AST-distance addition to `score_t2_continuous.py`, the
  `data/ground_truth/t3_hidden/` layer, three exploratory JSON outputs under
  `results/analysis/exploratory/`, tests, and these docs.
- Tests: `tests/test_diff_sampling.py`, `tests/test_score_t2_patch.py`,
  `tests/test_score_t3_difficulty.py`, and AST cases in
  `tests/test_score_t2_continuous.py`. (Six pre-existing failures in
  `test_runner.py` / `test_candidate_tracker.py` / `test_manage_candidates.py` are
  unrelated dataset-count drift and fail on clean HEAD.)

## 5. Carry-forward

Candidates for Constitution v0.3 (R3): a continuous location metric (IoU primary),
a continuous fix/patch metric, and a difficulty-adjusted T3 quality with a hidden +
metamorphic tier. The T3 real-data true-negative refines R5's "T3 needs a harder
dataset": harder **tasks**, not merely harder tests on easy tasks. Full 29-function
metamorphic authoring remains deferred (brushes the no-new-collection gate).
