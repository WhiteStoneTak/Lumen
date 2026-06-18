# Lumen Journal-Version Backlog

This file is the tracked backlog of findings and work items that the Lumen
paper's journal / extended version will need to address, but which were
deliberately scoped out of the preprint.

## Background

The Lumen paper received a (C) critical review with an attached meta-review.
The Tier 1 + Tier 2 findings — those that had to be fixed before a preprint
could be released — were addressed in the Phase 2 response sequence
(commits in the `6008a92`..`974dc9a` series on `main`). Tier 3 findings,
together with several broader work items implied by the response, were
explicitly deferred to the journal / extended version. Until now those
deferred items were not tracked in any single place. This file is that
single place.

Paper HEAD at the time this backlog was created: `974dc9a` (`phase7 (C)-resp
T-7: declare document scope (extended preprint)`).

This file is a backlog only. It does not modify the paper body, experimental
artifacts, governance JSON, the Constitution, scorers, runners, datasets, or
analysis scripts. It also does not assign priorities, schedules, or effort
estimates — it is a list, not a plan. Priorities are decided separately.

## Status legend

Each entry carries a `status` field. Initial value is `OPEN` for every item
(none has been started). Allowed values:

- `OPEN` — not started.
- `IN PROGRESS` — work has begun.
- `DONE` — addressed in the journal version (cite the commit / artifact).
- `DROPPED` — explicitly decided not to address; record the reason.

## A note on tone

Several backlog entries describe results or interpretations from
exploratory work or from review framings. The backlog must not restate those
in a confirmatory tone. The current authoritative confirmatory attempt is
`full_t2_confirmatory_v2`; any successor run is exploratory until promoted.

---

## 1. Deferred findings — Major group

### L3-01 — Information parity depends on an operational definition

- **Original severity:** Major (strong).
- **Paper location:** §3.3 (Information parity, operational definition);
  Appendix D.
- **What is the problem:** The information-parity claim between C1+ and C4
  rests decisively on an *operational* definition of information as the set
  of typed propositions. §3.3 itself discloses residual asymmetry — AST
  node-kind metadata, IR-level child ordering, and cross-reference structure
  between contract clauses are not preserved by C1+ — and concedes that under
  a Shannon-style definition C4 carries strictly more information. The paper
  flags this dependency openly, so the central claim is not falsified, but
  the *strength* of the parity claim is sensitive to definition choice.
- **Why deferred from the preprint:** Independently constraining this
  requires a C4 → C1+ → C4′ round-trip validation experiment that measures
  structural-recovery rates. That is an additional implementation and data
  collection task that cannot be closed by prose edits. Appendix D already
  exists as a placeholder for this experiment in the journal version.
- **Journal-version work:** Run the round-trip validation experiment and
  flesh out Appendix D from placeholder into a real section.
- **Dependencies / notes:** Tied to Appendix D and to §3.3's operational
  framing; results may inform whether §3.3 needs to be qualified further.
- **status:** DONE (R4-1 + R4-2 / WOV-243, WOV-244). Round-trip run on all 30
  functions: content recovery is high (contracts + shared-identifier links
  100%, node kinds 99.8%, types 96.4%, edges 98.7%), byte-exact AST identity
  0/30. Appendix D fleshed out; §3.2 residual-asymmetry paragraph re-qualified
  with the measured numbers. Artifacts: results/analysis/exploratory/roundtrip/.

### L3-02 — Bootstrap CI computed outside the frozen analysis script

- **Original severity:** Minor / Major boundary.
- **Paper location:** §3.6; Appendix E.
- **What is the problem:** A central reporting quantity — 95% bootstrap CIs
  — is computed by `scratch/bootstrap_ci_confirmatory.py`, not by the frozen
  `analyze_confirmatory.py`. Verification covers only point-estimate
  agreement (r, W, raw p); the CI computation methodology itself is not
  cross-checked. Constitution §17.4 mandates 95% bootstrap CIs and also
  defines the frozen-script regime, so computing a mandated quantity outside
  the frozen artifact is, under a strict reading of §17.4, a deviation that
  should have been documented as a protocol amendment. The paper discloses
  the sibling-script computation in §3.6 but does not label it an amendment.
- **Why deferred from the preprint:** Back-porting CI computation into the
  frozen analysis script requires a structurally equivalent
  re-implementation; this cannot be closed by prose edits. §6.2 already
  lists the back-port as a follow-on.
- **Journal-version work:** Either back-port the bootstrap CI into
  `analyze_confirmatory.py`, or cross-check the sibling script's CI
  methodology with an independent implementation.
- **Dependencies / notes:** Touches the frozen-script regime — any change
  has Constitution-level implications and should be coordinated with the
  v0.3 update (see §3 below).
- **status:** DONE (R2-1 / WOV-240) — resolved jointly with W-02; see that
  entry and `docs/protocol-amendment-R2-1-bootstrap-ci.md`.

### CC-01 — Two of three task families are uncollected

- **Original severity:** Major; highest acceptance-threat finding in the
  meta-review.
- **Paper location:** Whole-paper (§1.3 contributions; §3.3 tasks).
- **What is the problem:** The paper is framed as a methodology paper, but
  of the three task families (T1 / T2 / T3) only T2 has been collected. Six
  of nine confirmatory cells are uncollected placeholders. The central piece
  of the methodology (the C1+ information-parity control) is only
  empirically instantiated in T2. The (C) Reviewer-D persona singled this
  out as the only reject-level concern.
- **Why deferred from the preprint:** T1 and T3 collection each require a
  separate confirmatory pre-registration and a substantial data-collection
  effort. This cannot be closed by prose edits.
- **Journal-version work:** Pre-register and collect T1 and T3. See also
  the matching entry under §3 (whole-paper work items); the two must be
  cross-referenced when scheduling.
- **Dependencies / notes:** This is the largest item in the backlog by far.
  Any sequencing of journal-version work should account for it first.
- **status:** DONE (R5 / WOV-245..248). All nine confirmatory cells collected
  and analyzed. T1 (R5-1/R5-2): H1/T1 r_rb = +0.098, raw p = 0.361 (clean null,
  no ceiling; complete data 300/300). T3 (R5-3/R5-4): H1/T3 r_rb = +0.429, raw p = 0.219 but
  ceiling-censored (93.7% of T3 scores at 1.0, effective n ≈ 5; n = 26 funcs,
  4 pre-declared structural exclusions). No cell Holm-rejected (m = 9). The
  C1+ information-parity control is now instantiated on all three tasks; the
  central H1 (C4 > C1+) is unsupported throughout — clean null on T1, censored
  on T3, multiplicity-absorbed on T2. Decision-gate evaluated in
  docs/next-phase-design.md §4 (matched row: "C4 weak on T1/T3"; P1 gate not
  opened). Note: an initial T1 pass lost 27/300 cells to Anthropic credit
  exhaustion (claude-opus-4-6); recovered on resume after top-up — final T1
  dataset complete (300/300, 0 failures).
  Artifacts: results/analysis/confirmatory/full_t{1,3}_confirmatory_v1/.

---

## 2. Deferred findings — Minor group

### L1-06 — Reuse-value claim about rubric ceiling rests on an undefended assumption

- **Original severity:** Minor.
- **Paper location:** §5.3.
- **What is the problem:** §5.3 characterises the rubric ceiling as a
  "structural finding" and asserts that scaling n from 30 → 50 → 100 will
  not change the saturation rate. That reuse-value claim depends on the
  assumption that binary discretisation of the location sub-score saturates
  at the same rate regardless of n — an assumption the paper does not
  defend.
- **Why deferred from the preprint:** This is a framing / qualification
  fix, but the right wording depends on whether rubric refinement (see §3
  below) is pursued. Best handled together with the rubric-refinement work.
- **Journal-version work:** Either qualify the reuse-value claim
  (e.g. "under similar rubric design choices...") or argue explicitly for
  the generality of the ceiling property.
- **Dependencies / notes:** Cross-reference with the rubric-refinement
  work item in §3.
- **status:** OPEN

### L2-02 — Missing neighbouring related work in §2

- **Original severity:** Minor; **citation caveat — read carefully**.
- **Paper location:** §2 (Related Work).
- **What is the problem:** §2 omits neighbouring research areas —
  contract-based LLM consistency checking, AST-based hallucination
  detection, structured-prompting / focused-CoT — and not citing them risks
  making the novelty claim look overstated.
- **Citation caveats from the (C) review (must be honoured before any
  citation is added):**
  - "SOAP" is **not** a paper or system; it is the name of a program-analysis
    workshop venue ("State Of the Art in Program analysis"). Do **not**
    cite it as a work. This is a (C) confabulation.
  - "INDICT" (Le et al., NeurIPS 2024) exists, but it is a dual-critic
    framework for code generation. It is **not** "AST-based hallucination
    detection". The (C) characterisation of INDICT is wrong; cite it only
    with a correct characterisation.
  - Clover (Sun et al., SAIV 2024), Plan-and-Solve (Wang et al., ACL 2023),
    and PAL (Gao et al., ICML 2023) are real and the (C) descriptions are
    broadly correct.
  - "AST-based hallucination detection" as an area exists in the literature
    under other references; if §2 is to cover it, find appropriate
    citations independently rather than reusing the (C) exemplars.
- **Why deferred from the preprint:** Expanding Related Work properly
  requires citation work that must not be done under time pressure;
  inserting confabulated or mischaracterised citations into the paper is
  unacceptable.
- **Journal-version work:** Expand §2 to cover the neighbouring areas
  above, verifying the existence and bibliographic detail of every cited
  work before inclusion. Do not cite SOAP. Do not cite INDICT as AST-based
  hallucination detection.
- **status:** ADDRESSED in WOV-249 R6-1 / L2-02: empirical §2 now adds one
  positioning subsection covering contract/verifier-backed consistency checking,
  deterministic AST hallucination detection, and structured/focused prompting;
  SOAP is not cited and INDICT is omitted.

### L2-03 — §2.4 self-limitation may read as a double weakness

- **Original severity:** Minor.
- **Paper location:** §2.4 ("Novelty, circumscribed").
- **What is the problem:** The §2.4 self-limitation — that the contribution
  is the controlled combination rather than any individual ingredient — is
  intellectually honest, but when paired with a non-significant empirical
  result it can read as a double weakness ("method novelty also not
  demonstrated").
- **Why deferred from the preprint:** This is a framing question best
  revisited together with any other §2 / §4.1 framing tweaks in the journal
  version.
- **Journal-version work:** Optionally re-frame §2.4 to make explicit that
  the methodology itself is the deliverable and the empirical instantiation
  is diagnostic.
- **status:** OPEN

### L3-05 — Parse-failure exclusion is MNAR; sensitivity analysis missing

- **Original severity:** Minor.
- **Paper location:** §4.4; Tables 5 / 6.
- **What is the problem:** The gpt-5.5 parse-failure exclusion (12 / 120,
  concentrated in non-C1 conditions) is missing-not-at-random — failure is
  correlated with representation condition. The paper discloses the
  exclusion transparently, but it does not report the confirmatory-pair
  parse-failure rate as a baseline, so the temperature × representation
  confound is not visible to the reader.
- **Why deferred from the preprint:** Requires additional analysis on the
  collected data (parse-failure rates per cell; worst-case imputation
  sensitivity run); not a prose-only fix.
- **Journal-version work:** Add the confirmatory-pair parse-failure rate
  to the relevant Table caption, and add a sensitivity analysis that
  imputes parse-failed items at worst case (score 0).
- **status:** DONE (R2-2 / WOV-241). Confirmatory pair = 0/300 parse
  failures (baseline); successor gpt-5.5 = 12/120, non-C1 only (C1+ 2, C2 4,
  C3 3, C4 3). Worst-case 0-imputation: H3 inversion survives all four runs;
  gpt-5.5 strengthens −0.500 → −0.762, opus-4-7 unchanged (−1.000). Paper §4.4
  paragraph + Table 6 caption updated; exploratory analysis at
  results/analysis/exploratory/r2_2_parse_failure_sensitivity/. Script:
  scripts/r2_2_parse_failure_sensitivity.py.

### L6-04 — §4.1 "non-rejection is informative" wording check

- **Original severity:** Minor.
- **Paper location:** §4.1.
- **What is the problem:** The original §4.1 phrasing "non-rejection is
  informative rather than empty" is readable two ways: (i) absence of
  evidence ≠ evidence of absence (valid), or (ii) non-rejection as
  positive-direction qualified evidence (overclaim risk).
- **Important context:** §4.1 was rewritten in Phase 2 of the (C) response
  along an Informative Negative Outcomes path. The journal-version task is
  not to re-relitigate this, but to re-check that the current wording is
  consistent with the new negative-outcome-path framing whenever §4.1 is
  next touched.
- **Why deferred from the preprint:** Minor follow-up; not blocking.
- **Journal-version work:** When §4.1 is next revisited, check that the
  relevant sentence is consistent with the new framing.
- **status:** DONE (R0-4 / WOV-234) — verified, no change needed.
  Sentence-level classification of §4.1's H1-non-rejection prose:
  - Para 2 "fail to reject … no rejection on T2 … Informative Negative
    Outcomes path … materials released": factual/neutral — states the
    decision and the pre-registered classification, no effect claim.
  - Para 3 S1 "non-rejection is informative rather than empty":
    reading (i) — cashed out below as a power/measurement story, not as
    evidence the effect is real.
  - Para 3 S2 (r_rb = +0.581 in pre-registered direction, bootstrap CI
    excludes zero, raw p = 0.023 "would reject in isolation"): descriptive
    statistics, explicitly counterfactual ("in isolation"); the nearest
    approach to reading (ii) but does not assert C4 outperforms C1+.
  - Para 3 S3 ("the correction absorbs the moderate effect" at effective
    n = 14) and S4 (rubric ceiling → §3.6, §5.3): reading (i) —
    attributes the non-rejection to multiplicity + power + measurement
    artifact, i.e. absence of evidence ≠ evidence of absence.
  No sentence makes an affirmative reading-(ii) claim; S2's directional
  facts are subordinated by S3/S4. Wording is consistent with the
  Informative-Negative-Outcomes framing. No paper edit made.

### CC-02 — Naming-artifact disclosure better placed in §3.8

- **Original severity:** Minor.
- **Paper location:** §3.1; §3.8.
- **What is the problem:** The disclosure that `run_pilot.py` was reused
  for confirmatory data collection (a naming artifact) currently sits at
  the end of §3.1. The disclosure is stronger as a defence when placed in
  §3.8 (Pre-registration) alongside git provenance such as the scorer
  freeze commit.
- **Why deferred from the preprint:** Pure re-organisation; optional.
- **Journal-version work:** Move the naming-artifact paragraph from §3.1
  to §3.8.
- **status:** DONE (R0-3 / WOV-233). Moved the "One naming artifact
  warrants explicit note" paragraph from the end of §3.0 (Study phases)
  to §3.7 (Pre-registration), adjacent to the git-provenance discussion.
  The "the confirmatory run is not a pilot" disclosure survives verbatim.
  Section numbers cited above (§3.1/§3.8) reflect an earlier draft; the
  current numbering is §3.0 → §3.7. Committed in this change.

---

## 3. Whole-paper work items (not tied to a specific finding)

These come from the Phase 2 (C) response and from the Constitution. They
have no finding ID. They are listed here as facts about what the
journal-version scope contains; no priority or schedule is assigned.

### W-01 — Collect T1 and T3 task families

- **Source:** CC-01 above; §1.3 / §3.3 of the paper.
- **What:** Only T2 is currently collected; six of nine confirmatory cells
  are uncollected placeholders. T1 and T3 each require a separate
  confirmatory pre-registration before collection. This is a large item;
  no plan is set in this backlog.
- **Cross-reference:** CC-01.
- **status:** DONE (R5 / WOV-245..248). Both families pre-registered
  (`docs/preregistrations/t1-v1.md`, `t3-v1.md`), collected, and analyzed
  (`results/analysis/confirmatory/full_t{1,3}_confirmatory_v1/`). Nine-cell
  family complete; no Holm rejection. See CC-01 for the result summary.

### W-02 — Back-port bootstrap CI into the frozen analysis script

- **Source:** L3-02 above; already listed as a follow-on in §6.2.
- **What:** Either back-port the bootstrap CI computation into
  `analyze_confirmatory.py`, or independently cross-check the sibling
  script's CI methodology.
- **Cross-reference:** L3-02; coordinate with W-05 (Constitution v0.3).
- **status:** DONE (R2-1 / WOV-240). Path A taken: the percentile-bootstrap CI
  is back-ported into `analyze_confirmatory.py` behind `--with-ci` (default
  output unchanged); the scratch script is force-committed for provenance. H1/T2
  CI [+0.077, +0.917] reproduced exactly. H2/H3 differ via the R0-1 score-loader
  issue (documented). See `docs/protocol-amendment-R2-1-bootstrap-ci.md`. To be
  ratified in Constitution v0.3 (W-05 / R3).

### W-03 — C4 → C1+ → C4′ round-trip validation experiment

- **Source:** L3-01 above; Appendix D already exists as a placeholder.
- **What:** Implement and run the round-trip validation; replace
  Appendix D's placeholder content with the real experiment and results.
- **Cross-reference:** L3-01; possibly W-05 (round-trip may be promoted
  to protocol-level status in Constitution v0.3).
- **status:** DONE (R4-1 + R4-2 / WOV-243, WOV-244). Pipeline + metrics in
  src/experiment/roundtrip.py (spec docs/roundtrip-comparison-spec.md); all-30
  run + Appendix D written. Constitution v0.3 (R3) adopted round-trip as a
  reported diagnostic, threshold deferred (decision area 2).

### W-04 — Rubric refinement (location sub-score ceiling)

- **Source:** §5.3 and §6.2 already name this as a next step.
- **What:** Address the location sub-score ceiling identified in §5.3.
- **Cross-reference:** L1-06 (reuse-value framing depends on outcome of
  this work).
- **status:** OPEN

### W-05 — Constitution update to v0.3

- **Source:** Constitution §13 Phase 3 already plans a v0.3 update.
- **What:** Update `docs/design-constitution.tex` to v0.3. May include
  revisiting success criteria, promoting round-trip validation to
  protocol-level status, and recording any changes implied by W-02 / W-03.
  Scope of v0.3 is itself to be defined.
- **Cross-reference:** W-02, W-03.
- **status:** DONE (R3-1 / WOV-242). `docs/design-constitution.tex` bumped to
  v0.3 with a "Version 0.3 Changelog" section enumerating all five decision
  areas: (1) success criteria / T1+T3 primary endpoints on the R1 continuous
  scorers, frozen T2 composite retained, continuous T2 location = secondary;
  (2) round-trip = reported diagnostic, threshold deferred; (3) R2-1 CI
  amendment ratified + mandatory amendment procedure; (4) temperature-constraint
  sampling codified (fixed within model, per-cell parse rates disclosed);
  (5) pre-collection power analysis now required (closes OQ4). States T1/T3
  pre-registrations derive from v0.3. PDF rebuilt; README updated.
