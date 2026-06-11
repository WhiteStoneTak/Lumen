# Protocol amendment R2-1 — bootstrap CI back-port

- **Date:** 2026-06-11
- **Linear:** WOV-240 (R2-1); backlog W-02 / L3-02.
- **Touches frozen script:** `src/experiment/analyze_confirmatory.py`
  (freeze date 2026-04-02). A dated amendment note is recorded at the top of
  that file, as its own freeze policy requires.
- **Constitution:** §17.4 (mandates both the bootstrap CIs and the
  frozen-script regime). This amendment is to be folded into Constitution v0.3
  (R3 / WOV-242), which ratifies it.

## What changed

The paper's 95% bootstrap confidence intervals on the rank-biserial effect
size (e.g. H1/T2 `[+0.077, +0.917]`) were computed by a sibling script,
`scratch/bootstrap_ci_confirmatory.py`, which was **not committed** (`scratch/`
is gitignored). Under §17.4 that is an undeclared deviation: a reported
analysis quantity depended on an uncommitted file.

Two changes:

1. **Provenance:** `scratch/bootstrap_ci_confirmatory.py` and its output
   `scratch/bootstrap_ci_results.json` are now force-committed (via
   `git add -f`, without un-ignoring the rest of `scratch/`) exactly as they
   produced the paper's CIs.

2. **Back-port:** the percentile-bootstrap kernel is re-implemented inside
   `analyze_confirmatory.py` behind a new **off-by-default** `--with-ci` flag:
   - `_bootstrap_ci_rank_biserial(diffs, n_resamples=10000, seed=20260427,
     ci_level=0.95)` — resamples the full paired-difference vector (zeros
     included) with replacement, recomputes `r_rb` per resample (reusing the
     file's existing `_rank_biserial`), and takes the percentile interval. A
     **fresh** `np.random.default_rng(20260427)` is created per call, matching
     the sibling script (which reseeds for each hypothesis).
   - The pre-registered decisions (Wilcoxon `W`, raw `p`, Holm-Bonferroni) are
     untouched. With `--with-ci` absent, the JSON/CSV are **byte-for-byte
     identical** to the frozen artifact (verified by
     `tests/test_analyze_confirmatory_ci.py::test_default_output_has_no_ci_keys`).

## Reproduction status

Run scoped to the 30 confirmatory func_ids with `--with-ci`:

| Cell | Paper CI | Back-port (`analyze_confirmatory --with-ci`) | scratch script |
|---|---|---|---|
| H1/T2 | [+0.077, +0.917] | **[+0.076923, +0.916667]** ✅ exact | [+0.076923, +0.916667] |
| H2/T2 | [−0.333, +0.700] | [−0.391, +0.758] | [−0.333, +0.700] |
| H3/T2 | [−0.885, +0.077] | [−0.821, +0.095] | [−0.885, +0.077] |

**H1/T2 (the primary endpoint and the headline CI) reproduces exactly.**

H2/T2 and H3/T2 differ between the back-port and the scratch script. This is
**not** a CI-kernel discrepancy — it is the same root cause documented in R0-1
(WOV-231): the scratch script reads scores from only the
`full_t2_confirmatory_v2` run directory, whereas `analyze_confirmatory` builds
its score table from **all** of `results/runs/` with a "last run-dir in sort
order wins" rule, so non-confirmatory screening runs added since the freeze now
supersede the confirmatory **C1** scores. H1 does not use C1 → exact; H2 and H3
use C1 → drift, and their CIs drift with the underlying diffs.

The CI kernel itself is faithful: given identical diffs (as for H1) it returns
the identical interval. Producing the paper's H2/H3 CIs from
`analyze_confirmatory` requires the R0-1 score-loader fix (scope to the
confirmatory run set), tracked separately. Until then, the authoritative
H2/H3 CIs remain those in the frozen artifact and the preserved scratch output.

## Acceptance

- [x] CI computation lives in committed, tested code; the scratch script is
      committed for provenance. No analysis quantity depends on an uncommitted
      file.
- [x] H1 CI reproduced exactly; H2/H3 discrepancy documented (R0-1 cause).
- [x] This amendment note committed; in-file dated note added.
- [x] README W-02 caveat updated.
