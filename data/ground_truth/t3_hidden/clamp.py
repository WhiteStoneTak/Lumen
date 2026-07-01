"""Hidden/metamorphic layer for clamp T3 transform (clamp.TR01). EXPLORATORY (W-04).

Transform: enforce precondition lo <= hi by raising ValueError when lo > hi;
clamping to [lo, hi] otherwise unchanged.
"""

from __future__ import annotations


def reference(value: float, lo: float, hi: float) -> float:
    if lo > hi:
        raise ValueError("lo must be <= hi")
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


# Held-out adversarial inputs (differential-tested vs reference).
HIDDEN_INPUTS = [
    [5.0, 10.0, 1.0],      # lo > hi  -> ValueError
    [0.0, 100.0, -100.0],  # lo > hi  -> ValueError
    [1.001, 1.0, 1.0],     # value > hi at a zero-width interval
    [7.0, 5.0, 10.0],      # in range
    [15.0, 5.0, 10.0],     # above hi
    [-9.0, -5.0, -2.0],    # below lo, negative range
    [5.0, 5.0, 5.0],       # zero-width interval, in range
    [-100.0, 0.0, 0.0],    # below lo at zero-width
]


def _mr_within_bounds(fn) -> bool:
    for v, lo, hi in [(7.0, 5.0, 10.0), (-3.0, -5.0, -2.0), (0.0, 0.0, 10.0), (99.0, 1.0, 2.0)]:
        r = fn(v, lo, hi)
        if not (lo <= r <= hi):
            return False
    return True


def _mr_idempotent(fn) -> bool:
    for v, lo, hi in [(7.0, 5.0, 10.0), (15.0, 5.0, 10.0), (-9.0, -5.0, -2.0)]:
        once = fn(v, lo, hi)
        if fn(once, lo, hi) != once:
            return False
    return True


def _mr_identity_in_range(fn) -> bool:
    for v, lo, hi in [(7.0, 5.0, 10.0), (5.0, 5.0, 10.0), (10.0, 5.0, 10.0)]:
        if fn(v, lo, hi) != v:
            return False
    return True


def _mr_raises_on_bad_bounds(fn) -> bool:
    for v, lo, hi in [(5.0, 10.0, 1.0), (0.0, 100.0, -100.0)]:
        try:
            fn(v, lo, hi)
            return False  # should have raised
        except ValueError:
            continue
        except Exception:
            return False
    return True


METAMORPHIC = [
    _mr_within_bounds,
    _mr_idempotent,
    _mr_identity_in_range,
    _mr_raises_on_bad_bounds,
]
