from typing import Any

def frequency_table(values: list[Any]) -> list[tuple[Any, ...]]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Build a frequency table from a list of values

    Invariants:
    - None.
    """
    if not values:
        return []
    counts: dict = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    total = len(values)
    sorted_keys = sorted(counts.keys())
    result: list[tuple] = []
    cumulative = 0
    for key in sorted_keys:
        count = counts[key]
        cumulative += count
        cumulative_fraction = count / total
        result.append((key, count, cumulative_fraction))
    return result
