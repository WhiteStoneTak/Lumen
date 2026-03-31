def rle_encode(items: list) -> list:
    """Return the run-length encoding of items as a list of (value, count) pairs.

    Consecutive equal values are collapsed into a single (value, count) tuple.
    Non-consecutive duplicates produce separate tuples.
    Order is preserved.  Returns an empty list for empty input.

    Examples:
        rle_encode([1, 1, 2, 3, 3]) == [(1, 2), (2, 1), (3, 2)]
        rle_encode(['a', 'a', 'a']) == [('a', 3)]
        rle_encode([])              == []
    """
    if not items:
        return []
    result = []
    current = items[0]
    count = 1
    for item in items[1:]:
        if item == current:
            count += 1
        else:
            result.append((current, count))
            current = items[-1]  # BUG: should be `item`
            count = 1
    result.append((current, count))
    return result
