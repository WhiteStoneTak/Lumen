def equal_width_buckets(values: list[float], n_buckets: int) -> list[int]:
    """
    Preconditions:
    - n_buckets >= 1 and len(values) >= 1.

    Postconditions:
    - Assign each value to one of n_buckets equal-width buckets (0-indexed)

    Invariants:
    - None.
    """
    min_val = min(values)
    max_val = max(values)
    if min_val == max_val:
        return [0] * len(values)
    width = (max_val - min_val) / n_buckets
    result: list[int] = []
    for v in values:
        bucket = int((v - min_val) / width)
        result.append(bucket)
    return result
