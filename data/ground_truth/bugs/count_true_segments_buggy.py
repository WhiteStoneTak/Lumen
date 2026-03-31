def count_true_segments(flags: list) -> int:
    """Count the number of contiguous True segments in flags.

    A segment is a maximal consecutive run of True values.
    Returns 0 for an empty list or an all-False list.

    Examples:
        count_true_segments([True, True, False, True])        == 2
        count_true_segments([False, True, True, False, True]) == 2
        count_true_segments([True, True, True])               == 1
        count_true_segments([False, False])                   == 0
    """
    count = 0
    in_segment = False
    for flag in flags:
        if flag:
            in_segment = True
        elif in_segment:  # BUG: counts on exit; should count on entry (misses trailing segment)
            count += 1
            in_segment = False
    return count
