from typing import Any

def is_sorted(items: list[Any]) -> bool:
    """
    Preconditions:
    - items must be a list
    - Elements in items must be comparable to each other using the > operator

    Postconditions:
    - The return value is a bool
    - The return value is True if items is empty
    - The return value is True if items contains exactly one element
    - The return value is True if every element is less than or equal to the next element (non-decreasing order)
    - The return value is False if any element is strictly greater than the element immediately following it

    Invariants:
    - The function does not modify the input list
    """
    for i in range(len(items) - 1):
        if items[i] >= items[i + 1]:
            return False
    return True
