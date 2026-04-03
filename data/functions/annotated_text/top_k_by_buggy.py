from typing import Callable, Optional

from typing import Any

def top_k_by(items: list[Any], k: int, key: Callable[..., Any], tiebreak_key: Callable[..., Any | None]) -> list[Any]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Return the top-k items by a primary key, with stable tiebreaking

    Invariants:
    - None.
    """
    if k <= 0:
        return []
    indexed = list(enumerate(items))
    if tiebreak_key is not None:
        sorted_indexed = sorted(indexed, key=lambda pair: (key(pair[1]), tiebreak_key(pair[1]), pair[0]))
    else:
        sorted_indexed = sorted(indexed, key=lambda pair: (-key(pair[1]), pair[0]))
    return [item for _, item in sorted_indexed[:k]]
