def camel_to_snake(name: str) -> str:
    """
    Preconditions:
    - None.

    Postconditions:
    - Convert a camelCase or PascalCase identifier to snake_case

    Invariants:
    - None.
    """
    if not name:
        return name
    chars = list(name)
    result: list[str] = []
    for i, ch in enumerate(chars):
        if ch.isupper():
            prev_lower_or_digit = i > 0 and (chars[i - 1].islower() or chars[i - 1].isdigit())
            next_is_lower = i + 1 < len(chars) and chars[i + 1].islower()
            prev_is_upper = i > 0 and chars[i - 1].isupper()
            if prev_lower_or_digit:
                result.append('_')
            elif prev_is_upper or next_is_lower:
                result.append('_')
            result.append(ch.lower())
        else:
            result.append(ch)
    return ''.join(result)
