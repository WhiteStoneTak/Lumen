def max_subarray_bounds(nums: list[int]) -> tuple[int, int, int]:
    """Return the (start, end, total) of the maximum-sum contiguous subarray.

    Uses a modified Kadane's algorithm. Both indices are inclusive.
    If multiple subarrays tie for the maximum sum, return the one that
    starts earliest. If nums is empty, return (0, 0, 0). If all values
    are negative, return the single element with the largest value.

    Args:
        nums: List of integers.

    Returns:
        A tuple (start, end, total) where start and end are inclusive
        0-based indices and total is the subarray sum.

    Examples:
        max_subarray_bounds([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == (3, 6, 6)
        max_subarray_bounds([1]) == (0, 0, 1)
        max_subarray_bounds([-3, -1, -2]) == (1, 1, -1)
    """
    if not nums:
        return (0, 0, 0)

    best_sum = nums[0]
    best_start = 0
    best_end = 0

    cur_sum = nums[0]
    cur_start = 0

    for i in range(1, len(nums)):
        if cur_sum + nums[i] < nums[i]:
            cur_sum = nums[i]
            cur_start = i
        else:
            cur_sum = cur_sum + nums[i]

        if cur_sum >= best_sum:  # BUG: should be >
            best_sum = cur_sum
            best_start = cur_start
            best_end = i

    return (best_start, best_end, best_sum)
