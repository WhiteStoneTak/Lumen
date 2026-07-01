"""Hidden/metamorphic layer for is_sorted T3 (is_sorted.TR01). EXPLORATORY (W-04).

Transform: require STRICTLY ascending order (equal adjacent -> False). Empty and
single-element lists still return True.
"""

from __future__ import annotations


def reference(items: list) -> bool:
    for i in range(len(items) - 1):
        if items[i] >= items[i + 1]:
            return False
    return True


HIDDEN_INPUTS = [
    [[1, 2, 3]],          # strictly asc -> True
    [[1, 1, 2]],          # equal adjacent -> False
    [[3, 2, 1]],          # descending -> False
    [[]],                 # empty -> True
    [[5]],                # single -> True
    [[1, 2, 2, 3]],       # interior duplicate -> False
    [[-2, -1, 0, 1]],     # negatives strictly asc -> True
    [[1, 3, 2, 4]],       # dip -> False
    [[0, 0]],             # two equal -> False
]


def _mr_empty_and_single_true(fn) -> bool:
    return fn([]) is True and fn([7]) is True and fn([-1]) is True


def _mr_strict_increasing_true(fn) -> bool:
    return fn([1, 2, 3, 4, 5]) is True and fn([-3, 0, 10]) is True


def _mr_adjacent_dup_false(fn) -> bool:
    return fn([1, 2, 2, 3]) is False and fn([5, 5]) is False


def _mr_reverse_of_increasing_false(fn) -> bool:
    for base in ([1, 2, 3], [1, 2, 3, 4, 5], [-1, 0, 2]):
        if fn(list(reversed(base))) is not False:
            return False
    return True


def _mr_returns_bool(fn) -> bool:
    return isinstance(fn([1, 2, 3]), bool) and isinstance(fn([3, 2, 1]), bool)


METAMORPHIC = [
    _mr_empty_and_single_true,
    _mr_strict_increasing_true,
    _mr_adjacent_dup_false,
    _mr_reverse_of_increasing_false,
    _mr_returns_bool,
]
