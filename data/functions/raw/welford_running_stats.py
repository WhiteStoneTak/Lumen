def welford_running_stats(values: list[float]) -> list[tuple[int, float, float]]:
    """Compute running statistics using Welford's online algorithm.

    At each step i (1-indexed), return (count, mean, variance) where variance
    is the population variance (divided by count, not count-1).

    Args:
        values: List of floats.

    Returns:
        List of (count, mean, variance) tuples, one per input value, in order.
        Variance at count=1 is 0.0.

    Examples:
        welford_running_stats([2.0, 4.0, 6.0]) == [(1, 2.0, 0.0), (2, 3.0, 1.0), (3, 4.0, 8/3)]
        welford_running_stats([]) == []
        welford_running_stats([5.0]) == [(1, 5.0, 0.0)]
    """
    result: list[tuple[int, float, float]] = []
    n = 0
    mean = 0.0
    M2 = 0.0

    for x in values:
        n += 1
        delta = x - mean
        mean += delta / n
        delta2 = x - mean
        M2 += delta * delta2
        variance = M2 / n
        result.append((n, mean, variance))

    return result
