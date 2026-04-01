def camel_to_snake(name: str) -> str:
    """Convert a camelCase or PascalCase identifier to snake_case.

    Rules:
    - Insert underscore before each uppercase letter that follows a lowercase
      letter or digit.
    - Insert underscore before each uppercase letter that is followed by a
      lowercase letter and is preceded by another uppercase letter
      (handles abbreviations like "XMLParser" -> "xml_parser").
    - Convert all characters to lowercase.
    - Leading/trailing underscores are not added.

    Args:
        name: A camelCase or PascalCase identifier string.

    Returns:
        The snake_case version.

    Examples:
        camel_to_snake("camelCase") == "camel_case"
        camel_to_snake("XMLParser") == "xml_parser"
        camel_to_snake("getHTTPSResponse") == "get_https_response"
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
                result.append("_")
            elif prev_is_upper or next_is_lower:  # BUG: should be `and` not `or`
                result.append("_")

            result.append(ch.lower())
        else:
            result.append(ch)

    return "".join(result)
