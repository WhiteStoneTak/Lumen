"""Hidden/metamorphic layer for rle_encode T3 (rle_encode.TR01). EXPLORATORY (W-04).

Transform: output a FLAT interleaved list [v1, c1, v2, c2, ...] instead of a list
of (value, count) tuples. Run-detection logic unchanged. Empty -> [].
"""

from __future__ import annotations


def reference(items: list) -> list:
    if not items:
        return []
    out: list = []
    cur = items[0]
    cnt = 1
    for it in items[1:]:
        if it == cur:
            cnt += 1
        else:
            out.append(cur)
            out.append(cnt)
            cur = it
            cnt = 1
    out.append(cur)
    out.append(cnt)
    return out


HIDDEN_INPUTS = [
    [[1, 1, 2, 3, 3]],        # -> [1, 2, 2, 1, 3, 2]
    [[]],                     # -> []
    [[5]],                    # -> [5, 1]
    [["a", "a", "a"]],        # -> ['a', 3]
    [[1, 2, 1, 2]],           # alternating -> [1, 1, 2, 1, 1, 1, 2, 1]
    [[7, 7, 7, 7]],           # -> [7, 4]
    [[0, 0, 1, 1, 1, 0]],     # value re-appears -> [0, 2, 1, 3, 0, 1]
]


def _decode(flat: list) -> list:
    out: list = []
    for i in range(0, len(flat), 2):
        out.extend([flat[i]] * flat[i + 1])
    return out


def _mr_even_length(fn) -> bool:
    for items in ([1, 1, 2], [], [5], [1, 2, 1, 2]):
        if len(fn(list(items))) % 2 != 0:
            return False
    return True


def _mr_counts_sum_to_len(fn) -> bool:
    for items in ([1, 1, 2, 3, 3], [7, 7, 7], [], [1, 2, 3]):
        flat = fn(list(items))
        if sum(flat[1::2]) != len(items):
            return False
    return True


def _mr_values_no_adjacent_dup(fn) -> bool:
    for items in ([1, 1, 2, 2, 1], [5, 5, 5], [1, 2, 3]):
        vals = fn(list(items))[0::2]
        if any(vals[i] == vals[i + 1] for i in range(len(vals) - 1)):
            return False
    return True


def _mr_decode_roundtrip(fn) -> bool:
    for items in ([1, 1, 2, 3, 3], ["a", "a", "b"], [], [9]):
        flat = fn(list(items))
        if _decode(flat) != list(items):
            return False
    return True


def _mr_counts_positive(fn) -> bool:
    for items in ([1, 1, 2, 3, 3], [7], [1, 2, 1]):
        counts = fn(list(items))[1::2]
        if any((not isinstance(c, int)) or c < 1 for c in counts):
            return False
    return True


METAMORPHIC = [
    _mr_even_length,
    _mr_counts_sum_to_len,
    _mr_values_no_adjacent_dup,
    _mr_decode_roundtrip,
    _mr_counts_positive,
]
