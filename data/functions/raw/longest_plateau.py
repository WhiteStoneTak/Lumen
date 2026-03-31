def longest_plateau(nums: list) -> tuple[int, int, object]:
    """Return the start index, end index (inclusive), and value of the
    longest run of consecutive equal elements.

    If multiple runs tie for longest, return the one that starts earliest.
    If nums is empty, return (-1, -1, None).

    Args:
        nums: List of comparable elements.

    Returns:
        A tuple (start, end, value) where start and end are inclusive
        0-based indices.

    Examples:
        longest_plateau([1, 2, 2, 3, 3, 3, 1]) == (3, 5, 3)
        longest_plateau([5]) == (0, 0, 5)
        longest_plateau([]) == (-1, -1, None)
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

    # Handle the final run
    cur_len = len(nums) - cur_start
    best_len = best_end - best_start + 1
    if cur_len > best_len:
        best_start = cur_start
        best_end = len(nums) - 1
        best_val = cur_val

    return (best_start, best_end, best_val)
