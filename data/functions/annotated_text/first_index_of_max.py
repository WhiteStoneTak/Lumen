from typing import Any

def first_index_of_max(nums: list[Any]) -> int:
    """
    Preconditions:
    - nums is non-empty

    Postconditions:
    - The return value is a valid index into nums (0 <= return value < len(nums))
    - nums[return value] equals the maximum element of nums
    - There is no index i < return value such that nums[i] equals the maximum element
    - The return value is 0 when all elements of nums are equal

    Invariants:
    - None.
    """
    if not nums:
        raise ValueError('first_index_of_max requires a non-empty list')
    max_val = nums[0]
    max_idx = 0
    for i in range(1, len(nums)):
        if nums[i] > max_val:
            max_val = nums[i]
            max_idx = i
    return max_idx
