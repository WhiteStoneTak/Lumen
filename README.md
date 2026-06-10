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

Extended preprint. The Tier 1 and Tier 2 findings from the critical-review
round were addressed in the Phase 2 response (commits in the
`6008a92..974dc9a` series). Tier 3 findings and broader follow-on items
are tracked in [`docs/journal-version-backlog.md`](docs/journal-version-backlog.md)
for the journal version. The current authoritative confirmatory attempt is
`full_t2_confirmatory_v2`; only the T2 task family has been collected so
far (six of nine confirmatory cells are uncollected placeholders, as
disclosed in the paper).

The confirmatory result on T2 is non-rejection; see §4 of the paper for
how this is interpreted under the pre-registered analysis plan. It should
not be read as a positive finding.

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

`scratch/` and `results/runs/` are local-only by design (see `.gitignore`).
The bootstrap CI sibling script referenced from §3.6 of the paper currently
lives in `scratch/` and is therefore not in the repo; back-porting it into
the frozen analysis script is tracked as item W-02 in the journal-version
backlog.

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

The design constitution (`docs/design-constitution.pdf`, v0.2.2) is the
single source of truth for the experimental design, success criteria, and
frozen-script regime. The v0.3 update is planned per §13 Phase 3 of the
constitution and is tracked as item W-05 in the journal-version backlog.

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
