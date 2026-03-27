def clamp(value: float, lo: float, hi: float) -> float:
    """
    Preconditions:
    - lo <= hi

    Postconditions:
    - The return value is greater than or equal to lo
    - The return value is less than or equal to hi
    - If value < lo, the return value equals lo
    - If value > hi, the return value equals hi
    - If lo <= value <= hi, the return value equals value

    Invariants:
    - None.
    """
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value
