# Lumen

Lumen is a Route A empirical study investigating whether structured code
representations affect the accuracy of large language models on code reasoning
tasks (program understanding, bug detection, and code transformation).

## Scope

Current scope is **non-recursive, single-function Python only**.

## Conditions

Five progressively richer code representations are compared as LLM inputs:

| ID  | Description |
|-----|-------------|
| C1  | Raw source text |
| C1+ | Raw source text + behavioral contracts (derived from C4 to preserve information parity) |
| C2  | Source text + type annotations |
| C3  | Intermediate representation (IR) |
| C4  | IR + behavioral contracts |

## Current status

Scaffolding for **Phase 1** of the 90-day Route A empirical study.
See `docs/experimental-protocol.md` for the study protocol.

> **Note:** The design constitution PDF (`docs/design-constitution.pdf`) has been
> included in this repository. If it is missing, add it manually from the
> canonical source.

## Repository layout

```
lumen/
  docs/                        study documentation
    design-constitution.tex    canonical design constitution (LaTeX)
    design-constitution.pdf    canonical design constitution (PDF)
    experimental-protocol.md   study protocol placeholder
  src/
    pipeline/                  data transformation pipeline stubs
    experiment/                experiment runner and scoring stubs
    utils/                     shared utilities
  data/
    functions/                 raw and transformed function corpus
    contracts/                 generated, reviewed, and diffed contracts
    ground_truth/              checklists, known bugs, tests
  results/                     raw outputs and analysis artefacts
  paper/                       manuscript source
```
