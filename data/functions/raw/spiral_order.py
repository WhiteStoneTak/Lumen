def spiral_order(matrix: list[list[int]]) -> list[int]:
    """Return the elements of a 2D matrix in clockwise spiral order.

    Traversal starts from the top-left, goes right, then down, then left,
    then up, and repeats inward.

    Args:
        matrix: List of rows, each a list of ints. All rows have equal length.
                May be empty or have 0 columns.

    Returns:
        List of elements in spiral (clockwise) order.

    Examples:
        spiral_order([[1, 2, 3], [4, 5, 6], [7, 8, 9]]) == [1, 2, 3, 6, 9, 8, 7, 4, 5]
        spiral_order([[1, 2, 3, 4]]) == [1, 2, 3, 4]
        spiral_order([]) == []
    """
    if not matrix or not matrix[0]:
        return []

    result: list[int] = []
    top = 0
    bottom = len(matrix) - 1
    left = 0
    right = len(matrix[0]) - 1

    while top <= bottom and left <= right:
        for col in range(left, right + 1):
            result.append(matrix[top][col])
        top += 1

        for row in range(top, bottom + 1):
            result.append(matrix[row][right])
        right -= 1

        if top <= bottom:
            for col in range(right, left - 1, -1):
                result.append(matrix[bottom][col])
            bottom -= 1

        if left <= right:
            for row in range(bottom, top - 1, -1):
                result.append(matrix[row][left])
            left += 1

    return result
