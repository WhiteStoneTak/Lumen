def sliding_window_max(nums: list, k: int) -> list:
    """Return the maximum value in each sliding window of k consecutive elements.

    The window slides one position at a time from left to right.
    The result contains len(nums) - k + 1 values.
    Returns an empty list when nums is empty, k < 1, or k > len(nums).

    Examples:
        sliding_window_max([1, 3, 2, 4, 1], 3) == [3, 4, 4]
        sliding_window_max([5, 5, 5], 2)        == [5, 5]
        sliding_window_max([7], 1)              == [7]
    """
    if not nums or k < 1 or k > len(nums):
        return []
    result = []
    for i in range(len(nums) - k + 1):
        result.append(max(nums[i : i + k]))
    return result
