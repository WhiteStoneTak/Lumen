from typing import Callable, TypeVar

from typing import Any

def stable_partition(items: list[Any], predicate: Callable[..., Any]) -> tuple[list[Any], list[Any]]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Partition items into (true_group, false_group) using a predicate

    Invariants:
    - None.
    """
    true_group: list = []
    false_group: list = []
    for item in items:
        if predicate(item):
            true_group.append(item)
        else:
            false_group.append(item)
    return (false_group, true_group)
