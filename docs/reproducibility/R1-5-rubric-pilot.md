# R1-5 — New-rubric pilot validation (held-out, no live calls)

Linear: WOV-239 (R1-5). Sanity-checks the R1 scorers (R1-1 continuous T2
location, R1-3 T1, R1-4 T3) before they are frozen into Constitution v0.3.

## Segregation

Pilot set = the three **anchor** functions `clamp`, `count_vowels`, `is_sorted`.
These are **not** among the 30 retained confirmatory functions, so they are a
legitimate held-out pilot (same rule as the paper's Phase-2 pilot, §3.0). Pilot
data must never be pooled with confirmatory data. The pilot artifact lives at
`results/runs/pilot_r1_rubric_validation_20260611/` (run id contains "pilot").

**No new model calls were made.** The anchors already have T1/T2/T3 responses
across C1/C1+/C2/C3/C4 from earlier pilot/preflight runs; the harness
(`scripts/pilot_r1_rubric_validation.py`) re-scores those existing responses
with the new scorers. (A fresh live pilot run is unnecessary for a scorer
sanity-check and would spend API budget; the existing held-out responses
exercise the scorers end-to-end identically.)

The full pilot artifact (with per-cell records) is at
`results/runs/pilot_r1_rubric_validation_20260611/` (gitignored, like all run
dirs); the summary is mirrored to the tracked
`results/analysis/exploratory/pilot_r1_rubric_validation/summary.json`.

## Results (105 anchor cells; 35 per task, 3 models)

| Scorer | n scored | distinct values | min | max | all-zero? | tie-pair frac | status |
|---|---|---|---|---|---|---|---|
| T1 checklist (R1-3) | 35 | **9** | 0.444 | 1.0 | no | 0.188 | 35 ok |
| T2 location continuous (R1-1) | 35 | **5** | 0.111 | 1.0 | no | 0.279 | 35 ok |
| T3 test-pass sandboxed (R1-4) | 35 | **1** | 1.0 | 1.0 | no | 1.000 | 35 ok |

## Per-scorer verdict

- **T1 checklist — READY.** Non-degenerate: 9 distinct values spanning
  0.44–1.0, low tie mass. Runs end-to-end with no manual intervention.
- **T2 continuous location — READY.** Non-degenerate: 5 distinct values
  spanning 0.11–1.0. Confirms the R1-1 de-saturation holds on held-out data
  (the frozen binary location was identically 0; the continuous metric
  separates the same responses).
- **T3 test-pass — scorer READY; pilot set too easy.** Every anchor cell scored
  1.0 (all tests pass), so the pilot distribution is degenerate **at the top of
  the scale**. This is a property of the anchor functions, not the scorer: the
  anchors are trivial single-operator transforms that frontier models always
  get right. The scorer's resolution is proven by its unit tests
  (`tests/test_score_t3_sandbox.py`): partial transform → fractional,
  syntax-error → parse_failure, infinite loop → execution_timeout. **Action
  (pilot-design, not scorer-change):** the held-out pilot used for the *real*
  R5 dry-run must include functions of representative difficulty (not just the
  easy anchors) to exercise T3's fractional range before confirmatory
  collection. Recorded as a constraint for R5 pilot selection; no change to the
  R1-4 scorer is warranted.

## Parse-failure handling

The natural pilot responses were all well-formed (35/35 `ok` per task), so no
parse/execution failure was triggered organically. Correct triggering is
covered by the scorer unit tests: T3 syntax-error → `parse_failure`, T3
infinite-loop → `execution_timeout`, T1 empty/whitespace → `invalid_response`.
Criterion (c) is satisfied via those tests; the pilot data simply contained no
malformed outputs to surface it.

## Feedback into R1-1/R1-3/R1-4

None required. T1 and T2-location de-saturate as designed; T3 is mechanically
correct and its pilot saturation is attributable to anchor easiness, addressed
by the R5 pilot-selection constraint above rather than a scorer change.

## Acceptance

- [x] Pilot executed; distributions tabulated.
- [x] Explicit per-scorer verdict (T1 ready, T2 ready, T3 ready + pilot-set
      caveat for R5).
- [x] Pilot data segregated (held-out anchors, "pilot" run id, not pooled).
