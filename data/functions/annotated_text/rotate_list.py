from typing import Any

def rotate_list(items: list[Any], k: int) -> list[Any]:
    """
    Preconditions:
    - None.

    Postconditions:
    - The return value is a list
    - If items is empty, the return value is an empty list
    - The length of the return value equals len(items)
    - The return value equals items[(k % len(items)):] + items[:(k % len(items))] when items is non-empty
    - If k % len(items) == 0, the return value equals list(items)
    - All elements from items appear in the return value with the same frequency

    Invariants:
    - None.
    """
    if not items:
        return []
    n = len(items)
    k = k % n
    if k == 0:
        return list(items)
    return items[k:] + items[:k]
