# Lumen

Lumen is an empirical methodology study on whether code representation
affects the accuracy of frontier large language models on code reasoning
tasks. The core methodological contribution is an information-parity
control (C1+) that lets representation effects be tested without the usual
confound of differing information content across conditions.

**Paper (extended preprint):** [`paper/main.pdf`](paper/main.pdf) —
*Information-Parity Testing for Code Representation Effects on Frontier
LLMs: Methodology and Diagnostic Findings from a Bug-Detection Study*
(Takumi Shiraishi, May 2026).

## Status

The frozen extended preprint is tagged [`preprint-v1`](https://github.com/WhiteStoneTak/Lumen/releases/tag/preprint-v1)
(commit `aafb84c`, `paper/main.pdf`). Journal-version edits continue on `main`;
`preprint-v1` is the immutable reference for what the preprint claimed.

Extended preprint. The Tier 1 and Tier 2 findings from the critical-review
round were addressed in the Phase 2 response (commits in the
`6008a92..974dc9a` series). Tier 3 findings and broader follow-on items
are tracked in [`docs/journal-version-backlog.md`](docs/journal-version-backlog.md)
for the journal version. The full nine-cell confirmatory family is now
collected: T2 first (`full_t2_confirmatory_v2`), then T1 under
`docs/preregistrations/t1-v1.md` (R5-2, `full_t1_confirmatory_v1`) and T3
under `docs/preregistrations/t3-v1.md` (R5-4, `full_t3_confirmatory_v1`).

The confirmatory result is **non-rejection on all nine cells** (Holm
m = 9). The central H1 test (C4 > C1+) is not rejected on any task: T1
r = +0.10, raw p = 0.36 (a clean null, no rubric ceiling); T2 r = +0.58,
raw p = 0.023 (absorbed by the correction); T3 r = +0.43 but
ceiling-censored (93.7% of T3 scores at 1.0, effective n ≈ 5). The cleanest
unconfounded datum, T1, shows no structure advantage at constant
information. See §4 of the paper and `docs/next-phase-design.md` §4 for the
decision-gate evaluation. None of it should be read as a positive finding.

T1 collection note: an initial pass lost 27/300 cells to Anthropic credit
exhaustion mid-run (claude-opus-4-6 only); the run was resumed after a
top-up and all 27 recovered, so the final T1 dataset is complete (300/300).

Current empirical scope is non-recursive, single-function Python.

## Conditions

Five progressively richer code representations are compared as LLM inputs.
C1+ is derived from C4 to preserve information parity with C1, modulo the
residual asymmetries openly disclosed in §3.3 of the paper.

| ID  | Description                                                                 |
|-----|-----------------------------------------------------------------------------|
| C1  | Raw source text                                                             |
| C1+ | Raw source text + behavioral contracts (information-parity control vs C4)   |
| C2  | Source text + type annotations                                              |
| C3  | Intermediate representation (IR)                                            |
| C4  | IR + behavioral contracts                                                   |

## Repository layout

```
Lumen/
  paper/                         manuscript source and compiled PDF
    main.tex                     paper source
    main.pdf                     compiled extended preprint
    lumen.bib                    bibliography
    appendices/                  appendices A-E
    figures/                     F1-F3 PDFs and generation scripts
  docs/
    design-constitution.tex      canonical design constitution (LaTeX, v0.2.2)
    design-constitution.pdf      compiled constitution
    experimental-protocol.md     study protocol
    experiment-dataset-contracts.md
    candidate-workflow.md
    journal-version-backlog.md   tracked Tier-3 and follow-on items
  src/
    pipeline/                    data transformation pipeline
    experiment/                  runner and scoring (frozen for confirmatory)
    utils/                       shared utilities
  data/
    functions/                   raw and transformed function corpus
    contracts/                   generated, reviewed, diffed contracts
    ground_truth/                checklists, known bugs, tests
  results/
    analysis/confirmatory/       frozen confirmatory analysis artifacts
    analysis/exploratory/        exploratory and replication artifacts
    figures/                     analysis-derived figures
    raw/                         raw run outputs (per-run subdirs gitignored)
  automation/                    experiment automation scaffolding
  scripts/                       ad-hoc helpers
  tests/                         unit tests
```

`results/runs/` is local-only by design (see `.gitignore`). The bootstrap CI
that produces the paper's confidence intervals has been **back-ported into the
frozen analysis script** (`src/experiment/analyze_confirmatory.py --with-ci`;
seed 20260427, 10,000 resamples, percentile) under amendment R2-1, so no
analysis quantity depends on uncommitted files. The original sibling script is
preserved for provenance at `scratch/bootstrap_ci_confirmatory.py`. See
`docs/protocol-amendment-R2-1-bootstrap-ci.md`.

## Reproducibility

The confirmatory pipeline is frozen. Re-running the analysis against the
collected T2 artifact should reproduce the point estimates reported in the
paper:

```bash
pip install -e .
python -m src.experiment.analyze_confirmatory --run full_t2_confirmatory_v2
```

Frozen artifacts and their git provenance are documented in §3.8 of the
paper and in Appendix E.

## Design constitution

The design constitution (`docs/design-constitution.pdf`, **v0.3**) is the
single source of truth for the experimental design, success criteria, and
frozen-script regime. v0.3 (the "Version 0.3 Changelog" section) absorbs the
R1 measurement-design and R2 analysis-integrity outcomes and is the gate from
which the R5 T1/T3 confirmatory pre-registrations derive.

## Citation

Until an arXiv identifier is assigned, please cite as:

```
Shiraishi, T. (2026). Information-Parity Testing for Code Representation
Effects on Frontier LLMs: Methodology and Diagnostic Findings from a
Bug-Detection Study. Extended preprint.
https://github.com/WhiteStoneTak/Lumen
```

## License

MIT. See [`LICENSE`](LICENSE).

## Contact

Takumi Shiraishi — <takumi@wovol.com>
