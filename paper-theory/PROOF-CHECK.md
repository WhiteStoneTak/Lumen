# Independent proof-check ledger — theory companion paper

**Issue:** WOV-277 (T4-4), **Step 1 only**: *Independent proof-check of every
theorem / lemma / proposition (each assumption used, each step justified);
verify all idealization disclosures are attached.*

Steps 2 (notation / cross-reference / figure consistency) and 3 (arXiv
packaging) of WOV-277 are **out of scope** and were not performed.

**Method.** Each formal result was re-derived from its stated hypotheses
without trusting the surrounding prose: every invoked lemma was checked to be
actually applicable, every "by X" was confirmed to discharge the step it
claims, and the hypothesis each result *needs* was compared against the one it
*states* (and against the parity-ledger `tab:parity-ledger`). Numerical claims
were recomputed in Python. The manuscript was rebuilt with `tectonic`; all
cross-references and citations resolve (no `undefined`/`??`).

**Verdict.** All 60 formal environments + 5 predictions are sound as stated,
with **one** genuine defect found and fixed (`prop:abs-strict`, see below) and
a small number of cosmetic notes left for the Step-2 polish pass. The
idealization-disclosure guardrail (G3) is satisfied.

---

## 1. Defect found and fixed

### `prop:abs-strict` (§4, "Absolute parity is strictly stronger") — converse witness

**Problem.** The converse direction constructed the witness as
`rep' = (rep, N)` where `N ⊥ (X,Y)` is "independent noise." A representation is
a *deterministic* measurable map of `X` (`def:rep`); a function of `X` that is
independent of `X` is a.s. constant, so such an `N` forces
`σ(rep') = σ(rep)` — contradicting the very `σ(rep') ⊋ σ(rep)` the witness is
meant to exhibit. The step "rep' retains every predictive bit … yet
σ(rep') ⊋ σ(rep)" was therefore not justified by the construction given.

**Fix (committed).** Replaced the adjoined-noise construction with a rigorous
one that draws the extra coordinate from *within* `X`: take `rep` sufficient and
adjoin a coordinate `N` of the input that is not `σ(rep)`-measurable (a
predictively inert / surface-byte feature). Then `rep'` refines `rep`
(`σ(rep) ⊆ σ(rep') ⊆ B(X)`), and `cor:dpi-rep` along the refinement squeezes
`I(Y;rep'(X))` between `I(Y;rep(X))` and `I(Y;X)`, which sufficiency of `rep`
collapses to equality — so `rep'` is sufficient (`rep ≡_par rep'`) while
`σ(rep') ⊋ σ(rep)`. A parenthetical now records explicitly why independent
noise cannot serve. The result statement is unchanged and was already
independently witnessed by the C-ladder (`C1⁺` vs `C4`) and by
`prop:decode-parity`(c); the fix only repairs the illustrative proof step.

**Impact on downstream results: none.** Nothing depends on the *method* of the
witness, only on the truth of `prop:abs-strict`, which is unchanged.
`thm:retraction`(iii), `cor:defect-finer-order`, `rem:which-parity`, and
`tab:cladder` all cite the statement, not the construction.

---

## 2. Per-section verification ledger

Legend: ✓ = re-derived and sound; hypotheses listed are the ones actually used.

### §2 Preliminaries
| Result | Verdict | Note |
|---|---|---|
| `ass:sbs` standard Borel model | ✓ | standardness used only for `prop:disint` regularization, as claimed |
| `def:rep`, `def:kernel`, `def:predictor`, `def:risk`, `def:bayesrisk` | ✓ | definitions; `R*(rep)` monotone under refinement justified by tower rule |
| `prop:rn` Radon–Nikodym | ✓ | standard; cited correctly |
| `prop:disint` disintegration | ✓ | standardness of `Y` is where it is spent, correctly flagged |

### §3 Category of representations (GO)
| Result | Verdict | Note |
|---|---|---|
| `def:category … def:parity-rung` | ✓ | retraction eq. `p∘e=id_B` set up correctly |
| `thm:retraction` (i) idempotent splitting | ✓ | `φ∘φ=e(p e)p=φ`; split idempotent ⟹ `B≅im φ` |
| `thm:retraction` (ii) compositionality | ✓ | composite retraction + `φ_AC=e₁φ_BC p₁`; both-absolute equivalence checked both directions (morphism types verified A→B→C) |
| `thm:retraction` (iii) info-invisibility | ✓ | uses `suff-iff-mi` + `irrelevance` + `abs-strict`; defect in common kernel argument sound |
| `cor:defect-subadditive` | ✓ | triangle inequality on `W₁`; (ii) supplies intermediate laws |

### §4 Information parity & irrelevance
| Result | Verdict | Note |
|---|---|---|
| `def:entropy/kl/mi`, chain rule | ✓ | |
| `lem:dpi` DPI | ✓ | two-order chain-rule expansion; equality case correct |
| `cor:dpi-rep` | ✓ | `(U,V,W)=(Y,X,rep(X))`, Markov from measurability |
| `prop:suff-iff-mi` | ✓ | equality case of `cor:dpi-rep` = sufficiency |
| `prop:fisher-neyman` | ✓ | factorization theorem; standard-Borel supplies r.c.p. |
| `def:ratedist`, `def:parity` | ✓ | operational vs absolute correctly separated |
| **`prop:abs-strict`** | ✓ (after fix) | see §1 above |
| `prop:decode-parity` (a)(b)(c) | ✓ | (c) is the rigorous inert-coordinate witness |
| `thm:irrelevance` | ✓ | proof in appendix; see below |
| `cor:ratedist-gap` (a)(b) | ✓ | proof in appendix; see below |

### §5 Bounded-learner gap
| Result | Verdict | Note |
|---|---|---|
| `def:induced-class`, `def:emp-risk` (excess decomp `eq:excess`) | ✓ | three-term split (approx / info-gap / estimation) correct |
| `def:vc`, `def:rademacher`, `thm:uniform` | ✓ | symmetrization + McDiarmid (const `1/n` for `ℓ∈[0,1]`); est. error `4R+O(√…)` (factor 4 = ERM + in-class opt) |
| `prop:capacity-separation` | ✓ | bijective reparam keeps `σ`/info, inflates margin-norm ⟹ Rademacher; sound |
| `def:advantage`, `thm:bounded-gap` | ✓ | proof in appendix; sandwich correct, info channel cancels |
| `cor:realizable-gap`, `cor:size-gap` | ✓ | `Δ(rep',rep)=−Δ(rep,rep')`; union bound `1−2δ` |
| `prop:regime` (i)(ii)(iii) | ✓ | `n≳(4c₀)²·C` threshold; `VC(H∘rep)≤VC(H)` (shattered set maps to shattered set of equal size) verified |

### §6 Quantitative parity defect (GO)
| Result | Verdict | Note |
|---|---|---|
| `def:wasserstein`, `prop:kr-duality` | ✓ | KR duality cited correctly |
| `def:fisher`, `prop:kl-fisher` | ✓ | KL Hessian = Fisher to 2nd order |
| `def:parity-defect`, `def:coupled-transport` | ✓ | `eq:marginal-le-coupled` is joint convexity of `W₁` (correct direction: marginal ≤ coupled) |
| `thm:defect-risk-gap` | ✓ | proof in appendix; per-instance KR, `Y`-free integrand collapses to `E_X` |
| `prop:defect-fisher-local` | ✓ | proof in appendix; Pinsker+Fisher, coefficient `½=√¼` confirmed |
| `cor:defect-two-term`, `cor:defect-finer-order` | ✓ | min-of-two ≤ sum; refinement-over-info-gap argument sound |
| `ex:r4-defect` + `tab:r4-defect` | ✓ | **all numbers recomputed**, see §4 below |

### §7 Empirical anchoring / §8 Predictions
Strictly retrodiction and falsifiable conjecture (not proved results, by design;
guardrails G1/G2/G6). Checked that every invocation of a theorem matches the
theorem's actual content: T1↔`thm:irrelevance`+`thm:bounded-gap`,
T3↔`cor:realizable-gap`+`prop:regime`(iii), T2↔`prop:regime`(ii). Sign-agnostic
framing (F1 prohibition / F2 trend) is consistent with the one-sided bounds.
The `pred:size` envelope `|Δ| ≤ min{Φ, c·δ_par}+o(‖v̄‖)` correctly combines
`cor:size-gap` and `thm:defect-risk-gap`/`cor:defect-two-term`. ✓

### Appendix proofs
| Proof | Verdict | Key check |
|---|---|---|
| `lem:bayes-functional` | ✓ | `R*(rep)=E[G(q_rep)]`; `G` concave (inf of affines); monotonicity via conditional Jensen (correct direction) |
| `lem:suff-collapse` | ✓ | sufficiency ⟺ `q_rep=q_id` a.s.; tower rule + monotone-class on standard Borel |
| `thm:irrelevance` | ✓ | parity ⟹ both sufficient ⟹ posteriors collapse ⟹ equal `G` integrands ⟹ equal Bayes risk; absolute parity never used |
| `cor:ratedist-gap` | ✓ | (a) log loss `G(p)=H(p)`; (b) TV/Pinsker/Jensen with `E[KL(q_id‖q_rep)]=I(Y;X\|rep(X))=infogap` verified |
| `thm:retraction`, `cor:defect-subadditive` | ✓ | categorical algebra re-derived (see §3 row) |
| `thm:bounded-gap` | ✓ | floor (deterministic) + ceiling (`thm:uniform`) − subtraction; `R*(id)` cancels; no info term |
| `thm:defect-risk-gap` | ✓ | KR per instance + Jensen; parity cancels middle gap |
| `prop:defect-fisher-local` | ✓ | bounded-loss/TV + Pinsker + `prop:kl-fisher` at aggregate `v̄`; remainder is 2nd-order Taylor |

---

## 3. Idealization-disclosure audit (guardrail G3)

G3 requires every invocation of `thm:irrelevance` to disclose the idealization
it rests on via `\idealization{…}`. Disclosures present: §4 ×4
(`rem:which-parity`, `rem:parity-ledger`, `rem:slogan`, `rem:ratedist-reading`),
§5 ×1 (`thm:bounded-gap`), §6 ×2 (`thm:defect-risk-gap`,
`prop:defect-fisher-local`), §7 ×2 (anchor-T1, anchor-T3), §8 ×1
(`rem:pred-honesty`), §10 ×1, appendix ×6 (proofs of irrelevance, ratedist-gap,
retraction, bounded-gap, defect-risk-gap, fisher-local). **Total 17.**

Every *theorem that consumes* the at-optimum result carries a disclosure,
located either at an adjacent remark or — per the README's stated design
("proofs migrate to the appendix, each with its idealization disclosure
attached") — at its appendix proof. In particular `thm:retraction`(iii)'s use of
irrelevance is disclosed on its appendix proof. **G3 satisfied.**

Minor note (Step-2, non-blocking): the §3 body statements (`thm:retraction`(iii),
`rem:cat-go-scope`) and `cor:defect-finer-order` invoke `thm:irrelevance` in
their *statements* and rely on the disclosure carried by their proofs /
already-disclosed inputs rather than a co-located one. This matches the paper's
convention; flagged only so the Step-2 pass can decide whether a one-line
pointer is wanted at the section-body sites.

---

## 4. Numerical re-verification (`ex:r4-defect` / `tab:r4-defect`)

Recomputed in Python from the R4 recovery profile (contracts 100%, node kinds
99.8%, parent–child edges 98.7%, types 96.4%, byte-exact 0/30), `v̄ᵢ = 1−rec`,
diagonal Fisher (unit on semantic coords, ≈0 on the inert byte coord), `L=λ=1`:

| Quantity | Paper | Recomputed |
|---|---|---|
| Global term `\overline{W₁} ≲ Σ_rel v̄ᵢ` | 0.051 | 0.0510 |
| Fisher term `√(v̄ᵀFv̄)` | 0.038 | 0.0383 |
| `δ_par = global + λ·Fisher` | 0.089 | 0.0893 |
| naive `‖v̄‖` (unit incl. byte) | ≈1.00 | 1.0007 |
| ratio naive / Fisher | ≈26 | 26.1 |

Fisher-coefficient cross-check (`prop:defect-fisher-local`): `√(½·½)=½=√¼`,
matching `eq:defect-fisher-local`. All consistent.

---

## 5. Build confirmation

`tectonic main.tex` → `main.pdf` (~390 KiB). No undefined references, no
undefined citations, no `??` literals. Remaining warnings are
overfull/underfull `\hbox` (typesetting), which belong to the Step-2 polish
pass and were intentionally not addressed here.
