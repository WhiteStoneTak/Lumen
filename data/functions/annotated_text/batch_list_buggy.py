from typing import Any

def batch_list(items: list[Any], batch_size: int) -> list[Any]:
    """
    Preconditions:
    - None.

    Postconditions:
    - The return value is a list of lists
    - If items is empty or batch_size < 1, the return value is an empty list
    - Each sub-list has at most batch_size elements
    - All elements from items appear in the return value in their original order
    - The concatenation of all sub-lists equals items
    - All sub-lists except possibly the last have exactly batch_size elements

    Invariants:
    - None.
    """
    if not items or batch_size < 1:
        return []
    result = []
    for i in range(0, len(items), batch_size + 1):
        result.append(items[i:i + batch_size])
    return result
