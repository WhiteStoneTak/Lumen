# R1-2 — T2 diagnosis/fix sub-scores: keep binary (decision note)

Linear: WOV-236 (R1-2). Decides, with data, whether the T2 **diagnosis** and
**fix** sub-scores need continuous variants like the location sub-score did
(R1-1). **Decision: keep both binary.** No code change; frozen artifacts
untouched.

## 1. Per-sub-score tie contribution (full_t2_confirmatory_v2, 300 T2 records)

| Sub-score | Value distribution | Distinct | Marginal tied-pair fraction |
|---|---|---|---|
| location  | `{0: 300}` | **1** | **1.0000** |
| diagnosis | `{1: 219, 0: 81}` | 2 | 0.6045 |
| fix       | `{1: 254, 0: 46}` | 2 | 0.7395 |
| composite (0–3) | `{0: 19, 1: 89, 2: 192}` | 3 | 0.5000 |

The composite never reaches its ceiling of 3 for one reason only: **location is
0 for all 300 records**, so the maximum attainable composite is
diagnosis + fix = 2. location is the single pathological (zero-variance)
sub-score; diagnosis and fix both carry genuine variance (27% and 15% zeros).

## 2. The location fix alone resolves the saturation

Recomputing the composite with R1-1's continuous location substituted in, while
keeping diagnosis and fix **binary**:

| Composite | Distinct values | Tied-pair fraction |
|---|---|---|
| current (binary, location≡0) | 3 | 0.5000 |
| continuous location + binary diagnosis/fix | **60** | **0.0893** |

Fixing location alone cuts composite tie mass by ~82% (0.50 → 0.089) and lifts
the distinct-value count from 3 to 60. The ceiling-of-3 / effective-n collapse
documented in §5.3 is fully attributable to the location sub-score. Diagnosis
and fix do not need continuous variants to remove the saturation.

## 3. Why binary is defensible for diagnosis and fix

- **It is not saturation.** A binary item that genuinely separates the sample
  (~73/27 for diagnosis, ~85/15 for fix) is contributing real discrimination.
  Its high *marginal* tied-pair fraction is the arithmetic of any binary
  variable, not a measurement defect. The harmful quantity is tied *paired
  differences* in the C4-vs-C1+ Wilcoxon, and §2 shows continuous location
  already collapses those ties.
- **Fix → test-pass fraction belongs to T3/R1-4.** A continuous fix metric
  (passed/total tests) is attractive, but (a) it requires executing
  model-generated code, whose sandbox is the explicit deliverable of **R1-4**
  (WOV-238); building a second ad-hoc executor here would duplicate and
  pre-empt that design; and (b) T2 seeds a *single* defect, so a partial
  test-pass usually reflects an unrelated failure rather than graded
  bug-fixing. Test-pass fraction is the right continuous target for T3
  (multi-behaviour transformation), a weaker fit for T2's single-bug design.
- **Diagnosis has no objective graded ground truth in T2.** The truth layer is
  one canonical `bug_description` per function, not a checklist (checklists are
  the T1 mechanism). Grading diagnosis continuously would need an LLM-judge or
  token-overlap heuristic — subjective, and a Constitution-v0.3 / R3-scope
  decision, not an R1 measurement-mechanics fix.

## 4. Outcome

- Continuous **location** (R1-1) is the necessary and sufficient measurement fix
  for the T2 saturation.
- **diagnosis** and **fix** stay binary. If a future confirmatory re-analysis
  with continuous location still shows tie-driven power loss, revisit a
  test-pass-fraction fix metric once the R1-4 sandbox exists — recorded as a
  conditional follow-up, not a current need.
- No frozen artifact modified; no new scorer code required for this decision.
