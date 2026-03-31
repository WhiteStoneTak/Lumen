def group_and_aggregate(pairs: list[tuple]) -> dict:
    """Group (key, value) pairs and compute per-group statistics.

    For each unique key, compute: count, sum, min, and max of associated values.

    Args:
        pairs: List of (key, value) tuples. Key must be hashable. Value is numeric.

    Returns:
        Dict mapping each key to a dict with keys:
        "count" (int), "sum" (float), "min" (float), "max" (float).
        Keys appear in insertion order.

    Examples:
        group_and_aggregate([("a", 3), ("b", 1), ("a", 7)]) == {"a": {"count": 2, "sum": 10, "min": 3, "max": 7}, "b": {"count": 1, "sum": 1, "min": 1, "max": 1}}
        group_and_aggregate([]) == {}
        group_and_aggregate([("x", 5), ("x", 5)]) == {"x": {"count": 2, "sum": 10, "min": 5, "max": 5}}
    """
    result: dict = {}

    for key, value in pairs:
        if key not in result:
            result[key] = {
                "count": 1,
                "sum": value,
                "min": value,
                "max": value,
            }
        else:
            entry = result[key]
            entry["count"] += 1
            entry["sum"] += value
            if value < entry["min"]:
                entry["min"] = value
            if value > entry["max"]:
                entry["max"] = value

    return result
