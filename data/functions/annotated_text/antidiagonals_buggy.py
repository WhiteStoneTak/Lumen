from typing import Any

def antidiagonals(matrix: list[list[Any]]) -> list[list[Any]]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Return the antidiagonals of a 2D matrix as a list of lists

    Invariants:
    - None.
    """
    if not matrix or not matrix[0]:
        return []
    rows = len(matrix)
    cols = len(matrix[0])
    result: list[list] = []
    for d in range(rows + cols - 1):
        diagonal: list = []
        r_start = max(0, d - cols)
        r_end = min(rows, d + 1)
        for r in range(r_start, r_end):
            c = d - r
            diagonal.append(matrix[r][c])
        result.append(diagonal)
    return result
