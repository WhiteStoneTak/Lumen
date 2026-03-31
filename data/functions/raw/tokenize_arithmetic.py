def tokenize_arithmetic(expr: str) -> list[tuple[str, str]]:
    """Tokenize a simple arithmetic expression into (type, value) pairs.

    Recognized token types:
    - "NUM": integer or decimal number (positive; leading minus is treated as OP)
    - "OP": one of +, -, *, /
    - "LPAREN": (
    - "RPAREN": )

    Whitespace between tokens is ignored. The expression contains only
    digits, decimal points, +, -, *, /, (, ), and whitespace.

    Args:
        expr: A string representing an arithmetic expression.

    Returns:
        List of (type, value) tuples in left-to-right order.

    Examples:
        tokenize_arithmetic("3 + 42") == [("NUM", "3"), ("OP", "+"), ("NUM", "42")]
        tokenize_arithmetic("(1+2)*3") == [("LPAREN", "("), ("NUM", "1"), ("OP", "+"), ("NUM", "2"), ("RPAREN", ")"), ("OP", "*"), ("NUM", "3")]
        tokenize_arithmetic("10/2") == [("NUM", "10"), ("OP", "/"), ("NUM", "2")]
    """
    tokens: list[tuple[str, str]] = []
    i = 0
    n = len(expr)

    while i < n:
        ch = expr[i]

        if ch == " ":
            i += 1
            continue

        if ch in "+-*/":
            tokens.append(("OP", ch))
            i += 1
            continue

        if ch == "(":
            tokens.append(("LPAREN", ch))
            i += 1
            continue

        if ch == ")":
            tokens.append(("RPAREN", ch))
            i += 1
            continue

        if ch.isdigit() or ch == ".":
            j = i
            while j < n and (expr[j].isdigit() or expr[j] == "."):
                j += 1
            tokens.append(("NUM", expr[i:j]))
            i = j
            continue

        i += 1

    return tokens
