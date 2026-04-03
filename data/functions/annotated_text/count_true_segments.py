from typing import Any

def count_true_segments(flags: list[Any]) -> int:
    """
    Preconditions:
    - None.

    Postconditions:
    - The return value is a non-negative integer
    - If flags is empty or contains no True values, the return value is 0
    - The return value counts maximal consecutive runs of True values
    - If all elements of flags are True, the return value is 1
    - The return value increments by 1 for each False-to-True transition in flags

    Invariants:
    - None.
    """
    count = 0
    in_segment = False
    for flag in flags:
        if flag and (not in_segment):
            count += 1
            in_segment = True
        elif not flag:
            in_segment = False
    return count
