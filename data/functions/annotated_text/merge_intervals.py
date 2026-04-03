def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Merge all overlapping intervals and return sorted non-overlapping result

    Invariants:
    - None.
    """
    if not intervals:
        return []
    sorted_intervals = sorted(intervals, key=lambda iv: iv[0])
    result: list[list[int]] = []
    current = [sorted_intervals[0][0], sorted_intervals[0][1]]
    for i in range(1, len(sorted_intervals)):
        next_start = sorted_intervals[i][0]
        next_end = sorted_intervals[i][1]
        if next_start <= current[1]:
            if next_end > current[1]:
                current[1] = next_end
        else:
            result.append(current)
            current = [next_start, next_end]
    result.append(current)
    return result
