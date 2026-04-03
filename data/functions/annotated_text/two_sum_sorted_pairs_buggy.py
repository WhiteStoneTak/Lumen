def two_sum_sorted_pairs(nums: list[int], target: int) -> list[tuple[int, int]]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Return all unique pairs (a, b) from a sorted list where a + b == target

    Invariants:
    - None.
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
        elif s < target:
            left += 1
        else:
            right -= 1
    return result
