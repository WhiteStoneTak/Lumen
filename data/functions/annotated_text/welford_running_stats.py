def welford_running_stats(values: list[float]) -> list[tuple[int, float, float]]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Compute running statistics using Welford's online algorithm

    Invariants:
    - None.
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
