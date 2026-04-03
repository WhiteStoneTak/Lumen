from typing import Any

def group_by_key(pairs: list[tuple[Any, ...]]) -> dict[Any, Any]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Group a list of (key, value) pairs into a dict of value-lists

    Invariants:
    - None.
    """
    result: dict = {}
    for key, value in pairs:
        if key not in result:
            result[key] = []
        result[key].append(value)
    return result
