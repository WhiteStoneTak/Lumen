"""Hidden/metamorphic layer for rotate_list T3 (rotate_list.TR01). EXPLORATORY (W-04).

Transform: rotate RIGHT by k (last k elements move to front). k taken modulo
len(items); copy returned when k%n == 0 or items empty.
"""

from __future__ import annotations


def reference(items: list, k: int) -> list:
    if not items:
        return []
    n = len(items)
    k = k % n
    if k == 0:
        return list(items)
    return items[-k:] + items[:-k]


HIDDEN_INPUTS = [
    [[1, 2, 3, 4, 5], 2],    # -> [4, 5, 1, 2, 3]
    [[1, 2, 3], 3],          # full rotation -> identity
    [[1, 2, 3], 0],          # no rotation
    [[], 5],                 # empty
    [[7], 100],              # single element
    [[1, 2, 3, 4], 1],       # -> [4, 1, 2, 3]
    [[1, 2, 3, 4, 5], -1],   # negative k (mod) -> [2, 3, 4, 5, 1]
    [[1, 2, 3, 4, 5], 7],    # k > n -> same as k=2
]


def _mr_length_preserved(fn) -> bool:
    for items, k in [([1, 2, 3, 4], 2), ([5], 3), ([], 1), ([1, 2, 3, 4, 5], -2)]:
        if len(fn(list(items), k)) != len(items):
            return False
    return True


def _mr_multiset_preserved(fn) -> bool:
    for items, k in [([1, 2, 3, 4], 2), ([4, 4, 1, 2], 3), ([9, 8, 7], -1)]:
        if sorted(fn(list(items), k)) != sorted(items):
            return False
    return True


def _mr_full_rotation_identity(fn) -> bool:
    for items in ([1, 2, 3, 4], [5, 6], [7]):
        if fn(list(items), len(items)) != list(items):
            return False
    return True


def _mr_zero_identity(fn) -> bool:
    for items in ([1, 2, 3], [], [4]):
        if fn(list(items), 0) != list(items):
            return False
    return True


def _mr_periodic_in_k(fn) -> bool:
    for items, k in [([1, 2, 3, 4], 1), ([1, 2, 3, 4, 5], 3)]:
        if fn(list(items), k) != fn(list(items), k + len(items)):
            return False
    return True


METAMORPHIC = [
    _mr_length_preserved,
    _mr_multiset_preserved,
    _mr_full_rotation_identity,
    _mr_zero_identity,
    _mr_periodic_in_k,
]
