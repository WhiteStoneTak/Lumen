# Experimental Protocol — Lumen Route A Study

**Status:** Operational — Phase 1 scaffold (pipeline + pilot dataset)
**Authority:** This document is binding for the 90-day study. All terms are derived
from `docs/design-constitution.tex` v0.2.2, §14 (Experimental Protocol Addendum).
Any conflict between informal notes and this document is resolved in favour of the
constitution.

---

## 1. Scope

- Unit of analysis: a single, non-recursive Python function (standalone, no classes,
  no external-library imports beyond the standard library).
- Three task types: **T1** (program understanding), **T2** (bug detection), **T3**
  (code transformation).
- T2 composite score (0–3) is the **primary endpoint** of the confirmatory family.
- Dataset size: 30–50 functions (target 50; minimum for analysis: 30).
- Pilot set: 10–15 functions with full ground truth.
- All outputs are in English.

---

## 2. Conditions (Definitive)

Drawn from constitution §14.1 (Condition Table).

| ID  | Label            | Format     | Info level | Purpose                              |
|-----|------------------|------------|------------|--------------------------------------|
| C1  | Source Text      | Text       | Base       | Baseline                             |
| C1+ | Annotated Text   | Text       | Enriched   | Information-enrichment control       |
| C2  | Raw AST          | Structured | Base       | Pure structure effect (no extra info)|
| C3  | Typed AST        | Structured | +Types     | Marginal type-annotation effect      |
| C4  | Contract IR      | Structured | Enriched   | Full enrichment in structured form   |

**Critical pair:** C1+ vs. C4 — same information content, different format.
C1+ is constructed by projecting C4's annotations back into Python source as:
- PEP 484-style inline type annotations, and
- a structured docstring block with preconditions, postconditions, and invariants.

C1+ is **not optional** and must be derived from C4 to preserve information parity.

---

## 3. File Naming and Path Conventions

Each function is identified by a short, human-readable `func_id` (e.g., `clamp`,
`count_vowels`). The `func_id` is the filename stem used consistently across all
derived artifacts.

```
data/functions/raw/{func_id}.py          # C1: raw Python source
data/functions/ast/{func_id}.json        # C2: AST JSON (lumen_schema: ast-v1)
data/functions/typed_ast/{func_id}.json  # C3: typed AST JSON
data/functions/ir/{func_id}.json         # C4: contract-augmented IR
data/functions/annotated_text/{func_id}.py  # C1+: annotated source text

data/contracts/raw/{func_id}.json        # raw LLM-generated contract
data/contracts/reviewed/{func_id}.json   # author-reviewed contract
data/contracts/diffs/{func_id}.json      # edit provenance log

data/ground_truth/checklists/{func_id}.json  # T1 property checklist
data/ground_truth/bugs/{func_id}.json        # T2 bug annotation
data/ground_truth/tests/{func_id}_test.py    # T3 test suite
```

---

## 4. Artifact Schemas

All JSON artifacts include a `lumen_schema` field for forward compatibility.

### 4.1 AST JSON (`ast-v1`)

```json
{
  "lumen_schema": "ast-v1",
  "func_id": "<string>",
  "source_hash": "<sha256 hex of raw .py file>",
  "ast": { ... }
}
```

The `ast` field is a recursive dict serialization of the Python `ast.AST` node tree.
Each node is `{"_type": "<NodeClassName>", "<field>": ...}`. Lists and scalars are
passed through unchanged. Produced by `src/pipeline/text_to_ast.py`.

### 4.2 Contract Raw (`contract-raw-v1`)

```json
{
  "lumen_schema": "contract-raw-v1",
  "func_id": "<string>",
  "source_hash": "<sha256 hex>",
  "generation_model": "<model id or null>",
  "generation_attempt": 0,
  "preconditions": ["<string assertion>", ...],
  "postconditions": ["<string assertion>", ...],
  "invariants": ["<string assertion>", ...]
}
```

Produced by `src/pipeline/contract_generator.py`. Not to be edited by the author.

### 4.3 Contract Reviewed (`contract-reviewed-v1`)

Same top-level fields as `contract-raw-v1` except `lumen_schema` is
`contract-reviewed-v1`. This file reflects the author-reviewed version and is the
authoritative contract used in C4 and C1+.

### 4.4 Contract Diff (`contract-diff-v1`)

```json
{
  "lumen_schema": "contract-diff-v1",
  "func_id": "<string>",
  "source_hash": "<sha256 hex>",
  "regeneration_attempts": 0,
  "edits": [
    {
      "kind": "correct | delete | add",
      "clause_type": "precondition | postcondition | invariant",
      "original": "<string or null>",
      "revised": "<string or null>",
      "justification": "<one line>"
    }
  ]
}
```

See constitution §14.2 for the exhaustive list of allowed and disallowed author edits.
An empty `edits` list means the raw contract was accepted without modification.

---

## 5. Dataset Constraints

- Functions must be **non-recursive** (verified by `check_no_recursion.py`).
- Functions must be **single-function** — one top-level `def`, no nested classes.
- Functions must be **standalone** — no imports beyond the Python standard library.
- Each function must have a correct version (for T1/T3) and a buggy version (for T2).
- Bugs are introduced manually by the author in controlled categories:
  off-by-one, wrong comparison operator, missing boundary check, incorrect variable
  reference, swapped arguments.
- Each bug is annotated with: (a) line range, (b) bug category, (c) reference fix.

---

## 6. Contract Review Provenance

See constitution §14.2 for the full protocol. Summary:

**Allowed author edits (review stage):**
1. Correct a factually wrong predicate.
2. Delete a vacuously true, untestable, or redundant clause.
3. Add at most one missing clause per function.

**Author may NOT:** rewrite the contract from scratch, add domain knowledge not
inferable from the source, or introduce information not derivable from the code.

**Rejection criteria** (triggers regeneration):
- > 50% of clauses are factually incorrect.
- The contract misidentifies the return type.
- The contract contains no postconditions.

Up to two regeneration attempts. Third failure → function excluded, exclusion logged.

Every contract diff must record `regeneration_attempts` (0, 1, or 2) in the diff file.

---

## 7. Scoring Overview

### Primary metrics (confirmatory, auto-scored)

| Task | Metric                        | Primary endpoint? |
|------|-------------------------------|-------------------|
| T1   | Property-checklist fraction   | Yes               |
| T2   | Composite 0–3                 | Yes — **primary** |
| T3   | Test pass rate (0.0–1.0)      | Yes               |

T2 is the **designated primary endpoint** within the confirmatory family.

T2 sub-scores (each 0 or 1):
- **Location:** LLM identifies the correct line/expression.
- **Diagnosis:** LLM names the correct bug category.
- **Fix:** The proposed fix passes the full test suite.

### Secondary metrics (exploratory only)

| Task | Metric              |
|------|---------------------|
| T1   | Holistic 1–5 score  |

T1 holistic score is human-judged, blind. Intra-rater reliability (weighted κ)
reported. Demoted to appendix-only if κ < 0.6. Never used in confirmatory analysis.

T3 "minimal modification" metric: **dropped** (constitution v0.2.2 §14.3).

---

## 8. LLM Selection

- **Test subjects (2):** Claude Sonnet (Anthropic), GPT-4o (OpenAI). Final model IDs
  to be recorded here when locked.
- **Contract-generation LLM:** Must differ from both test subjects. Selection deferred
  to Phase 1 execution; record final choice here before contract generation begins.

---

## 9. Statistical Analysis Plan

- **Design:** Within-subjects (repeated-measures). Unit = (function, condition, model).
- **Confirmatory hypotheses:** H1, H2, H3 (see constitution §5).
- **Correction:** Holm–Bonferroni across the confirmatory family (3 hypotheses × 3
  primary metrics = 9 tests).
- **Significance level:** α = 0.05 (after correction).
- **Test:** Wilcoxon signed-rank (default). Mixed-effects alternative deferred to
  Phase 2 decision.
- **Exploratory analyses:** Uncorrected p-values, labeled "exploratory" throughout.

---

## 10. Analysis Freeze / Amendments

- Confirmatory analysis scripts (`analyze_confirmatory.py`) must be **frozen before
  data collection begins**.
- Freeze date: _TBD — record here before Phase 2 starts_.
- Any post-hoc addition to `analyze_confirmatory.py` requires a dated amendment note
  at the top of the file explaining what was added and why.
- Post-hoc analyses go in `analyze_exploratory.py` only and must be clearly labeled.
- Pre-registration: _TBD — OSF or AsPredicted link to be recorded here_.
