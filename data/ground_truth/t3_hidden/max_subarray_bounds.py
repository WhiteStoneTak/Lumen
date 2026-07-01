"""Hidden/metamorphic layer for max_subarray_bounds T3 (max_subarray_bounds.TR01). EXPLORATORY (W-04).

Transform: return a LIST of ALL (start, end, total) subarrays whose sum equals
the global maximum sum, sorted by ascending start index. Empty -> []. All-negative
-> single-element subarrays at the max value.
"""

from __future__ import annotations


def reference(nums: list[int]) -> list[tuple[int, int, int]]:
    if not nums:
        return []
    n = len(nums)
    best: int | None = None
    results: list[tuple[int, int, int]] = []
    for i in range(n):
        s = 0
        for j in range(i, n):
            s += nums[j]
            if best is None or s > best:
                best = s
                results = [(i, j, s)]
            elif s == best:
                results.append((i, j, s))
    results.sort(key=lambda t: t[0])
    return results


HIDDEN_INPUTS = [
    [[-2, 1, -3, 4, -1, 2, 1, -5, 4]],   # -> [(3, 6, 6)]
    [[1]],                               # -> [(0, 0, 1)]
    [[-3, -1, -2]],                      # all negative -> [(1, 1, -1)]
    [[]],                                # -> []
    [[1, -1, 1]],                        # ties -> [(0,0,1),(0,2,1),(2,2,1)]
    [[2, 2]],                            # -> [(0, 1, 4)]
    [[-1, -1]],                          # negative ties -> [(0,0,-1),(1,1,-1)]
    [[5, -2, 5]],                        # -> [(0, 2, 8)]
]


def _global_max_sum(nums: list[int]) -> int:
    best = nums[0]
    for i in range(len(nums)):
        s = 0
        for j in range(i, len(nums)):
            s += nums[j]
            if s > best:
                best = s
    return best


def _mr_valid_tuples(fn) -> bool:
    for nums in [[-2, 1, -3, 4, -1, 2, 1, -5, 4], [1, -1, 1], [5, -2, 5], [3]]:
        for (s, e, t) in fn(list(nums)):
            if not (0 <= s <= e < len(nums)):
                return False
            if sum(nums[s:e + 1]) != t:
                return False
    return True


def _mr_all_same_total(fn) -> bool:
    for nums in [[1, -1, 1], [-1, -1], [2, 2], [4, -1, 4]]:
        totals = {t for (_, _, t) in fn(list(nums))}
        if len(totals) > 1:
            return False
    return True


def _mr_total_is_global_max(fn) -> bool:
    for nums in [[-2, 1, -3, 4, -1, 2, 1, -5, 4], [1, -1, 1], [-3, -1, -2], [5, -2, 5]]:
        res = fn(list(nums))
        if not res:
            return False
        gm = _global_max_sum(nums)
        if any(t != gm for (_, _, t) in res):
            return False
    return True


def _mr_sorted_by_start(fn) -> bool:
    for nums in [[1, -1, 1], [-1, -1, -1], [2, 2, 2]]:
        starts = [s for (s, _, _) in fn(list(nums))]
        if starts != sorted(starts):
            return False
    return True


def _mr_empty_empty(fn) -> bool:
    return fn([]) == []


METAMORPHIC = [
    _mr_valid_tuples,
    _mr_all_same_total,
    _mr_total_is_global_max,
    _mr_sorted_by_start,
    _mr_empty_empty,
]
