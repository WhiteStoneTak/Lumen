# Lumen Dataset Expansion: Candidate Workflow

This document explains how new candidate functions move from initial collection
through Stage 1 review, prerequisites, and Stage 2 difficulty screening.

## Purpose

The current dataset (3 pilot functions: `clamp`, `count_vowels`, `is_sorted`)
is too easy for frontier models: all T2 and T3 items score perfectly under all
five conditions, making H1 (T2 C4 vs C1+) undetectable.

The next step is expanding to **20–50 harder functions**.  This requires a
disciplined screening process to confirm difficulty *before* investing in full
truth authoring.

---

## candidate_id vs func_id

**`candidate_id`** is a working name used while a function is under evaluation.
It lives only in `data/dataset/candidates.json`.

**`func_id`** is the permanent identifier used in `data/dataset/functions_manifest.json`
and across all pipeline artifacts.

These start out equal in practice — use a snake_case name that will become the
`func_id` if the candidate passes.  But until a candidate is formally admitted
to the dataset manifest, it is a candidate, not a function.

> Do NOT add a `func_id` entry to the manifest for a candidate that has not
> yet passed Stage 2 screening.

---

## Workflow States

Each candidate has a **workflow state** derived from its tracker fields:

| State | Meaning |
|---|---|
| `pending` | Added to tracker; Stage 1 not yet reviewed |
| `deferred` | Stage 1 set to DEFER with a stated reason |
| `excluded` | Stage 1 EXCLUDE; row preserved for audit |
| `pass-blocked` | Stage 1 PASS, but Stage 2 prerequisites not yet met |
| `pass-ready` | Stage 1 PASS AND in manifest with T2 available |
| `stage2-screened` | Stage 2 T2 C1 screen result recorded |
| `anchor` | One of the 3 pilot calibration anchors |

Inspect these with:
```bash
./scripts/screen.sh list
./scripts/screen.sh list --state pass-blocked
./scripts/screen.sh list --state pass-ready
```

---

## Stage 1 PASS ≠ Stage 2-Ready

This distinction matters.  **Stage 1 PASS** means the researcher has judged
the candidate worth advancing.  It does **not** mean the function can be
immediately used in a screening run.

A candidate is **stage2-ready** only when ALL of the following prerequisites
exist in the repo:

1. `data/functions/raw/{candidate_id}.py` — correct source
2. `data/dataset/functions_manifest.json` entry with `T2.available = true`
3. `data/ground_truth/bugs/{candidate_id}.json` — draft T2 bug annotation
4. `data/ground_truth/tests/{candidate_id}_t2_test.py` — minimal T2 test suite (5–7 tests)

Until those four exist, the candidate is `pass-blocked`.

The summary command shows which candidates are blocked and why:
```bash
./scripts/screen.sh summarize
# or
PYTHONPATH=src python -m experiment.summarize_candidates
```

---

## Step-by-step Workflow

### Stage 0: Collect candidates (manual)

Identify 30–50 candidate functions from sources (curated Python, coding
exercises, authored functions).  Quickly check each against the inclusion
criteria before adding to the tracker.

Inclusion quick-check:
- Body 8–35 executable lines
- At least one meaningful branch or loop
- Non-recursive, single `def`, no I/O or external imports
- A plausible non-trivial T2 bug family (not single comparison-operator flip)
- Clear T3 transform family (not single constant substitution)

### Stage 1: Review and classify (manual)

Add the candidate to the tracker:
```bash
./scripts/screen.sh add \
  --id my_func \
  --source "authored" \
  --lines 14 \
  --complexity medium \
  --t2-family "boundary_interaction" \
  --t3-family "invariant_preserving_refactor"
```

Review the function against the inclusion/exclusion criteria and record your
decision:
```bash
# Accept:
./scripts/screen.sh update-stage1 my_func --result PASS

# Reject (reason required):
./scripts/screen.sh update-stage1 my_func \
  --result EXCLUDE \
  --reason "Single operator flip on isolated line; pilot-family bug"

# Hold for later review:
./scripts/screen.sh update-stage1 my_func \
  --result DEFER \
  --reason "Revisit: body line count needs recount after refactor"
```

**Excluded rows are never deleted.**  They remain in the tracker as an audit
trail so the same function is not accidentally re-added.

### Between Stage 1 and Stage 2: Prerequisites (manual)

For each Stage 1 PASS candidate, you must complete the following before it can
enter a Stage 2 screening run:

1. **Raw source** — write the correct implementation at
   `data/functions/raw/{candidate_id}.py`

2. **Manifest entry** — add the candidate to
   `data/dataset/functions_manifest.json` following the existing schema.
   Set `tasks.T2.available = true`.

3. **T2 bug** — write a draft bug annotation at
   `data/ground_truth/bugs/{candidate_id}.json` using the `t2-bug-v1` schema.
   Prefer harder bug families (boundary interaction, state mutation ordering,
   loop termination, conditional coverage gap) over simple operator flips.

4. **T2 test suite** — write `data/ground_truth/tests/{candidate_id}_t2_test.py`.
   Minimum: 5–7 tests covering both correct-behavior and bug-detection cases.
   At least one test must fail on the buggy source and pass on the correct
   source.

Once all four exist, the candidate will appear as `pass-ready` in the tracker
summary and will be auto-detected for the next Stage 2 wave.

### Stage 2: T2 C1 Difficulty Screen (automated)

Run:
```bash
./scripts/screen.sh t2-screen-wave1
# or
make t2-screen-wave1
```

This uses `--list stage2-eligible` to auto-detect candidates that are Stage 1
PASS with no prior Stage 2 result.  **Note:** stage2-eligible (tracker) is
broader than stage2-ready (manifest+T2).  If a candidate is eligible but not
ready, the runner will error on it.  Confirm candidates are pass-ready first.

After the run completes, ingest the results:
```bash
./scripts/screen.sh ingest-stage2
```

Stage 2 decision rules:
- T2 C1 score = 3.0 → **EXCLUDE** (too easy for frontier model on raw source)
- T2 C1 score 2.0–2.9 → **INCLUDE**
- T2 C1 score 1.0–1.9 → **INCLUDE** (high priority — harder)
- T2 C1 score < 1.0 (= 0) → **DEFER** (may be malformed; re-examine bug)

### Stage 3: T3 C2 Advisory Screen (optional, automated)

For Stage 2 INCLUDE candidates, optionally run a T3 C2 advisory check:
```bash
./scripts/screen.sh t3-screen-wave1
./scripts/screen.sh ingest-stage3
```

Stage 3 decision rules (advisory only; does not affect `final_decision`):
- T3 C2 score = 1.0 → `ceiling_risk` (T3 is easy even from AST-only)
- T3 C2 score < 1.0 → `preferred` (T3 has representation-dependent difficulty)

### Truth authoring (after Stage 2 screening)

Only after a candidate passes Stage 2 (INCLUDE):
- Add remaining representations: `data/functions/ast/`, `typed_ast/`, `ir/`, `annotated_text/`
- Add buggy variants of all representations
- Author T1 checklist (`data/ground_truth/checklists/`)
- Author T3 transform spec (`data/ground_truth/transforms/`)
- Generate contracts (see pipeline)

**Do not begin full truth authoring for all Stage 1 PASS candidates.**
Stage 2 screening exists to protect this investment.

---

## Calibration Anchors

The three pilot functions (`clamp`, `count_vowels`, `is_sorted`) are
calibration anchors.  They:
- remain in the dataset permanently
- always have `final_decision = INCLUDE` regardless of Stage 2 score
- serve as known-easy references for scorer sanity checks

Their Stage 2 scores (all 3.0) and Stage 3 scores (all 1.0) define the
"too easy" baseline.  If a new candidate scores at or near this level on C1,
it is likely too easy for the primary comparison.

---

## Target Dataset Sizes

| Phase | Target | Notes |
|---|---|---|
| Exploratory pilot | 13–18 functions | 3 anchors + 10–15 new |
| Phase 2 serious run | 23–33 functions | 3 anchors + 20–30 new |
| Confirmatory | 50 functions | Protocol target |

**Do not run the confirmatory analysis on fewer than 30 functions.**

---

## What is Automated vs Manual

| Step | Who does it |
|---|---|
| Stage 0: Candidate collection | Manual (researcher) |
| Stage 1: PASS/EXCLUDE/DEFER | Manual (researcher) |
| Prerequisites (source, manifest, bug, tests) | Manual (researcher) |
| Stage 2 screening run | Automated (runner) |
| Stage 2 result ingestion | Automated (update_candidates_from_run) |
| Stage 3 screening run | Automated (runner) |
| Stage 3 result ingestion | Automated (update_candidates_from_run) |
| Full truth authoring | Manual (researcher) + automated pipeline |
| Contract generation | Automated (contract_generator) |

---

## Quick Reference

```bash
# See current state
./scripts/screen.sh summarize

# Add a candidate
./scripts/screen.sh add --id my_func --source "authored" --lines 14 --complexity medium

# Review it
./scripts/screen.sh update-stage1 my_func --result PASS

# See what's blocked before Stage 2
./scripts/screen.sh list --state pass-blocked

# After completing prerequisites, verify it's ready
./scripts/screen.sh show my_func

# Run Stage 2 screening
./scripts/screen.sh t2-screen-wave1

# Ingest results
./scripts/screen.sh ingest-stage2
```
