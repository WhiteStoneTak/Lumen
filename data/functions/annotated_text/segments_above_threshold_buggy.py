def segments_above_threshold(nums: list[float], threshold: float) -> list[list[float]]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Return all maximal contiguous sublists where every element is strictly greater than threshold

    Invariants:
    - None.
    """
    result: list[list[float]] = []
    current_segment: list[float] = []
    for val in nums:
        if val >= threshold:
            current_segment.append(val)
        elif current_segment:
            result.append(current_segment)
            current_segment = []
    if current_segment:
        result.append(current_segment)
    return result
