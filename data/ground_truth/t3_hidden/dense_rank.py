"""Hidden/metamorphic layer for dense_rank T3 (dense_rank.TR01). EXPLORATORY (W-04).

Transform: standard competition rank ('1224'), DESCENDING (highest value = rank
1). Tied items all get the lowest rank in their group; the next rank skips by the
size of the tie group. 1-based integer ranks, returned in input order. [] -> [].
"""

from __future__ import annotations


def reference(values: list) -> list:
    if not values:
        return []
    order = sorted(values, reverse=True)   # highest first
    rank_map: dict = {}
    for i, v in enumerate(order):
        if v not in rank_map:
            rank_map[v] = i + 1            # 1-based position of first occurrence
    return [rank_map[v] for v in values]


HIDDEN_INPUTS = [
    [[100, 90, 90, 80]],          # -> [1, 2, 2, 4]
    [[5, 5, 5, 1]],               # -> [1, 1, 1, 4]
    [[]],                         # -> []
    [[3.0, 1.0, 4.0, 1.0, 5.0]],  # -> [3, 4, 2, 4, 1]
    [[7]],                        # -> [1]
    [[2, 2, 2]],                  # -> [1, 1, 1]
    [[1, 2, 3, 4]],               # -> [4, 3, 2, 1]
    [[10, 10, 5, 5, 1]],          # -> [1, 1, 3, 3, 5]
]


def _mr_length_preserved(fn) -> bool:
    for vals in ([100, 90, 90, 80], [5], [], [3, 1, 4, 1, 5]):
        if len(fn(list(vals))) != len(vals):
            return False
    return True


def _mr_ranks_in_range(fn) -> bool:
    for vals in ([100, 90, 90, 80], [5, 5, 5, 1], [7], [1, 2, 3, 4]):
        n = len(vals)
        ranks = fn(list(vals))
        if any((not isinstance(r, int)) or r < 1 or r > n for r in ranks):
            return False
    return True


def _mr_min_rank_is_one(fn) -> bool:
    for vals in ([100, 90, 90, 80], [5, 5, 5, 1], [7], [1, 2, 3, 4]):
        if min(fn(list(vals))) != 1:
            return False
    return True


def _mr_equal_values_equal_ranks(fn) -> bool:
    for vals in ([5, 5, 5, 1], [10, 10, 5, 5, 1], [3, 1, 4, 1, 5]):
        ranks = fn(list(vals))
        seen: dict = {}
        for v, r in zip(vals, ranks):
            if v in seen and seen[v] != r:
                return False
            seen[v] = r
    return True


def _mr_descending_consistency(fn) -> bool:
    # Higher value must get a strictly smaller rank number (descending order).
    for vals in ([100, 90, 90, 80], [10, 10, 5, 5, 1], [1, 2, 3, 4]):
        ranks = fn(list(vals))
        for i in range(len(vals)):
            for j in range(len(vals)):
                if vals[i] > vals[j] and not (ranks[i] < ranks[j]):
                    return False
    return True


def _mr_max_gets_rank_one_count(fn) -> bool:
    for vals in ([100, 90, 90, 80], [5, 5, 5, 1], [10, 10, 5, 5, 1]):
        ranks = fn(list(vals))
        mx = max(vals)
        n_max = sum(1 for v in vals if v == mx)
        n_rank1 = sum(1 for r in ranks if r == 1)
        if n_rank1 != n_max:
            return False
    return True


METAMORPHIC = [
    _mr_length_preserved,
    _mr_ranks_in_range,
    _mr_min_rank_is_one,
    _mr_equal_values_equal_ranks,
    _mr_descending_consistency,
    _mr_max_gets_rank_one_count,
]
