def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    """Merge all overlapping intervals and return sorted non-overlapping result.

    Two intervals [a, b] and [c, d] overlap if c <= b (when sorted by start).
    Adjacent touching intervals (e.g. [1,2] and [2,4]) are also merged.

    Args:
        intervals: List of [start, end] pairs with start <= end.

    Returns:
        List of merged [start, end] pairs sorted by start, non-overlapping.

    Examples:
        merge_intervals([[1,3],[2,6],[8,10],[15,18]]) == [[1,6],[8,10],[15,18]]
        merge_intervals([[1,4],[4,5]]) == [[1,5]]
        merge_intervals([]) == []
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
