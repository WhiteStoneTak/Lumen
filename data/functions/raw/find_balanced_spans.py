def find_balanced_spans(s: str, open_char: str, close_char: str) -> list[tuple[int, int]]:
    """Find all top-level balanced bracket spans in a string.

    Returns the (start, end) index pairs of the outermost matching pairs,
    where start is the index of open_char and end is the index of the
    matching close_char.

    Nested brackets are not returned separately — only the outermost span.
    Unmatched brackets are ignored.

    Args:
        s: Input string.
        open_char: The opening bracket character (single char).
        close_char: The closing bracket character (single char).

    Returns:
        List of (start, end) index tuples in order of appearance.

    Examples:
        find_balanced_spans("a(b(c)d)e(f)", "(", ")") == [(1, 7), (9, 11)]
        find_balanced_spans("((()))", "(", ")") == [(0, 5)]
        find_balanced_spans("no brackets", "(", ")") == []
    """
    result: list[tuple[int, int]] = []
    depth = 0
    span_start = -1

    for i, ch in enumerate(s):
        if ch == open_char:
            if depth == 0:
                span_start = i
            depth += 1
        elif ch == close_char:
            if depth > 0:
                depth -= 1
                if depth == 0:
                    result.append((span_start, i))
                    span_start = -1

    return result
