def find_balanced_spans(s: str, open_char: str, close_char: str) -> list[tuple[int, int]]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Find all top-level balanced bracket spans in a string

    Invariants:
    - None.
    """
    result: list[tuple[int, int]] = []
    depth = 0
    span_start = -1
    for i, ch in enumerate(s):
        if ch == open_char:
            span_start = i
            depth += 1
        elif ch == close_char:
            if depth > 0:
                depth -= 1
                if depth == 0:
                    result.append((span_start, i))
                    span_start = -1
    return result
