def clamp(value: float, lo: float, hi: float) -> float:
    """Return value clamped to the closed interval [lo, hi].

    Assumes lo <= hi.
    """
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value
