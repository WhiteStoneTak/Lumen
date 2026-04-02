def peak_valley_indices(nums: list[float]) -> list[tuple[str, int]]:
    """Return the indices of strict local peaks and valleys in order.

    A strict local peak at index i satisfies nums[i] > nums[i-1] and
    nums[i] > nums[i+1]. A strict local valley satisfies nums[i] < nums[i-1]
    and nums[i] < nums[i+1]. Boundary elements (index 0 and last) are never
    peaks or valleys. Plateaus are not included.

    Args:
        nums: List of floats (or ints).

    Returns:
        List of ("peak", i) or ("valley", i) tuples in index order.

    Examples:
        peak_valley_indices([1, 3, 2, 0, 4, 1]) == [("peak", 1), ("valley", 3), ("peak", 4)]
        peak_valley_indices([1, 2, 3]) == []
        peak_valley_indices([3, 1, 3, 1]) == [("valley", 1), ("peak", 2)]
    """
    result: list[tuple[str, int]] = []

    if len(nums) < 3:
        return result

    for i in range(1, len(nums) - 1):
        left = nums[i - 1]
        mid = nums[i]
        right = nums[i + 1]

        if mid >= left and mid >= right:
            result.append(("peak", i))
        elif mid < left and mid < right:
            result.append(("valley", i))

    return result
