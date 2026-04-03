from typing import Callable, Optional

from typing import Any

def chunk_on_change(items: list[Any], key: Callable[..., Any | None]) -> list[list[Any]]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Split items into chunks, starting a new chunk whenever key(item) changes

    Invariants:
    - None.
    """
    if not items:
        return []
    key_fn: Callable = key if key is not None else lambda x: x
    result: list[list] = []
    current_chunk: list = [items[0]]
    current_key = key_fn(items[0])
    for i in range(1, len(items)):
        item_key = key_fn(items[i])
        if item_key == current_key:
            current_chunk.append(items[i])
        else:
            result.append(current_chunk)
            current_chunk = [items[i]]
            current_key = item_key
    result.append(current_chunk)
    return result
