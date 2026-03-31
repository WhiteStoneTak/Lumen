def antidiagonals(matrix: list[list]) -> list[list]:
    """Return the antidiagonals of a 2D matrix as a list of lists.

    Antidiagonals run from top-right to bottom-left. The first antidiagonal
    contains matrix[0][0]. The second contains matrix[0][1] and matrix[1][0].
    Elements within each antidiagonal are listed in row-ascending order
    (top to bottom, i.e. increasing row index).

    Args:
        matrix: List of rows. All rows have equal length. May be empty.

    Returns:
        List of antidiagonals, each a list of elements.

    Examples:
        antidiagonals([[1, 2, 3], [4, 5, 6], [7, 8, 9]]) == [[1], [2, 4], [3, 5, 7], [6, 8], [9]]
        antidiagonals([[1, 2], [3, 4]]) == [[1], [2, 3], [4]]
        antidiagonals([]) == []
    """
    if not matrix or not matrix[0]:
        return []

    rows = len(matrix)
    cols = len(matrix[0])
    result: list[list] = []

    for d in range(rows + cols - 1):
        diagonal: list = []
        r_start = max(0, d - cols + 1)
        r_end = min(rows, d + 1)
        for r in range(r_start, r_end):
            c = d - r
            diagonal.append(matrix[r][c])
        result.append(diagonal)

    return result
