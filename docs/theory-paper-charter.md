# Theory Companion Paper — Charter (T0-1)

**Status:** Draft for ratification. Gate for the entire T-track (WOV-260).
**Authority:** Subordinate to `docs/design-constitution.tex` and the frozen
empirical record (`preprint-v1`). This charter governs a *new, separate*
manuscript; it does not modify the empirical paper, the Constitution,
scorers, runners, datasets, or frozen analysis scripts.
**Working title:** *Structured Representation for Code LLMs: When Format Can
and Cannot Help a Bounded Learner, and Why.*
**Output target:** arXiv preprint, ML-theory flavored (primary category to be
decided in T4-4; candidates cs.LG / stat.ML / cs.SE).
**Relation to the empirical study:** theory-first **companion**. The frozen
preprint (`preprint-v1`) is the empirical anchor; this paper is its
theoretical sibling, not a revision of it.

---

## 0. How to read this

This charter fixes, before any mathematics is written, four things that are
expensive to change later: (1) the thesis, (2) the role each area of
mathematics is required to play, (3) the honesty guardrails, and (4) the
section spine. Everything in the T1–T4 milestones derives from this document.
If a later issue cannot be made to serve the thesis under the guardrails, the
issue is cut, not the guardrails.

---

## 1. Thesis (one sentence, load-bearing)

> Under information parity, no representation can lower the Bayes-optimal
> predictor's risk — a consequence of the data-processing inequality and
> sufficiency — so any genuine code-representation effect on an LLM is a
> **bounded-computation** phenomenon whose maximum magnitude is controlled by
> a capacity/complexity term rather than by information content; the Lumen T1
> clean null is the predicted information-limit outcome, and the theory
> localizes where a bounded-regime effect should appear.

Two halves, both required:

- **Negative half (explains the null).** At constant information, the optimum
  is format-invariant. The observed T1 null (r = +0.10, raw p = 0.36, no
  ceiling) is therefore *what the theory predicts*, not an anomaly to explain
  away.
- **Positive half (pays rent).** Effects, if they exist, live in the bounded
  regime (finite capacity / finite sample / bounded compute). The theory
  bounds their size and **names the regime to test next**. This is the
  paper's forward-looking contribution and the antidote to "a math-dressed
  null."

The positive half is delivered as **falsifiable predictions** (T3-2), never
as established empirical findings.

---

## 2. The four mathematical areas and their required roles

All four areas were chosen deliberately (also as a learning vehicle: target
level is Japanese HS math through 数IIIC plus undergraduate physics
mathematics, pushed slightly above). The standing rule is **no decorative
math**: each area must connect to a theorem or a section it is necessary for.
The spine is information theory + statistical learning theory; category
theory and OT/information geometry are formalization/quantification layers
that survive **only if they earn a theorem**.

| Area | Required role | Anchored in |
|---|---|---|
| Measure-theoretic probability | Rigorous setup: representations as measurable maps, predictors as Markov kernels, risk and Bayes risk | §2 (T1-1) |
| Information theory | Parity = sufficiency / Markov-equivalence; the irrelevance theorem via DPI; rate-distortion for lossy reps | §4 (T1-2, T2-1, T2-2) |
| Statistical learning theory | The bounded-learner gap; an upper bound on achievable representation advantage via capacity/sample complexity | §5 (T1-3, T2-4) |
| Category theory | Why C1+ is the correct control (parity = retraction); the round-trip C4→C1+→C4′ defect | §3 (T1-4, T2-3) — **go/no-go** |
| Optimal transport + information geometry | Quantitative parity defect (Wasserstein between induced predictive distributions; Fisher sensitivity), tied to R4 data | §6 (T1-5, T2-5) — **go/no-go** |

**Go/no-go discipline.** Category theory (T1-4 → T2-3) and OT/info-geometry
(T1-5 → T2-5) each carry an explicit decision: if the area produces only a
restatement of the information-theoretic content and buys no new proposition,
it is demoted from a section to a remark. The decision is recorded in the
corresponding T2 issue.

---

## 3. Honesty guardrails (binding on every T-track issue)

A math-heavy paper built on top of a null result is most at risk of reading
as obfuscation. These guardrails exist to prevent that, and they inherit the
posture of `docs/next-phase-design.md` §5.

- **G1 — The null is a prediction, not a disappointment.** The T1 clean null
  is presented as the predicted information-limit outcome. It is never framed
  as a result the method "should have" turned positive, nor explained away.
- **G2 — No manufactured positive claim.** No structure-advantage claim is
  built on top of the null. The theory's positive content is *where* effects
  can exist (bounded regime), stated as falsifiable predictions, not as
  findings.
- **G3 — Idealizations disclosed at every use.** The irrelevance theorem
  assumes Bayes-optimality (infinite-capacity limit) and exact parity; a real
  frozen LLM satisfies neither. Every invocation states which idealization it
  relies on. "Parity is operational, not absolute" (paper §3.3) is carried in
  as a formal caveat and quantified by the §6 parity defect.
- **G4 — No decorative math.** Category theory and OT/info-geometry stay only
  if they earn a theorem (§2 go/no-go). Elegance is not a justification.
- **G5 — Citation hygiene (from R6, verbatim).** Do not cite "SOAP" as a
  work; do not mischaracterize INDICT (Le et al., NeurIPS 2024); verify
  Clover, Plan-and-Solve, PAL before citing; find correct references
  independently rather than reusing prior confabulated exemplars.
- **G6 — Speculation labeled.** Anything beyond the proved theorems (e.g.,
  conjectured mechanisms inside real LLMs) is explicitly marked as conjecture.

---

## 4. Section spine

1. **Introduction** — the format-vs-information question restated formally;
   the companion relationship to `preprint-v1`; contributions.
2. **Preliminaries** — measure-theoretic setup: input space, representations
   as measurable maps, predictors as Markov kernels, loss, risk, Bayes risk.
   (T1-1)
3. **The category of representations** — the C-ladder as morphisms;
   information parity as a retraction; the round-trip defect. (T1-4, T2-3;
   go/no-go)
4. **Information parity and the irrelevance theorem** — sufficiency, DPI, the
   at-optimum invariance theorem; rate-distortion corollary for lossy reps.
   (T1-2, T2-1, T2-2)
5. **The bounded-learner gap** — where format can help once information is
   held constant; the upper bound on achievable advantage; the regime that
   activates it. (T1-3, T2-4)
6. **Quantitative parity defect** — Wasserstein distance between induced
   predictive distributions; Fisher-information sensitivity; connection to the
   R4 round-trip recovery data. (T1-5, T2-5; go/no-go)
7. **Empirical anchoring** — retrodict the Lumen T1 null and T3 ceiling
   through the theory; state the limits of the mapping. (T3-1)
8. **Predictions and falsifiable tests** — bounded-regime experiments the
   theory implies, each with a sign/size prediction and an explicit
   falsifier. (T3-2)
9. **Related work** — information-theoretic, learning-theoretic, and
   categorical views of representation, plus code-representation-for-LLMs.
   (T4-2)
10. **Limitations and honesty** — assumptions and failure modes; what the
    theory does *not* establish; red-team against overclaim. (T4-3)
11. **Conclusion.**

**Appendix.** Full proofs of all theorems, lemmas, and propositions,
each with its idealization disclosure attached. (T4-4)

---

## 5. Relation map (what feeds what)

- **`preprint-v1` (frozen empirical anchor)** supplies: the C-ladder, the
  information-parity control C1+, and the outcomes the theory must be
  consistent with — T1 clean null, T2 non-significant moderate effect, T3
  ceiling.
- **`docs/design-constitution.tex` §14.1** is the authoritative C-ladder:
  C2 = Raw AST, C3 = Typed AST, C4 = Contract IR, C1+ = annotated source
  projected from C4. Use these definitions, not the README's simplified
  table.
- **R4 round-trip data (empirical paper Appendix D)** supplies the
  structural-recovery rates the §6 parity-defect metric is computed against.
- **`docs/next-phase-design.md`** defines the R/P tracks; this paper is a new
  **T track**, gated on nothing of its own but consuming R4/R5 outputs as
  data and the R6 citation guardrails as policy.

---

## 6. T-track issue map (as created in Linear, Lumen project)

| Issue | Milestone | Deliverable |
|---|---|---|
| WOV-260 T0-1 | T0 | This charter |
| WOV-261 T0-2 | T0 | `paper-theory/` LaTeX skeleton, `notation.tex`, bib, build target |
| WOV-262 T1-1 | T1 | §2 measure-theoretic setup |
| WOV-263 T1-2 | T1 | Information theory + formal parity definition |
| WOV-264 T1-3 | T1 | Statistical learning theory foundations |
| WOV-265 T1-4 | T1 | Category theory foundations (go/no-go) |
| WOV-266 T1-5 | T1 | OT + information geometry foundations (go/no-go) |
| WOV-267 T2-1 | T2 | Definitions: structured representation, information parity |
| WOV-268 T2-2 | T2 | Irrelevance-at-optimum theorem (DPI ⇒ Bayes-risk invariance) |
| WOV-269 T2-3 | T2 | Category-theoretic parity-as-retraction (go/no-go) |
| WOV-270 T2-4 | T2 | Bounded-learner advantage upper bound |
| WOV-271 T2-5 | T2 | Quantitative parity defect (Wasserstein + Fisher) (go/no-go) |
| WOV-272 T3-1 | T3 | Retrodict T1 null / T3 ceiling |
| WOV-273 T3-2 | T3 | Falsifiable predictions + bounded-regime experiments |
| WOV-274 T4-1 | T4 | Full manuscript draft |
| WOV-275 T4-2 | T4 | Related work with citation hygiene |
| **T4-3** (not yet in Linear) | T4 | §10 Limitations/honesty + internal red-team against overclaim |
| **T4-4** (not yet in Linear) | T4 | Proof-check pass, polish, arXiv preparation |

> **Note.** T4-3 and T4-4 could not be created in Linear because the Wovol
> workspace hit its free issue limit. They are recorded here so they are not
> lost; create the Linear issues once the limit is lifted. T4-3 is the
> manuscript's integrity gate (guardrails G1/G2/G3) and must not be skipped.

---

## 7. Exit criteria for T0-1

- [ ] Thesis sentence (§1) ratified.
- [ ] Four-area role table (§2) and go/no-go discipline accepted.
- [ ] Honesty guardrails (§3) enumerated and accepted.
- [ ] Section spine (§4) ratified.
- [ ] Charter committed.

Once these are checked, T0-2 (scaffold `paper-theory/`) may begin. No T1/T2
issue starts before this charter exits.
