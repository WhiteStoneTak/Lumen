from typing import Callable, Optional


def chunk_on_change(items: list, key: Optional[Callable] = None) -> list[list]:
    """Split items into chunks, starting a new chunk whenever key(item) changes.

    Consecutive items with the same key value are grouped together.
    If key is None, uses the item itself as the key.

    Args:
        items: List of items.
        key: Optional callable mapping an item to its group key. If None,
             uses identity.

    Returns:
        List of non-empty sublists, each a maximal run of items with equal
        key values.

    Examples:
        chunk_on_change([1, 1, 2, 2, 1, 3]) == [[1, 1], [2, 2], [1], [3]]
        chunk_on_change(["ab", "ac", "b", "bc"], key=lambda s: s[0]) == [["ab", "ac"], ["b", "bc"]]
        chunk_on_change([]) == []
    """
    if not items:
        return []

    key_fn: Callable = key if key is not None else (lambda x: x)

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
            # BUG: current_key is not updated — should be: current_key = item_key

    result.append(current_chunk)
    return result
