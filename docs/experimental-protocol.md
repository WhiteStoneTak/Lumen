# Experimental Protocol — Lumen Route A Study

> **Status:** Placeholder. Fill in details before Phase 1 begins.

---

## Scope

- Unit of analysis: single Python function (non-recursive, standalone).
- Three task types: T1 (program understanding), T2 (bug detection), T3 (code transformation).
- LLM inputs are drawn from five conditions; all other prompt elements are held constant.

## Conditions

| ID  | Description |
|-----|-------------|
| C1  | Raw source text |
| C1+ | Raw source text + contracts (contracts derived from C4 to preserve information parity) |
| C2  | Source text + type annotations |
| C3  | Intermediate representation |
| C4  | IR + behavioral contracts |

## Dataset Constraints

- TODO: minimum number of functions, selection criteria.
- TODO: sources (e.g., curated open-source, synthetic).
- TODO: exclusion criteria (recursive, multi-function, stdlib-heavy, etc.).

## Contract Review Provenance

- Contracts are generated automatically then reviewed by a human annotator.
- TODO: review rubric, reviewer qualification criteria, inter-rater reliability plan.
- Diffs between raw and reviewed contracts are stored in `data/contracts/diffs/`.

## Scoring Overview

- **T1 checklist (score_t1_checklist.py):** binary item-level checklist scoring.
- **T1 holistic (score_t1_holistic.py):** LLM-as-judge holistic quality rating.
- **T2 (score_t2.py):** bug detection accuracy (precision / recall / F1).
- **T3 (score_t3.py):** transformation correctness against test suite.

## Analysis Freeze / Amendments

- Confirmatory analyses are pre-registered and locked before data collection.
- Any post-hoc exploratory analyses must be clearly labeled in `analyze_exploratory.py`.
- TODO: pre-registration link or internal freeze date.
