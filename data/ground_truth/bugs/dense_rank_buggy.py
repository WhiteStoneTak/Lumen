def dense_rank(values: list[float]) -> list[int]:
    """Assign dense ranks to a list of values (1-based).

    Tied values receive the same rank. The next distinct value receives
    rank+1 (not rank+count_of_ties). Returned ranks correspond to the
    original input positions.

    Args:
        values: List of floats (or ints).

    Returns:
        List of integer ranks in the same order as input values.

    Examples:
        dense_rank([3.0, 1.0, 4.0, 1.0, 5.0]) == [2, 1, 3, 1, 4]
        dense_rank([5, 5, 5]) == [1, 1, 1]
        dense_rank([]) == []
    """
    if not values:
        return []

    sorted_unique = sorted(set(values))
    rank_map: dict = {}

    for rank, val in enumerate(sorted_unique, start=0):  # BUG: should be start=1
        rank_map[val] = rank

    return [rank_map[v] for v in values]
