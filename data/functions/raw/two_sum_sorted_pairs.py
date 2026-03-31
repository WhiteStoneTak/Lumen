def two_sum_sorted_pairs(nums: list[int], target: int) -> list[tuple[int, int]]:
    """Return all unique pairs (a, b) from a sorted list where a + b == target.

    Uses a two-pointer approach. Each value may appear multiple times; unique
    (value, value) pairs are returned without duplication. Pairs are returned
    in ascending order of the first element.

    Args:
        nums: Sorted list of integers (non-decreasing).
        target: Target sum.

    Returns:
        List of (a, b) tuples with a <= b and a + b == target, no duplicates.

    Examples:
        two_sum_sorted_pairs([1, 2, 3, 4, 6], 6) == [(2, 4)]
        two_sum_sorted_pairs([1, 1, 2, 3, 4, 4, 5], 5) == [(1, 4), (2, 3)]
        two_sum_sorted_pairs([1, 2, 3], 10) == []
    """
    result: list[tuple[int, int]] = []
    left = 0
    right = len(nums) - 1

    while left < right:
        s = nums[left] + nums[right]
        if s == target:
            result.append((nums[left], nums[right]))
            left_val = nums[left]
            right_val = nums[right]
            while left < right and nums[left] == left_val:
                left += 1
            while left < right and nums[right] == right_val:
                right -= 1
        elif s < target:
            left += 1
        else:
            right -= 1

    return result
