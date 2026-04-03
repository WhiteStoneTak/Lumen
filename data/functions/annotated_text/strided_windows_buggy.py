from typing import Any

def strided_windows(items: list[Any], size: int, stride: int, include_partial: bool) -> list[list[Any]]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Extract overlapping or non-overlapping windows from a list

    Invariants:
    - None.
    """
    result: list[list] = []
    n = len(items)
    i = 0
    while i + size < n:
        result.append(list(items[i:i + size]))
        i += stride
    if include_partial and i < n:
        result.append(list(items[i:]))
    return result
