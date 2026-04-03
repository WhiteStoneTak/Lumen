def tokenize_arithmetic(expr: str) -> list[tuple[str, str]]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Tokenize a simple arithmetic expression into (type, value) pairs

    Invariants:
    - None.
    """
    tokens: list[tuple[str, str]] = []
    i = 0
    n = len(expr)
    while i < n:
        ch = expr[i]
        if ch == ' ':
            i += 1
            continue
        if ch in '+-*/':
            tokens.append(('OP', ch))
            i += 1
            continue
        if ch == '(':
            tokens.append(('LPAREN', ch))
            i += 1
            continue
        if ch == ')':
            tokens.append(('RPAREN', ch))
            i += 1
            continue
        if ch.isdigit() or ch == '.':
            j = i
            while j < n and (expr[j].isdigit() or expr[j] == '.'):
                j += 1
            tokens.append(('NUM', expr[i:j]))
            i = j
            continue
        i += 1
    return tokens
