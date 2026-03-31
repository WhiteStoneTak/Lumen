def first_index_of_max(nums: list) -> int:
    """Return the index of the first occurrence of the maximum value in nums.

    When the maximum value appears multiple times, the lowest index is returned.
    Raises ValueError for an empty list.

    Examples:
        first_index_of_max([3, 1, 4, 1, 5, 9, 2, 6]) == 5
        first_index_of_max([5, 5, 5])                 == 0
        first_index_of_max([1, 2, 3])                 == 2
    """
    if not nums:
        raise ValueError("first_index_of_max requires a non-empty list")
    max_val = nums[0]
    max_idx = 0
    for i in range(1, len(nums)):
        if nums[i] > max_val:
            max_val = nums[i]
            max_idx = i
    return max_idx
