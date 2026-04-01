def sorted_list_intersection(a: list[int], b: list[int]) -> list[int]:
    """Return the intersection of two sorted lists, preserving duplicate counts.

    Each value appears in the result min(count_in_a, count_in_b) times.
    Result is sorted.

    Args:
        a: Sorted list of integers (non-decreasing).
        b: Sorted list of integers (non-decreasing).

    Returns:
        Sorted list of integers representing the multiset intersection.

    Examples:
        sorted_list_intersection([1, 2, 2, 3], [2, 2, 3, 4]) == [2, 2, 3]
        sorted_list_intersection([1, 2, 3], [4, 5, 6]) == []
        sorted_list_intersection([], [1, 2]) == []
    """
    result: list[int] = []
    i = 0
    j = 0

    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            result.append(a[i])
            i += 1
            # BUG: j += 1 is missing — j is not advanced, so b[j] can match
            # multiple elements from a, producing too many copies
        elif a[i] < b[j]:
            i += 1
        else:
            j += 1

    return result
