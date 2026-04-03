def peak_valley_indices(nums: list[float]) -> list[tuple[str, int]]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Return the indices of strict local peaks and valleys in order

    Invariants:
    - None.
    """
    result: list[tuple[str, int]] = []
    if len(nums) < 3:
        return result
    for i in range(1, len(nums) - 1):
        left = nums[i - 1]
        mid = nums[i]
        right = nums[i + 1]
        if mid >= left and mid >= right:
            result.append(('peak', i))
        elif mid < left and mid < right:
            result.append(('valley', i))
    return result
