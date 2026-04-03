from typing import Any

def longest_plateau(nums: list[Any]) -> tuple[int, int, object]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Return the start index, end index (inclusive), and value of the longest run of consecutive equal elements

    Invariants:
    - None.
    """
    if not nums:
        return (-1, -1, None)
    best_start = 0
    best_end = 0
    best_val = nums[0]
    cur_start = 0
    cur_val = nums[0]
    for i in range(1, len(nums)):
        if nums[i] == cur_val:
            pass
        else:
            cur_len = i - cur_start
            best_len = best_end - best_start + 1
            if cur_len > best_len:
                best_start = cur_start
                best_end = i - 1
                best_val = cur_val
            cur_start = i
            cur_val = nums[i]
    cur_len = len(nums) - cur_start
    best_len = best_end - best_start + 1
    if cur_len >= best_len:
        best_start = cur_start
        best_end = len(nums) - 1
        best_val = cur_val
    return (best_start, best_end, best_val)
