# R0-1 — Reproducibility check: `full_t2_confirmatory_v2`

Linear issue: WOV-231 (R0-1). Verifies that the repo reproduces the
confirmatory point estimates reported in `paper/main.tex` §4.

- Date run: 2026-06-10
- Environment: Python 3.11.5, scipy 1.17.1, numpy 1.26.4
- No frozen script, dataset, or analysis artifact was modified.

## Summary

| Check | Result |
|---|---|
| Frozen artifact reproduces paper §4 table (all 9 cells) | ✅ exact |
| Fresh re-run reproduces **H1/T2** (primary endpoint) | ✅ exact |
| Fresh re-run reproduces **H2/T2 and H3/T2** | ❌ diverges (C1-dependent) |
| Figures F1/F2/F3 regenerate from frozen analysis JSONs | ✅ drawing streams byte-identical |

The paper's numbers are faithfully backed by a committed frozen artifact
(`results/analysis/confirmatory/full_t2_confirmatory_v2/`). The **frozen → paper**
chain is sound. The **raw scores → fresh analysis** chain is *not* byte-reproducible
for the two cells that depend on condition C1, because `results/runs/` has grown
since the 2026-04-27 freeze. Details below.

## 1. Point estimates: paper vs frozen artifact vs fresh re-run

`paper/main.tex` §4 table (lines 754–759) and the frozen JSON
`results/analysis/confirmatory/full_t2_confirmatory_v2/confirmatory_results.json`
agree on every cell:

| Cell | Paper §4 | Frozen JSON | Fresh re-run (current `results/runs/`) |
|---|---|---|---|
| H1/T2 (C4>C1+) | W=83.0, p=0.023, r_rb=+0.581 | W=83.0, p=0.022765, r_rb=+0.580952 | **W=83.0, p=0.022765, r_rb=+0.580952** ✅ |
| H2/T2 (C4>C1) | W=63.0, p=0.233, r_rb=+0.200 | W=63.0, p=0.233427, r_rb=+0.200 | W=54.5, p=0.320068, r_rb=+0.197802 ❌ |
| H3/T2 (C1+>C1) | W=24.0, p=0.969, r_rb=−0.473 | W=24.0, p=0.96875, r_rb=−0.472527 | W=39.0, p=0.942916, r_rb=−0.426471 ❌ |

Fresh re-run restricted to the 30 retained confirmatory functions
(`data/dataset/confirmatory_governance.json → full_t2_plan.retained_func_ids`):

```
python -m src.experiment.analyze_confirmatory \
  --func-ids antidiagonals batch_list camel_to_snake ... welford_running_stats
```

**The primary endpoint H1/T2 reproduces exactly.** H1 is the cell the paper
foregrounds (constitution §14) and the one carrying the headline claim.

> Note: the issue text references a `--run full_t2_confirmatory_v2` flag. That flag
> does not exist; `analyze_confirmatory` takes `--func-ids` / `--results-dir`. The
> frozen run is reproduced by restricting to the 30 governance func_ids above.

## 2. Root cause of the H2/H3 divergence

`src/experiment/analyze_confirmatory._build_score_table` resolves duplicate
`(func_id, task, condition, model_id)` records by **"last record in run-directory
sort order wins"** (later runs presumed to be rescores). Scores are loaded from
*every* directory under `results/runs/`.

Since the 2026-04-27 freeze, `results/runs/` has gained directories that sort
lexicographically **after** `full_t2_confirmatory_v2` and that contain T2/**C1**
scores for the same functions — e.g. `t2_screen_wave1`, `t2_screen_wave2_second`,
`t2_cts_rescore_v1`. For several of the 30 functions these screening-wave C1 scores
differ from the confirmatory C1 scores, so they now silently supersede them.

Consequences:
- **H1 (C4 vs C1+)** never touches C1 → unaffected → reproduces exactly.
- **H2 (C4 vs C1)** and **H3 (C1+ vs C1)** both depend on C1 → drift.

This is a defect in the *re-run-from-raw* path (non-confirmatory screening runs
are allowed to outrank the registered confirmatory run), not in the frozen
artifact or the paper. The frozen artifact remains the authoritative record.

There are 62 `(func_id, model)` C1/T2 keys with more than one run-level record and
33 distinct func_ids in `results/runs/` (the 30 retained + 3 extras: `clamp`,
`count_vowels`, and one more screening function).

### Recommended follow-up (not done here — would touch frozen logic)
A faithful re-run needs the score loader scoped to the confirmatory run set rather
than "all runs, lexicographically-last wins." Tracked as analysis-integrity work
(see R2 milestone). No change was made under R0-1 to preserve the freeze.

## 3. Figure regeneration

`paper/figures/scripts/make_f1_f2_forest.py` and `make_f3_histograms.py` read
`r_rb` and bootstrap CIs verbatim from the frozen exploratory analysis JSONs
(`results/analysis/exploratory/.../exploratory_results.json`); no statistics are
recomputed. Regenerating overwrites only PDF metadata dates; the decompressed
drawing content streams are **byte-identical** to the committed PDFs:

```
F1 drawing-stream identical: True (20792 B)
F2 drawing-stream identical: True (21665 B)
F3 drawing-stream identical: True (18004 B)
```

Committed PDFs were restored after the check; the working tree is clean.

## 4. Acceptance criteria

- [x] Report listing each reported point estimate and its reproduced value.
- [x] Figure regeneration confirmed (drawing streams byte-identical).
- [x] No modification to any frozen script, dataset, or analysis artifact.

Carry-forward: the H2/H3 re-run divergence is a real analysis-integrity gap
(non-confirmatory runs superseding confirmatory C1 scores). It does not affect
the paper, which is backed by the frozen artifact, but it should be fixed before
any future confirmatory collection re-uses this loader. Related: R2-1 (WOV-240).
