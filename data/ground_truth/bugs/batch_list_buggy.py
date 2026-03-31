def batch_list(items: list, batch_size: int) -> list:
    """Split items into consecutive non-overlapping batches.

    Each batch contains at most batch_size elements.
    The final batch may be smaller if len(items) is not divisible by batch_size.
    Returns an empty list when items is empty or batch_size is less than 1.

    Examples:
        batch_list([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
        batch_list([1, 2, 3, 4, 5], 5) == [[1, 2, 3, 4, 5]]
        batch_list([], 3)               == []
    """
    if not items or batch_size < 1:
        return []
    result = []
    for i in range(0, len(items), batch_size + 1):  # BUG: should be batch_size
        result.append(items[i : i + batch_size])
    return result
