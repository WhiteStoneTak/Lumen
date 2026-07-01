"""Hidden/metamorphic layer for merge_intervals T3 (merge_intervals.TR01). EXPLORATORY (W-04).

Transform: return the total number of integer points covered by at least one
interval (a single int), instead of the merged interval list. Empty -> 0.
"""

from __future__ import annotations


def reference(intervals: list[list[int]]) -> int:
    if not intervals:
        return 0
    ivs = sorted((iv[0], iv[1]) for iv in intervals)
    total = 0
    cur_lo, cur_hi = ivs[0]
    for lo, hi in ivs[1:]:
        if lo <= cur_hi:            # overlapping or touching at a shared point
            cur_hi = max(cur_hi, hi)
        else:
            total += cur_hi - cur_lo + 1
            cur_lo, cur_hi = lo, hi
    total += cur_hi - cur_lo + 1
    return total


HIDDEN_INPUTS = [
    [[[1, 3], [2, 6], [8, 10]]],   # -> 9
    [[[1, 2], [2, 4]]],            # touching -> 4
    [[]],                          # -> 0
    [[[5, 5]]],                    # single point -> 1
    [[[1, 10], [2, 3]]],           # nested -> 10
    [[[1, 2], [4, 5], [7, 8]]],    # disjoint -> 6
    [[[1, 5], [1, 5]]],            # duplicate -> 5
    [[[-3, -1], [0, 2]]],          # negative + disjoint -> 6
]


def _mr_nonneg_int(fn) -> bool:
    for arg in ([[1, 3], [2, 6]], [], [[0, 0]], [[-2, 2]]):
        r = fn([list(x) for x in arg])
        if not isinstance(r, int) or isinstance(r, bool) or r < 0:
            return False
    return True


def _mr_ge_max_single(fn) -> bool:
    for arg in ([[1, 3], [10, 12]], [[0, 9]], [[2, 2], [5, 8]]):
        longest = max(hi - lo + 1 for lo, hi in arg)
        if fn([list(x) for x in arg]) < longest:
            return False
    return True


def _mr_le_sum_of_lengths(fn) -> bool:
    for arg in ([[1, 3], [2, 6], [8, 10]], [[1, 5], [1, 5]], [[0, 0], [1, 1]]):
        s = sum(hi - lo + 1 for lo, hi in arg)
        if fn([list(x) for x in arg]) > s:
            return False
    return True


def _mr_monotone_add(fn) -> bool:
    base = [[1, 3], [10, 12]]
    extra = base + [[20, 25]]
    if fn([list(x) for x in extra]) < fn([list(x) for x in base]):
        return False
    return True


def _mr_single_interval_length(fn) -> bool:
    for lo, hi in [(1, 5), (0, 0), (-3, 2)]:
        if fn([[lo, hi]]) != hi - lo + 1:
            return False
    return fn([]) == 0


METAMORPHIC = [
    _mr_nonneg_int,
    _mr_ge_max_single,
    _mr_le_sum_of_lengths,
    _mr_monotone_add,
    _mr_single_interval_length,
]
