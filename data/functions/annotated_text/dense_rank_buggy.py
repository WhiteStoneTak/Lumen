def dense_rank(values: list[float]) -> list[int]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Assign dense ranks to a list of values (1-based)

    Invariants:
    - None.
    """
    if not values:
        return []
    sorted_unique = sorted(set(values))
    rank_map: dict = {}
    for rank, val in enumerate(sorted_unique, start=0):
        rank_map[val] = rank
    return [rank_map[v] for v in values]
