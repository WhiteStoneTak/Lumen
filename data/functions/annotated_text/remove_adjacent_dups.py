from typing import Any

def remove_adjacent_dups(items: list[Any]) -> list[Any]:
    """
    Preconditions:
    - None.

    Postconditions:
    - The return value is a list
    - If items is empty, the return value is an empty list
    - The return value contains no two adjacent equal elements
    - Every element in the return value also appears in items (values are preserved)
    - The relative order of distinct adjacent runs is maintained
    - The length of the return value is at most len(items)

    Invariants:
    - None.
    """
    if not items:
        return []
    result = [items[0]]
    for item in items[1:]:
        if item != result[-1]:
            result.append(item)
    return result
