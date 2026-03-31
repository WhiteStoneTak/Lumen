def remove_adjacent_dups(items: list) -> list:
    """Return a copy of items with adjacent duplicate values collapsed.

    Consecutive equal values are reduced to a single occurrence.
    Non-adjacent duplicates are preserved.  Order is maintained.
    An empty list is returned unchanged.

    Examples:
        remove_adjacent_dups([1, 1, 2, 3, 3, 3, 2]) == [1, 2, 3, 2]
        remove_adjacent_dups([])                     == []
        remove_adjacent_dups([7])                    == [7]
    """
    if not items:
        return []
    result = [items[0]]
    for item in items[1:]:
        if item != result[-1]:
            result.append(item)
    return result
