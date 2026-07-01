"""Hidden/metamorphic layer for strided_windows T3 (strided_windows.TR01). EXPLORATORY (W-04).

Transform: return the windows in REVERSE order (last window first). Window
contents unchanged. Empty / no-window input -> [].
"""

from __future__ import annotations


def reference(items: list, size: int, stride: int, include_partial: bool = False) -> list:
    result: list = []
    n = len(items)
    i = 0
    while i + size <= n:
        result.append(list(items[i:i + size]))
        i += stride
    if include_partial and i < n:
        result.append(list(items[i:]))
    return result[::-1]


HIDDEN_INPUTS = [
    [[1, 2, 3, 4, 5], 3, 1],            # -> [[3,4,5],[2,3,4],[1,2,3]]
    [[1, 2, 3, 4, 5], 3, 2],            # -> [[3,4,5],[1,2,3]]
    [[1, 2, 3, 4, 5], 3, 2, True],      # partial -> [[5],[3,4,5],[1,2,3]]
    [[], 3, 1],                         # -> []
    [[1, 2], 3, 1],                     # window larger than input -> []
    [[1, 2, 3, 4, 5, 6], 2, 2],         # -> [[5,6],[3,4],[1,2]]
    [[7, 8, 9], 1, 1],                  # -> [[9],[8],[7]]
    [[1, 2, 3, 4], 2, 3],               # -> [[4? no]] full windows only: [[1,2]] -> [[1,2]]
]


def _n_full_windows(n: int, size: int, stride: int) -> int:
    if n < size:
        return 0
    return (n - size) // stride + 1


def _mr_full_windows_have_size(fn) -> bool:
    for items, size, stride in [([1, 2, 3, 4, 5], 3, 1), ([1, 2, 3, 4, 5, 6], 2, 2)]:
        for w in fn(list(items), size, stride):
            if len(w) != size:
                return False
    return True


def _mr_count_matches_formula(fn) -> bool:
    for items, size, stride in [([1, 2, 3, 4, 5], 3, 1), ([1, 2, 3, 4, 5], 3, 2),
                                ([1, 2], 3, 1), ([7, 8, 9], 1, 1)]:
        if len(fn(list(items), size, stride)) != _n_full_windows(len(items), size, stride):
            return False
    return True


def _mr_last_element_is_first_forward_window(fn) -> bool:
    # Reversed order => the last item of the result is the FIRST forward window.
    for items, size, stride in [([1, 2, 3, 4, 5], 3, 1), ([1, 2, 3, 4, 5, 6], 2, 2)]:
        res = fn(list(items), size, stride)
        if res and res[-1] != list(items[:size]):
            return False
    return True


def _mr_empty_when_too_short(fn) -> bool:
    return fn([], 3, 1) == [] and fn([1, 2], 3, 1) == []


METAMORPHIC = [
    _mr_full_windows_have_size,
    _mr_count_matches_formula,
    _mr_last_element_is_first_forward_window,
    _mr_empty_when_too_short,
]
