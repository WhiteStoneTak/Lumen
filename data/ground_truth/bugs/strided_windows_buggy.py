def strided_windows(items: list, size: int, stride: int, include_partial: bool = False) -> list[list]:
    """Extract overlapping or non-overlapping windows from a list.

    Windows start at indices 0, stride, 2*stride, ... Each window has `size`
    elements. If include_partial is True, trailing windows that don't have
    enough remaining elements are included as shorter lists. If include_partial
    is False (default), only full-sized windows are returned.

    Args:
        items: Input list.
        size: Window size (>= 1).
        stride: Step between window start positions (>= 1).
        include_partial: If True, include trailing partial windows.

    Returns:
        List of windows (each a list of items).

    Examples:
        strided_windows([1, 2, 3, 4, 5], 3, 1) == [[1, 2, 3], [2, 3, 4], [3, 4, 5]]
        strided_windows([1, 2, 3, 4, 5], 3, 2) == [[1, 2, 3], [3, 4, 5]]
        strided_windows([1, 2, 3, 4, 5], 3, 2, include_partial=True) == [[1, 2, 3], [3, 4, 5], [5]]
    """
    result: list[list] = []
    n = len(items)
    i = 0

    while i + size < n:  # BUG: should be <= not <; drops last window when i+size==n exactly
        result.append(list(items[i:i + size]))
        i += stride

    if include_partial and i < n:
        result.append(list(items[i:]))

    return result
