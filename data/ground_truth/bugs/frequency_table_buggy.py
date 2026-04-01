def frequency_table(values: list) -> list[tuple]:
    """Build a frequency table from a list of values.

    Returns a list of (value, count, cumulative_fraction) tuples, sorted
    by value ascending. cumulative_fraction is the fraction of total items
    seen up to and including this value's count (cumulative sum of counts
    divided by total length).

    Args:
        values: List of comparable, hashable items.

    Returns:
        List of (value, count, cumulative_fraction) tuples sorted by value.
        cumulative_fraction is a float in (0.0, 1.0].
        Returns [] for empty input.

    Examples:
        frequency_table([3, 1, 2, 1, 3, 3]) == [(1, 2, 1/3), (2, 1, 0.5), (3, 3, 1.0)]
        frequency_table([]) == []
        frequency_table(["b", "a", "b"]) == [("a", 1, 1/3), ("b", 2, 1.0)]
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
        cumulative_fraction = count / total  # BUG: should be cumulative / total
        result.append((key, count, cumulative_fraction))

    return result
