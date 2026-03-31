def segments_above_threshold(nums: list[float], threshold: float) -> list[list[float]]:
    """Return all maximal contiguous sublists where every element is
    strictly greater than threshold.

    Args:
        nums: List of floats.
        threshold: The threshold value (exclusive lower bound).

    Returns:
        List of sublists, each being a maximal contiguous run of values
        strictly greater than threshold. Empty if no such elements exist.

    Examples:
        segments_above_threshold([1, 5, 6, 2, 8, 9, 3], 4) == [[5, 6], [8, 9]]
        segments_above_threshold([1, 2, 3], 5) == []
        segments_above_threshold([6, 6, 6], 5) == [[6, 6, 6]]
    """
    result: list[list[float]] = []
    current_segment: list[float] = []

    for val in nums:
        if val > threshold:
            current_segment.append(val)
        else:
            if current_segment:
                result.append(current_segment)
                current_segment = []

    if current_segment:
        result.append(current_segment)

    return result
