"""Hidden/metamorphic layer for group_and_aggregate T3 (group_and_aggregate.TR01). EXPLORATORY (W-04).

Transform: per group return {count, mean, range} where mean = sum/count (float)
and range = max - min. The keys 'sum', 'min', 'max' must NOT appear. Keys in
insertion order. Empty -> {}.
"""

from __future__ import annotations


def reference(pairs: list) -> dict:
    acc: dict = {}
    for key, value in pairs:
        if key not in acc:
            acc[key] = {"count": 1, "_sum": value, "_min": value, "_max": value}
        else:
            e = acc[key]
            e["count"] += 1
            e["_sum"] += value
            if value < e["_min"]:
                e["_min"] = value
            if value > e["_max"]:
                e["_max"] = value
    out: dict = {}
    for key, e in acc.items():
        out[key] = {
            "count": e["count"],
            "mean": e["_sum"] / e["count"],
            "range": e["_max"] - e["_min"],
        }
    return out


HIDDEN_INPUTS = [
    [[("a", 3), ("b", 1), ("a", 7)]],   # a:{2,5.0,4}, b:{1,1.0,0}
    [[]],                               # {}
    [[("x", 5), ("x", 5)]],             # {2, 5.0, 0}
    [[("a", 1), ("a", 2), ("a", 3)]],   # {3, 2.0, 2}
    [[("k", -2), ("k", 4)]],            # {2, 1.0, 6}
    [[("p", 10)]],                      # {1, 10.0, 0}
    [[("a", 1), ("b", 2), ("c", 3)]],   # three singleton groups
]

_ALLOWED_KEYS = {"count", "mean", "range"}


def _mr_only_allowed_keys(fn) -> bool:
    for pairs in [[("a", 3), ("b", 1), ("a", 7)], [("x", 5), ("x", 5)], [("p", 10)]]:
        for entry in fn(list(pairs)).values():
            if set(entry.keys()) != _ALLOWED_KEYS:
                return False
    return True


def _mr_counts_sum_to_len(fn) -> bool:
    for pairs in [[("a", 3), ("b", 1), ("a", 7)], [("a", 1), ("a", 2), ("a", 3)], []]:
        out = fn(list(pairs))
        if sum(e["count"] for e in out.values()) != len(pairs):
            return False
    return True


def _mr_insertion_order(fn) -> bool:
    pairs = [("c", 1), ("a", 2), ("b", 3), ("a", 4)]
    if list(fn(list(pairs)).keys()) != ["c", "a", "b"]:
        return False
    return True


def _mr_singleton_range_zero(fn) -> bool:
    for pairs in [[("p", 10)], [("x", -3)], [("z", 0)]]:
        out = fn(list(pairs))
        key = pairs[0][0]
        e = out[key]
        if e["range"] != 0 or e["mean"] != pairs[0][1]:
            return False
    return True


def _mr_mean_within_group_bounds(fn) -> bool:
    import collections

    for pairs in [[("a", 3), ("b", 1), ("a", 7)], [("k", -2), ("k", 4)],
                  [("a", 1), ("a", 2), ("a", 3)]]:
        groups: dict = collections.defaultdict(list)
        for k, v in pairs:
            groups[k].append(v)
        out = fn(list(pairs))
        for k, vals in groups.items():
            m = out[k]["mean"]
            if not (min(vals) <= m <= max(vals)):
                return False
    return True


METAMORPHIC = [
    _mr_only_allowed_keys,
    _mr_counts_sum_to_len,
    _mr_insertion_order,
    _mr_singleton_range_zero,
    _mr_mean_within_group_bounds,
]
