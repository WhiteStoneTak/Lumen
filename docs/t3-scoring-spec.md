# T3 (code-transformation) scoring specification

Linear: WOV-238 (R1-4). Canonical, reproducible specification of the T3 scorer.
Implementation: `src/experiment/score_t3.py`.

## 1. Inputs

- **Ground truth:** a T3 transform spec per function (`t3-transform-spec`,
  resolved through the dataset manifest) that links a post-transform unittest
  suite `data/ground_truth/tests/{func_id}_t3_test.py`.
- **Model response:** free text containing the transformed implementation.

## 2. Score

```
score = passed_tests / total_tests   ∈ [0, 1]
```

Failure modes do **not** silently become a mid-scale value:

| Situation | status | score | failure_reason.code |
|---|---|---|---|
| code ran, tests scored | `ok` | passed/total | — |
| no code block in response | `parse_failure` | 0.0 | `no_code_candidate` |
| candidate doesn't parse | `parse_failure` | 0.0 | `syntax_error` |
| target function absent / misnamed | `parse_failure` | 0.0 | `missing_target_function` / `wrong_function_name` |
| import/exec raised | `execution_failure` | 0.0 | `module_load_failure` |
| **non-terminating / over budget** | `execution_failure` | 0.0 | `execution_timeout` |
| suite ran 0 tests | `scoring_error` | 0.0 | `zero_total_tests` |

Parse/execution failures are flagged with distinct `status`/`failure_reason`
codes (not pooled as honest 0/total passes), so the L3-05-style
missing-not-at-random analysis (R2-2) over parse failures stays possible.

## 3. Execution sandboxing and timeout (exact)

Real collection uses `score_t3_sandboxed(...)` (the mandated path for R5).
Test execution is fenced in a **child process**:

- The candidate is written to a temp `.py`; a driver script
  (`_T3_DRIVER`) is run as `subprocess.run([sys.executable, driver, cand,
  func_id, test_path], capture_output=True, text=True, timeout=timeout_s)`.
- The driver imports the candidate and the linked test module, injects the
  candidate function onto the test module and patches `TestCase` method globals
  (identical to the in-process injection), runs the suite with a silent
  `TextTestRunner`, and prints one JSON line `{"passed":…, "total":…}` (or
  `{"error": …}`).
- **Timeout:** `T3_SANDBOX_TIMEOUT_S = 10.0` s wall clock. On
  `subprocess.TimeoutExpired` the child is killed and the runner returns
  `(0, 0, "TIMEOUT: …")`, which the scorer maps to
  `status=execution_failure`, `failure_reason.code=execution_timeout`.
  Rationale: one suite is 8–13 fast unit tests; 10 s is generous for honest
  code and short enough to fence a runaway/non-terminating candidate.
- Temp candidate and driver files are always unlinked in a `finally`.

The legacy in-process `run_t3_tests` (no timeout) is retained as the default of
`score_t3` for backward-compatible unit tests; it must not be used for live
collection of untrusted model output. `score_t3(payload, resp, runner=…)`
accepts a pluggable runner so the sandbox path is a thin wrapper.

> Note: the subprocess gives wall-clock isolation, not OS-level resource
> capping. If R5 needs hard CPU/memory caps, add `resource.setrlimit` in the
> driver (POSIX) — flagged as an optional hardening, not required for the
> measurement-design pass.

## 4. Anti-ceiling analysis (dataset-derived)

Per-function test-case counts across the **29** authored T3 suites:

```
min 8, max 13, mean 10.7, median 11
distribution {8:2, 9:4, 10:7, 11:6, 12:8, 13:2}
functions with <4 tests: none
```

- Attainable score = `k / total`, `total ∈ [8, 13]` → **9–14 distinct
  attainable values per function**, far above the T2 composite's realised 3.
- Pooling across the realised test-counts (8…13) gives **53 distinct
  attainable score values** in [0, 1].
- **No dataset gap:** every function has ≥ 8 tests, so no minimum-test-count
  enrichment is required (the issue's contingency does not trigger). If future
  functions are added with < ~5 tests, enrich them before T3 collection.

So T3, like T1, provably cannot repeat the T2 0–3 saturation on this dataset.

## 5. Tests

- `tests/test_score_t3.py` (existing): extraction, parse, correct→1.0,
  partial→fractional, syntax/wrong-name/no-candidate→parse_failure, contract.
- `tests/test_score_t3_sandbox.py` (R1-4): against the **sandboxed** runner —
  all-pass→1.0, partial→fractional, syntax-error→parse_failure,
  **infinite-loop→execution_timeout** (fenced by the wall-clock budget), and
  sandbox==in-process score agreement.

## 6. Scope

Scorer only. **No T3 model data is collected here** — collection is R5, gated
on Constitution v0.3.
