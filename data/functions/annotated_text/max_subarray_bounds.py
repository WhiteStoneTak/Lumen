def max_subarray_bounds(nums: list[int]) -> tuple[int, int, int]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Return the (start, end, total) of the maximum-sum contiguous subarray

    Invariants:
    - None.
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
        if cur_sum > best_sum:
            best_sum = cur_sum
            best_start = cur_start
            best_end = i
    return (best_start, best_end, best_sum)
