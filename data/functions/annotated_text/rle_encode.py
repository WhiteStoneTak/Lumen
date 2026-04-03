from typing import Any

def rle_encode(items: list[Any]) -> list[Any]:
    """
    Preconditions:
    - None.

    Postconditions:
    - The return value is a list of (value, count) tuples
    - If items is empty, the return value is an empty list
    - Each count in the return value is a positive integer
    - No two adjacent tuples in the return value have the same value
    - The sum of all counts equals len(items)
    - Expanding each (value, count) pair yields items exactly (run-length decoding recovers the input)

    Invariants:
    - None.
    """
    if not items:
        return []
    result = []
    current = items[0]
    count = 1
    for item in items[1:]:
        if item == current:
            count += 1
        else:
            result.append((current, count))
            current = item
            count = 1
    result.append((current, count))
    return result
