def sorted_list_intersection(a: list[int], b: list[int]) -> list[int]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Return the intersection of two sorted lists, preserving duplicate counts

    Invariants:
    - None.
    """
    result: list[int] = []
    i = 0
    j = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            result.append(a[i])
            i += 1
        elif a[i] < b[j]:
            i += 1
        else:
            j += 1
    return result
