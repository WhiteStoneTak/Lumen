# T1 (program-understanding) scoring specification

Linear: WOV-237 (R1-3). Canonical, reproducible specification of the T1 scorer.
Implementation: `src/experiment/score_t1_checklist.py`, exposed under the
protocol name `src/experiment/score_t1.py` (`score_t1 = score_t1_checklist`).
Deterministic; **no LLM judge** is used, so two independent implementers
following this spec produce identical scores.

## 1. Inputs

- **Ground truth:** `data/ground_truth/checklists/{func_id}.json`, schema
  `t1-checklist-v1`. A list of `properties`, each with `property_id`,
  `category` (`inputs|outputs|behavior|edge_case`), `statement` (the canonical
  natural-language property), and `required`.
- **Model response:** free text.

## 2. Score

```
score = matched_properties / total_properties   ∈ [0, 1]
```

`total_properties` = number of properties in the checklist. Each property is
scored 0 or 1 by the deterministic rule in §3. `status = "ok"` for a non-empty
response; an empty/whitespace-only response yields `status = "invalid_response"`,
`score = 0.0`, `failure_reason.code = "empty_response"` (not pooled as a 0).

## 3. Per-property match rule (deterministic)

For one property `statement` and the response, both lowercased and normalised
(`normalize_t1_response`: lowercase, strip punctuation to spaces, collapse
whitespace):

1. **Key-term extraction** (`_extract_key_terms`): tokenise the statement on
   `[^a-z0-9_ ]`; keep tokens of length ≥ 2 that are not in the stop-word set;
   deduplicate preserving order. These are the property's semantic anchors
   (parameter names, type names, numbers, domain vocabulary).
2. **No key terms** → property scores **0** (`note: "No key terms…"`).
3. **Term presence**: a key term is "found" iff it occurs in the normalised
   response at a **word boundary** (`\bterm\b`) — prevents `lo`/`hi` from
   matching inside `float`/`this`.
4. **Coverage threshold**: require at least `min(2, len(key_terms))` key terms
   found. Fewer → property scores **0**.
5. **Negation guard** (`_has_nearby_negation`): for each of the first two found
   terms, if a negation token (`not `, `never`, `incorrect`, `wrong`,
   `doesn't`, `does not`, `cannot`, `can't`, `isn't`, `aren't`, `wasn't`,
   `weren't`, `inaccurate`, `untrue`) appears within the **15 characters
   immediately preceding** an occurrence of the term, the property scores **0**
   (the model stated the property's negation). The 15-char window is
   deliberately tight so an unrelated "not …" elsewhere does not suppress a
   genuine match.
6. Otherwise the property scores **1**.

The result records `matched` and `total`; `score == matched / total` exactly
(unit-tested). The rule is a conservative recall measure: a property counts
only when its anchors are present and not locally negated.

## 4. Anti-ceiling analysis (dataset-derived)

The T2 failure (backlog L1-06, paper §5.3) was a 0–3 integer composite that
realised only **3** distinct values and saturated at 2, collapsing the
effective Wilcoxon *n* from 30 to ~14. The T1 scorer cannot repeat this on this
dataset, by construction:

- The score is `k / P` where `P` is the property count. The currently authored
  checklists have **P = 7, 8, 9** (count_vowels, is_sorted, clamp), giving
  **8, 9, 10** distinct attainable values *per function* — already 2–3× the T2
  composite's realised resolution.
- Pooling across just these three property counts yields **23 distinct
  attainable score values** in [0, 1]:
  `0, 1/9, 1/8, 1/7, 2/9, 1/4, 2/7, 1/3, 3/8, 3/7, 4/9, 1/2, 5/9, 4/7, 5/8,
  2/3, 5/7, 3/4, 7/9, 6/7, 7/8, 8/9, 1`.
- Resolution **grows with P**: any function with P ≥ 7 contributes ≥ 8 levels.
  The protocol's functions are non-trivial (multiple inputs, outputs, behaviours,
  edge cases), so P is bounded well above the ~3 that caused the T2 collapse.
- There is no hard ceiling short of 1.0 that is structurally unreachable the way
  T2's composite-of-3 was (its location sub-score was identically 0 — see R1-1).
  Each property is independently attainable, so the top of the scale is live.

**Conclusion:** for P ≥ 4 the per-function resolution (≥ 5 levels) already
exceeds T2's realised 3; at the dataset's actual P = 7–9 the pooled scale has 23
levels. Tie mass cannot collapse the effective *n* the way the T2 composite did.
When the confirmatory T1 checklists (30 functions) are authored for R5, this
analysis must be re-run on their realised P distribution and the realised
score distribution checked against this argument (R1-5 pilot).

## 5. Tests

`tests/test_score_t1_checklist.py` covers key-term extraction, the per-property
matcher (match / no-match / negation-suppression), and integration on the three
real checklists with perfect (→ high), partial (→ fractional), and contradictory
(→ low) responses, plus `score == matched/total`. `tests/test_score_t1.py`
checks the canonical alias and the per-function attainable-resolution claim.

## 6. Scope

Scorer only. **No T1 model data is collected here** — collection is R5, gated on
Constitution v0.3.
