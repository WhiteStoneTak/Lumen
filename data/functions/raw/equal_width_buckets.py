def equal_width_buckets(values: list[float], n_buckets: int) -> list[int]:
    """Assign each value to one of n_buckets equal-width buckets (0-indexed).

    Buckets span [min_val + i*width, min_val + (i+1)*width) for i=0..n-2,
    and [min_val + (n-1)*width, max_val] (inclusive on both ends) for the
    last bucket. Values equal to max_val always go in the last bucket.

    If all values are equal, all go in bucket 0.
    Requires n_buckets >= 1 and len(values) >= 1.

    Args:
        values: Non-empty list of floats.
        n_buckets: Number of equal-width buckets (>= 1).

    Returns:
        List of bucket indices (0-indexed) in the same order as values.

    Examples:
        equal_width_buckets([1.0, 2.0, 3.0, 4.0, 5.0], 2) == [0, 0, 1, 1, 1]
        equal_width_buckets([10, 20, 30], 3) == [0, 1, 2]
        equal_width_buckets([5, 5, 5], 3) == [0, 0, 0]
    """
    min_val = min(values)
    max_val = max(values)

    if min_val == max_val:
        return [0] * len(values)

    width = (max_val - min_val) / n_buckets
    result: list[int] = []

    for v in values:
        bucket = int((v - min_val) / width)
        if bucket >= n_buckets:
            bucket = n_buckets - 1
        result.append(bucket)

    return result
