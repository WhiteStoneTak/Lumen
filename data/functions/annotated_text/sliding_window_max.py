from typing import Any

def sliding_window_max(nums: list[Any], k: int) -> list[Any]:
    """
    Preconditions:
    - None.

    Postconditions:
    - The return value is a list
    - If nums is empty, k < 1, or k > len(nums), the return value is an empty list
    - The length of the return value equals len(nums) - k + 1 when the result is non-empty
    - Each element in the return value equals the maximum of a consecutive k-element window of nums
    - The i-th element of the return value is max(nums[i:i+k])
    - Every element of the return value is also present in nums

    Invariants:
    - None.
    """
    if not nums or k < 1 or k > len(nums):
        return []
    result = []
    for i in range(len(nums) - k + 1):
        result.append(max(nums[i:i + k]))
    return result
