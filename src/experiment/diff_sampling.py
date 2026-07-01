"""Deterministic, type-driven input sampler for differential testing (EXPLORATORY).

Status: exploratory measurement-design instrument (backlog W-04). Shared by the
T2 semantic-equivalence metric (``score_t2_patch.py``) and the T3 hidden /
metamorphic layer (``score_t3_difficulty.py``). It is **not** part of the frozen
confirmatory pipeline and is never imported by a frozen scorer.

Purpose
-------
Given a function's parameter types (recovered from the frozen IR type layer,
``data/functions/ir/{func_id}.json`` → ``type_info.params[*].mypy_type``), produce
a *deterministic* battery of concrete argument tuples. Two implementations of the
same function (e.g. a model's patched source vs the reference-fixed source) are
then run against the identical battery and their outputs compared, yielding a
continuous behavioural-agreement rate.

Design choices
--------------
* **Determinism.** Every battery is seeded (``random.Random(seed)``) so a
  re-analysis is byte-reproducible. The edge-case prefix is fixed per type.
* **Honest non-applicability.** If *any* parameter type is unsupported (most
  importantly a callable parameter, e.g. ``top_k_by``'s ``key=``), the sampler
  returns ``None`` and the caller reports ``status="not_applicable"`` rather than
  silently scoring 0 — a not-applicable case must never manufacture fake
  saturation or fake signal (W-04 guardrail).
* **JSON-native values.** Sampled arguments use only ``int|float|str|bool|list``
  so they can be shipped to a subprocess differential driver as one JSON line.
  ``tuple`` element types are materialised as lists; the sampled functions accept
  sequence inputs, so this is behaviour-preserving for the metric's purpose.
"""

from __future__ import annotations

import random
from typing import Any

SCHEMA = "diff-sampling-v1"

# Alphabet for string sampling: letters + digits + a couple of separators, so a
# transform like camel_to_snake sees realistic mixed-case identifiers.
_STR_ALPHABET = "abcdeFGHIJklmnoPQRst01_ "


class UnsupportedTypeError(ValueError):
    """Raised internally when a mypy type has no concrete generator."""


# ---------------------------------------------------------------------------
# Per-type generators
# ---------------------------------------------------------------------------

def _gen_scalar(mypy_type: str, rng: random.Random) -> Any:
    if mypy_type == "builtins.int":
        return rng.randint(-25, 25)
    if mypy_type == "builtins.float":
        return round(rng.uniform(-25.0, 25.0), 3)
    if mypy_type == "builtins.bool":
        return rng.random() < 0.5
    if mypy_type == "builtins.str":
        n = rng.randint(0, 10)
        return "".join(rng.choice(_STR_ALPHABET) for _ in range(n))
    raise UnsupportedTypeError(mypy_type)


def _element_type(mypy_type: str) -> str:
    """Return the element type of a ``builtins.list[...]`` / ``tuple[...]`` string."""
    inner = mypy_type[mypy_type.index("[") + 1 : mypy_type.rindex("]")].strip()
    # tuple[X, ...] -> element type is X
    if inner.endswith(", ..."):
        inner = inner[: -len(", ...")].strip()
    return inner


def _gen_value(mypy_type: str, rng: random.Random) -> Any:
    """Generate one value of ``mypy_type``. Raises UnsupportedTypeError if unknown."""
    if mypy_type in ("builtins.int", "builtins.float", "builtins.bool", "builtins.str"):
        return _gen_scalar(mypy_type, rng)
    # ``Any`` defaults to a small int — the safest concrete inhabitant.
    if mypy_type == "Any":
        return rng.randint(-9, 9)
    if mypy_type.startswith("builtins.list[") or mypy_type.startswith("builtins.tuple["):
        elem = _element_type(mypy_type)
        length = rng.randint(0, 6)
        return [_gen_value(elem, rng) for _ in range(length)]
    raise UnsupportedTypeError(mypy_type)


# ---------------------------------------------------------------------------
# Edge-case prefix (fixed, per type) — cheap high-signal inputs
# ---------------------------------------------------------------------------

def _edge_values(mypy_type: str) -> list[Any]:
    if mypy_type == "builtins.int":
        return [0, 1, -1]
    if mypy_type == "builtins.float":
        return [0.0, 1.0, -1.0]
    if mypy_type == "builtins.bool":
        return [True, False]
    if mypy_type == "builtins.str":
        return ["", "a", "Ab_1"]
    if mypy_type == "Any":
        return [0, 1]
    if mypy_type.startswith("builtins.list[") or mypy_type.startswith("builtins.tuple["):
        elem = _element_type(mypy_type)
        single = _edge_values(elem)[:1] or [0]
        return [[], single]  # empty + singleton
    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_supported(param_types: list[str]) -> bool:
    """True iff every parameter type has a concrete generator."""
    rng = random.Random(0)
    for t in param_types:
        try:
            _gen_value(t, rng)
        except (UnsupportedTypeError, ValueError):
            return False
    return True


def sample_inputs(
    param_types: list[str],
    *,
    n_random: int = 40,
    seed: int = 20260630,
) -> list[list[Any]] | None:
    """Return a deterministic battery of argument lists, or ``None`` if unsupported.

    The battery is the cartesian-free *positional* zip: each entry is one full
    argument list (one value per parameter). It begins with a small fixed
    edge-case block (index-aligned across parameters), then ``n_random`` seeded
    random rows. Returns ``None`` if any parameter type is unsupported so the
    caller can mark the record ``not_applicable``.
    """
    if not param_types:
        # Zero-arg function: a single empty call is the only input.
        return [[]]
    if not is_supported(param_types):
        return None

    rows: list[list[Any]] = []

    # Edge block: align the fixed edge vectors by index, padding by cycling.
    edge_cols = [_edge_values(t) or [_gen_value(t, random.Random(1))] for t in param_types]
    edge_len = max(len(c) for c in edge_cols)
    for i in range(edge_len):
        rows.append([col[i % len(col)] for col in edge_cols])

    # Random block: one shared RNG advanced across all params for reproducibility.
    rng = random.Random(seed)
    for _ in range(n_random):
        rows.append([_gen_value(t, rng) for t in param_types])

    return rows
