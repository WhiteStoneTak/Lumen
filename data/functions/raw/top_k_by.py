from typing import Callable, Optional


def top_k_by(items: list, k: int, key: Callable, tiebreak_key: Optional[Callable] = None) -> list:
    """Return the top-k items by a primary key, with stable tiebreaking.

    Items are sorted by key(item) descending. When primary keys are equal
    and tiebreak_key is provided, sort by tiebreak_key(item) ascending as
    the secondary key. When keys are still equal, preserve original order
    (stable). Returns at most k items; fewer if len(items) < k.

    Args:
        items: List of items.
        k: Number of top items to return. If k <= 0, return [].
        key: Primary key callable (higher = ranked higher).
        tiebreak_key: Secondary key callable for ties (lower = ranked higher).
                      If None, original order breaks ties.

    Returns:
        List of up to k items, sorted from best to kth-best.

    Examples:
        top_k_by([3, 1, 4, 1, 5], 3, key=lambda x: x) == [5, 4, 3]
        top_k_by(["b", "a", "c", "a"], 3, key=lambda s: len(s), tiebreak_key=lambda s: s) == ["a", "a", "b"]
        top_k_by([1, 2], 5, key=lambda x: x) == [2, 1]
    """
    if k <= 0:
        return []

    indexed = list(enumerate(items))

    if tiebreak_key is not None:
        sorted_indexed = sorted(
            indexed,
            key=lambda pair: (-key(pair[1]), tiebreak_key(pair[1]), pair[0]),
        )
    else:
        sorted_indexed = sorted(
            indexed,
            key=lambda pair: (-key(pair[1]), pair[0]),
        )

    return [item for _, item in sorted_indexed[:k]]
