def group_by_key(pairs: list[tuple]) -> dict:
    """Group a list of (key, value) pairs into a dict of value-lists.

    Keys maintain insertion order (Python 3.7+ dict ordering).
    Values within each key group preserve original relative order.

    Args:
        pairs: List of (key, value) tuples. Key must be hashable.

    Returns:
        Dict mapping each key to the list of values associated with it,
        in the order they appeared.

    Examples:
        group_by_key([("a", 1), ("b", 2), ("a", 3), ("c", 1), ("b", 4)]) == {"a": [1, 3], "b": [2, 4], "c": [1]}
        group_by_key([]) == {}
        group_by_key([("x", 10)]) == {"x": [10]}
    """
    result: dict = {}

    for key, value in pairs:
        if key not in result:
            result[key] = []
        result[key].append(key)

    return result
