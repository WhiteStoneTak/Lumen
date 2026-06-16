# Lumen Next-Phase Design

**Status:** Planning — not binding on the frozen confirmatory regime.
**Authority:** Subordinate to `docs/design-constitution.tex` (v0.2.2) and
`docs/journal-version-backlog.md`. Where this document assigns sequencing,
priorities, or gates, it is doing the one thing the backlog explicitly does
not do (the backlog is "a list, not a plan"; see its §intro). Where it
touches success criteria or the frozen-script regime, the Constitution
wins until a v0.3 update lands (item W-05).

**Created against repo HEAD:** `aafb84c` (`paper: retitle Bug-Detection
Pilot -> Study`). Paper is an extended preprint; the authoritative
confirmatory attempt is `full_t2_confirmatory_v2` (T2 only).

---

## 0. Purpose and how to read this

This document plans what comes after the Bug-Detection **Study** is fixed as
a research artifact. It has two tracks:

- **Research track (R0–R6)** — closes the deferred backlog and earns the
  evidence Lumen's central bet needs. Every R-phase maps to one or more
  existing backlog IDs (`W-0x`, `L3-0x`, `CC-0x`). This track is the spine.
- **Product track (P1–P3)** — the Semantic Coding Layer, then small DSLs,
  then (only if warranted) a Lumen Language. This track is **gated on
  research outcomes**. It is real, but it is downstream and conditional, not
  a parallel commitment.

The single most important framing, carried over from the paper's own §4.1
negative-outcome path: **Lumen's central bet (canonical structured core over
surface text) is still live, not proven.** C4 > C1+ came out directional and
consistent but did not reach Holm-corrected significance, and the largest
identified cause is a measurement ceiling, not an absence of effect. Nothing
in this plan should be written or executed in a way that converts that
"promising but not established" status into a confirmatory claim.

---

## 1. Evaluation of the external roadmap input

A roadmap proposal (ChatGPT, supplied 2026-06-10) was assessed before use.
Verdict: directionally sound on sequencing, but incomplete and loose on
specifics. Disposition:

**Accepted (matches paper + backlog):**
- "Better measurement before more data." The T2 composite saturates at 2
  (ceiling 3 never reached), shrinking the effective Wilcoxon n from 30 to
  ~13–14. Fixing the instrument before scaling n is correct and matches
  §5.3 / §6.2 and backlog `W-04` / `L1-06`.
- T1/T3 require a **separate** confirmatory pre-registration (matches `W-01`
  / `CC-01`).
- C4 → C1+ → C4′ round-trip validation as a follow-on (matches `W-03` /
  `L3-01`, Appendix D placeholder).
- "Layer before language." Do not start by building a programming language.

**Modified:**
- The proposal's linear 7-step chain is re-cut into a spine with parallel
  integrity work and an explicit Constitution-v0.3 gate before any new
  pre-registration (see R3). New confirmatory pre-registrations derive from
  the Constitution; changing scorers/criteria first and pre-registering
  second is the only safe order.
- The proposal's decision-branch table is kept but re-grounded (see §4).

**Rejected / corrected:**
- The proposal **omits `W-02` (back-port bootstrap CI into the frozen
  analysis script) and `W-05` (Constitution v0.3) entirely.** Both are
  research-integrity items in the backlog and are reinstated here as R2/R3.
- Condition definitions in the proposal (and in the README's simplified
  table) are loose: it describes C2 as "source + types" and C3 as "IR". The
  **authoritative** Constitution §14.1 table is used throughout this
  document instead: **C2 = Raw AST, C3 = Typed AST, C4 = Contract IR**, with
  C1+ = annotated source projected from C4.
- The proposal's "replication" language for the successor pair is not
  adopted. Per §3.4, the successor run is a robustness follow-on under
  temperature relaxation, **not** a cross-generation replication; the word
  "replication" survives only as a process/artifact-name descriptor.

**Out of scope of the proposal but required:** `L3-05` (MNAR parse-failure
sensitivity), `L2-02` (related-work expansion with the citation caveats),
`L2-03`, `L6-04`, `CC-02`. Folded into the R-track below.

---

## 2. Research track

Sequencing principle: close measurement and integrity gaps on **existing**
data first; settle the Constitution; only then launch new confirmatory
collection. Phases that do not touch the frozen regime can run in parallel.

### R0 — Fix the Bug-Detection Study as an artifact

- **Goal:** A citable, reproducible study that says exactly what the data
  support and no more.
- **Backlog:** `CC-02` (move the `run_pilot.py` naming-artifact paragraph
  from §3.1 to §3.8), `L6-04` (re-check the §4.1 "non-rejection is
  informative" wording against the negative-outcome framing).
- **Work:**
  - Title now reads "Bug-Detection Study" (done, `aafb84c`); keep the
    "confirmatory run is not a pilot" distinction intact everywhere.
  - Verify repo reproducibility end to end: raw outputs ↔ scores ↔ figures
    ↔ frozen scripts; confirm `analyze_confirmatory --run
    full_t2_confirmatory_v2` reproduces the reported point estimates.
- **Exit:** Reproduction reproduces point estimates; preprint frozen with a
  tag; no confirmatory-tone leakage about exploratory results.
- **Runs in parallel with:** nothing — gate for the rest.

### R1 — Measurement-design pass (the instrument)

- **Goal:** Replace the discretised, ceiling-prone T2 location sub-score and
  pre-empt the same failure in the not-yet-built T1/T3 scorers.
- **Backlog:** `W-04` (location sub-score ceiling), `L1-06` (reuse-value
  claim depends on this outcome).
- **Work:**
  - Add a **continuous-valued** T2 location metric (candidates: AST
    node-proximity distance, line-span overlap / IoU, normalized token
    distance) reported alongside — not replacing — the frozen 0–3 composite,
    so the confirmatory artifact stays intact.
  - Decide whether diagnosis/fix sub-scores also need continuous variants.
  - **Design** T1 property-checklist scoring and T3 test-pass scoring so
    they cannot saturate the way T2 did; document the anti-ceiling argument
    that `L1-06` says §5.3 currently lacks.
  - Validate the new rubric on a small held-out pilot (do **not** pool with
    confirmatory data).
- **Exit:** A continuous T2 metric exists and is sanity-checked; T1/T3
  scorer designs exist with an explicit non-saturation argument.
- **Mantra:** *more data later, better measurement first.*

### R2 — Analysis-integrity pass (on existing data)

- **Goal:** Close the two integrity gaps that do not need new collection.
- **Backlog:** `W-02` (bootstrap CI computed in `scratch/`, outside the
  frozen `analyze_confirmatory.py`, against Constitution §17.4), `L3-05`
  (MNAR parse-failure exclusion; no confirmatory-pair baseline; no
  worst-case imputation sensitivity).
- **Work:**
  - Either back-port the bootstrap CI into the frozen analysis script, or
    independently re-implement and cross-check the sibling script's CI
    methodology. Treat any change to the frozen regime as a documented
    protocol amendment, coordinated with R3.
  - Report confirmatory-pair parse-failure rate as a baseline; add a
    worst-case (score-0) imputation sensitivity run for the gpt-5.5
    exclusion (12/120, concentrated in non-C1 conditions).
- **Exit:** CI methodology is cross-checked; MNAR sensitivity reported.
- **Runs in parallel with:** R1 (different surface area).

### R3 — Constitution v0.3 (the gate)

- **Goal:** Fold R1/R2 outcomes into the binding design before any new
  pre-registration.
- **Backlog:** `W-05`.
- **Work:** Update `docs/design-constitution.tex` to v0.3 — revisit success
  criteria, decide whether the continuous metric and round-trip validation
  become protocol-level, and record amendments implied by `W-02`/`W-03`.
- **Exit:** v0.3 ratified. **No new confirmatory pre-registration starts
  before this exit.**
- **Depends on:** R1, R2.

### R4 — Round-trip validation (C4 → C1+ → C4′)

- **Goal:** Quantify how operational the C1+/C4 information parity really is,
  turning Appendix D from placeholder into a real section.
- **Backlog:** `W-03`, `L3-01`, Appendix D.
- **Work:** Project C4 → C1+ (annotated source), re-parse C1+ → C4′, and
  measure structural-recovery rates: node-kind retention, type-annotation
  retention, contract-clause retention, parent–child structure retention,
  cross-reference/semantic retention, and canonical-hash agreement.
- **Interpretation guard:** High recovery + C4 still winning strengthens the
  "structure itself matters" reading; it does **not** by itself establish it.
- **Exit:** Recovery rates reported; §3.3's operational-parity framing
  re-qualified if the data demand it.
- **Runs in parallel with:** R5 prep (no new task-family collection needed).

### R5 — T1 / T3 confirmatory collection

- **Goal:** Test whether the C4 > C1+ direction generalizes beyond bug
  detection to program understanding (T1) and code transformation (T3).
- **Backlog:** `W-01`, `CC-01` (largest item in the backlog).
- **Work:** Separate confirmatory pre-registrations (one per task family,
  derived from Constitution v0.3). Keep **C4 vs C1+ as the central
  comparison**; keep per-model analysis exploratory. Reuse the R1 scorers.
- **Exit:** T1 and/or T3 collected and analyzed under pre-registration; six
  uncollected confirmatory cells reduced.
- **Depends on:** R3 (and R1 scorers).

### R6 — Related work and framing

- **Goal:** Defend the novelty claim without importing bad citations.
- **Backlog:** `L2-02`, `L2-03`.
- **Citation guardrails (from the (C) review — honour before adding any
  cite):**
  - **Do not cite "SOAP" as a work** — it is a program-analysis workshop
    venue name, a (C) confabulation.
  - **Do not cite INDICT (Le et al., NeurIPS 2024) as "AST-based
    hallucination detection"** — it is a dual-critic code-generation
    framework; cite only with a correct characterization.
  - Clover (Sun et al., SAIV 2024), Plan-and-Solve (Wang et al., ACL 2023),
    PAL (Gao et al., ICML 2023) are real; verify before citing.
  - For "AST-based hallucination detection," find correct references
    independently rather than reusing the (C) exemplars.
- **Exit:** §2 covers contract-based consistency checking, AST-based
  hallucination detection, and structured-prompting, every cite verified.

---

## 3. Product track (gated, downstream)

Do not start P1 until at least one of R1/R5 gives a measured signal that the
structured representation helps beyond the current T2 ceiling artifact.
Before that, P-track is design sketching only.

### P1 — Semantic Coding Layer (prototype)

- **Idea:** Humans keep reading ordinary source and diffs; the AI works over
  a Lumen Core IR / semantic graph behind the source. Not a new language.
- **MVP (single Python function in, structured artifacts out):**
  - structured IR (C4-style),
  - contract summary,
  - likely-bug explanation,
  - semantic-patch proposal,
  - ordinary source diff for human review.
- No editor, compiler, or language runtime required at this stage.
- **Reuses:** the existing C1→C4 pipelines and the C4→C1+ projection.

### P2 — Small DSLs

Only once P1 shows the IR is worth authoring against. Candidates, smallest
first: Contract DSL (pre/post/invariant), Semantic Patch DSL (which meaning
changes how), Intent DSL (function/module intent), Projection DSL (how IR is
shown to human vs LLM). These are shared-meaning notations, not Python
replacements.

### P3 — Lumen Language

Only if, after P1/P2, the limits of recovering meaning from source text are
demonstrably binding and the round-trip data (R4) show structure carrying
weight. At that point a language is justified as the **human-facing
projection of the Core IR**, not as an ego goal. Until then, P3 is a
hypothesis, not a plan.

---

## 4. Decision gates

Re-grounded from the external proposal's branch table. "Strong" means a
pre-registered, multiple-comparison-surviving effect under the R1 metric —
not a raw-p or directional-only signal.

| Observed next result | Decision |
|---|---|
| Improved-rubric T2 keeps C4 > C1+ strongly | Advance bug-detection / code-review layer (P1) |
| C4 > C1+ also holds on T1 and T3 | Promote Semantic Coding Layer to the primary bet |
| C4 strong on T2 only | Scope Lumen to verification / review support |
| C4 weak on T1 / T3 | Revisit the LLM-facing projection design, not the language |
| C1+ stably ≥ C4 across tasks | Re-weight toward information design / annotated source over Core IR |
| C1+ ≥ C4 across all primary tasks | Formally re-evaluate the canonical-core-over-surface-text bet |

### R5 evaluation (2026-06-16, WOV-246 / WOV-248)

R5 collected and analyzed T1 and T3 under `t1-v1` / `t3-v1`. The
generalization question now has its first real answer, and it is **negative
for the central bet**:

- **T1 (understanding):** H1 (C4 > C1+) is a **clean null** —
  $r_{\text{rb}} = +0.051$, raw $p = 0.428$, CI $[-0.520, +0.614]$. The
  graded checklist scorer did **not** ceiling out (9 distinct values,
  mean 0.90), so this is a genuine no-effect, not a measurement artifact.
- **T3 (transformation):** H1 is **ceiling-censored** — $r_{\text{rb}} =
  +0.429$ but raw $p = 0.219$ on effective $n \approx 5$, because 93.7% of
  T3 scores are exactly 1.0 (both frozen models solve nearly everything).
  Untestable, exactly as pre-declared (`t3-v1` §3.3).
- **T2 (bug detection):** unchanged — moderate $r_{\text{rb}} = +0.58$ but
  **not** multiplicity-surviving.

Under the table's strict "strong = multiple-comparison-surviving"
definition, **C4 is strong on no task**, and the cleanest unconfounded
datum (T1, no ceiling) shows **no structure advantage at constant
information**. The matching row is **"C4 weak on T1 / T3 → Revisit the
LLM-facing projection design, not the language."** The "C4 > C1+ also holds
on T1 and T3" promotion row is **not** triggered.

**P1 gate (WOV-251/252):** the gate required "a measured signal that the
structured representation (C4) helps beyond the T2 ceiling artifact." R5
did **not** produce that signal (T1 null; T3 ceiling). **R5 does not open
the P1 implementation gate.** P1 implementation remains gated; the only
unblocked move is design/projection rework, consistent with the matched
row.

Current standing (updated): **C4 not established and, on the one
ceiling-free task (T1), shows no advantage over annotated text. Do not
promote the Semantic Coding Layer to the primary bet; revisit the
LLM-facing projection before any C4-as-canonical commitment. T3 needs a
harder dataset (or partial-credit transforms) before it can test anything;
T2 needs the rubric refinement (W-04).**

---

## 5. Guardrails (apply to every phase)

- **No confirmatory tone on exploratory results.** Successor-pair and any
  post-hoc findings stay exploratory until promoted under pre-registration.
- **Frozen-script regime is sacred** until v0.3 (R3). Additions (e.g. the
  continuous metric) sit alongside the frozen artifact; they do not mutate
  it. Changes that must touch it are documented protocol amendments.
- **"Not a pilot" stays intact.** The Phase-2 pilot and the confirmatory T2
  collection remain distinct in every document.
- **Information parity is operational, not absolute** (§3.3). R4 measures
  exactly how operational; do not overstate parity before those data exist.
- **Citation hygiene** per R6 — no confabulated or mischaracterized cites.

---

## 6. What this document does not do

It does not modify the paper body, the Constitution, scorers, runners,
datasets, frozen analysis scripts, or governance JSON. It does not start any
new data collection. It assigns sequencing and gates only; concrete
pre-registrations, effort estimates, and schedules are produced per-phase
when that phase is actually opened. Backlog IDs remain the source of truth
for the underlying findings.
