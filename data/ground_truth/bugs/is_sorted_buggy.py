def is_sorted(items: list) -> bool:
    """Return True if items is in non-decreasing order, False otherwise.

    Returns True for empty and single-element lists.
    """
    for i in range(len(items) - 1):
        if items[i] >= items[i + 1]:
            return False
    return True
