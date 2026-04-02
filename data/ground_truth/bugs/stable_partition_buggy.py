from typing import Callable, TypeVar

T = TypeVar("T")


def stable_partition(items: list, predicate: Callable) -> tuple[list, list]:
    """Partition items into (true_group, false_group) using a predicate.

    Preserves the relative order of items within each group.
    Items for which predicate returns True go in the first group.

    Args:
        items: List of items.
        predicate: Callable that accepts one item and returns bool.

    Returns:
        A tuple (true_group, false_group) where true_group contains items
        for which predicate(item) is True, and false_group the rest, both
        in original relative order.

    Examples:
        stable_partition([1, 2, 3, 4, 5], lambda x: x % 2 == 0) == ([2, 4], [1, 3, 5])
        stable_partition([], lambda x: True) == ([], [])
        stable_partition(["a", "b", "c"], lambda x: x > "a") == (["b", "c"], ["a"])
    """
    true_group: list = []
    false_group: list = []

    for item in items:
        if predicate(item):
            true_group.append(item)
        else:
            false_group.append(item)

    return (false_group, true_group)
