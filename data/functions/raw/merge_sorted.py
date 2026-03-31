def merge_sorted(a: list, b: list) -> list:
    """Merge two sorted lists into one sorted list.

    Both a and b must be sorted in ascending order.
    The returned list contains all elements from both inputs, also in ascending order.
    Duplicate values across a and b are preserved.

    Examples:
        merge_sorted([1, 3, 5], [2, 4, 6]) == [1, 2, 3, 4, 5, 6]
        merge_sorted([1, 2], [3, 4, 5, 6]) == [1, 2, 3, 4, 5, 6]
        merge_sorted([], [1, 2])            == [1, 2]
    """
    result = []
    i, j = 0, 0
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            result.append(a[i])
            i += 1
        else:
            result.append(b[j])
            j += 1
    while i < len(a):
        result.append(a[i])
        i += 1
    while j < len(b):
        result.append(b[j])
        j += 1
    return result
