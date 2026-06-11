# R1-1 — Continuous-valued T2 location metric (design note + re-analysis)

Linear: WOV-235 (R1-1), backlog W-04, paper §5.3.
Status: **exploratory** measurement-design instrument. The frozen confirmatory
composite and `analyze_confirmatory.py` are untouched; this metric is reported
*alongside* them and is not used for confirmatory inference until (and unless)
adopted in Constitution v0.3.

## 1. Problem

The frozen integer T2 composite (0–3) saturated at 2 (ceiling 3 never reached),
collapsing the effective Wilcoxon *n* from 30 to ~14 through ties (§5.3). The
binary **location** sub-score is the main culprit. Measured directly on the
frozen run `full_t2_confirmatory_v2` (300 T2 records):

```
frozen binary location subscore distribution: {0: 300}
```

The location sub-score is **0 for every one of the 300 records** — zero variance.
The frozen `score_t2_location` awards 1 only when an explicit ground-truth line
number appears, or one of three hard-coded code patterns (`clamp`,
`count_vowels`, `is_sorted`) matches. Frontier models almost always *quote the
buggy line* instead of citing a line number, so the sub-score never fires. It
contributes no signal and only adds tie mass that depresses the composite.

## 2. Metric chosen

A continuous location score in [0, 1] (`src/experiment/score_t2_continuous.py`)
built from two recovered signals, both anchored to the ground-truth source file
coordinate system (`data/functions/raw/{func_id}.py`, where the truth span
lives):

1. **Explicit line numbers** (`line 29`, `L29`, `#29`).
2. **Quoted-code recovery** — fenced/inline code fragments matched (whitespace-
   normalised, bidirectional substring) against the source lines to recover the
   line the model implicitly pointed at. This rescues the dominant
   "quoted the line, gave no number" case.

Both yield a predicted line set `P`; with truth set `T`:

- `P ∩ T ≠ ∅`  → **IoU** `|P∩T| / |P∪T|` (exact match → 1.0).
- `P ≠ ∅`, no overlap → `0.5 · max(0, 1 − (d−1)/W)`, `d` = min line distance,
  `W = max(4, func_len//4)`. Disjoint-and-far → exactly 0.0.
- `P = ∅` (unmappable) → 0.0.

The proximity branch is capped at 0.5, strictly below any genuine overlap, so
"near the line" can never beat "touched the line". IoU and AST node-proximity
were both candidates; line-span IoU + length-normalised proximity was chosen
because the truth layer is line-range based and it needs no AST round-trip,
keeping the exploratory metric dependency-free. (AST proximity remains a future
option for span-level bugs.)

## 3. Anti-saturation argument (empirically checked)

The binary location sub-score takes 2 nominal values {0,1} and, on this dataset,
exactly **1** realised value (all 0). The continuous metric takes values on a
continuum: IoU produces fractions whose denominator depends on predicted/truth
span lengths, and the proximity branch adds a length-normalised ramp. Because
the 30 functions differ in length and bug position and models emit differing
numbers of references, the value set cannot collapse to ≤3 levels.

Re-analysis of the same 300 frozen responses
(`python -m experiment.score_t2_continuous --reanalyze full_t2_confirmatory_v2`):

| Metric | n | distinct values | tied-pair fraction |
|---|---|---|---|
| binary location (frozen) | 300 | **1** | **1.0000** |
| continuous location (this) | 300 | **37** | **0.1422** |

Realised continuous distribution (rounded, top values):
`1.0×96, 0.5×44, 0.333×28, 0.25×18, 0.2×18, 0.143×11, 0.167×7, 0.4×7, …`
(37 distinct levels total). Tied-pair mass drops from 1.0 to 0.14 — the metric
provably does not repeat the ≤3-level saturation on this dataset.

## 4. Artifacts and guarantees

- New module: `src/experiment/score_t2_continuous.py` (does not import or mutate
  `score_t2.py` or `analyze_confirmatory.py`).
- Tests: `tests/test_score_t2_continuous.py` — exact→1.0, disjoint-far→0.0,
  overlap & proximity monotonicity, quoted-code recovery, unmappable→0.0 (15
  cases, all passing).
- Exploratory output (every filename/field labelled exploratory):
  `results/analysis/exploratory/t2_continuous_location_full_t2_confirmatory_v2/exploratory_location_continuous.json`.
- `git diff` confirms no change to any frozen scorer, dataset, or confirmatory
  analysis artifact.

## 5. Carry-forward

This metric is a candidate location sub-score for Constitution v0.3 (R3) and a
prerequisite input for the R1-5 rubric pilot. It is **not** to be pooled with or
substituted into the frozen confirmatory composite. Whether C4's apparent
advantage survives a continuous location metric is an R1/R5 question, not
settled here — this issue only establishes that the instrument de-saturates.
