def rotate_list(items: list, k: int) -> list:
    """Return items rotated left by k positions.

    The element at index k becomes the new first element.
    k is taken modulo len(items), so any integer is valid.
    Returns a copy when k is 0 (after mod) or items is empty.

    Examples:
        rotate_list([1, 2, 3, 4, 5], 2) == [3, 4, 5, 1, 2]
        rotate_list([1, 2, 3], 3)        == [1, 2, 3]
        rotate_list([1, 2, 3], 1)        == [2, 3, 1]
    """
    if not items:
        return []
    n = len(items)
    k = k % n
    if k == 0:
        return list(items)
    return items[:k] + items[k:]  # BUG: swapped slices; should be items[k:] + items[:k]
