"""Canonical T1 (program-understanding) scorer entrypoint.

T1 is scored as the fraction of ground-truth checklist properties
(``data/ground_truth/checklists/{func_id}.json``) that a model response
correctly states:

    score = matched_properties / total_properties  ∈ [0, 1]

The implementation lives in :mod:`experiment.score_t1_checklist` (a
protocol-first, deterministic keyword/negation matcher — no LLM judge). This
module is the stable, protocol-named public entrypoint required by the
measurement-design pass (Linear R1-3 / WOV-237); it re-exports that API rather
than duplicating the logic, so there is exactly one source of truth.

The full, reproducible scoring specification and the anti-ceiling analysis are
in ``docs/t1-scoring-spec.md``.
"""

from __future__ import annotations

from experiment.score_t1_checklist import (
    load_t1_scoring_context,
    normalize_t1_response,
    score_t1_checklist,
    score_t1_property,
)

#: Canonical scoring entrypoint. See :func:`score_t1_checklist`.
score_t1 = score_t1_checklist

__all__ = [
    "score_t1",
    "score_t1_checklist",
    "score_t1_property",
    "normalize_t1_response",
    "load_t1_scoring_context",
]
