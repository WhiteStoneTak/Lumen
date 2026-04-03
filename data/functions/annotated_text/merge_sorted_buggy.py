from typing import Any

def merge_sorted(a: list[Any], b: list[Any]) -> list[Any]:
    """
    Preconditions:
    - a is sorted in non-decreasing order
    - b is sorted in non-decreasing order

    Postconditions:
    - The return value is a list sorted in non-decreasing order
    - The length of the return value equals len(a) + len(b)
    - Every element from a appears in the return value the same number of times as in a
    - Every element from b appears in the return value the same number of times as in b
    - If both a and b are empty, the return value is an empty list

    Invariants:
    - None.
    """
    result = []
    i, j = (0, 0)
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
    while j < len(b) - 1:
        result.append(b[j])
        j += 1
    return result
