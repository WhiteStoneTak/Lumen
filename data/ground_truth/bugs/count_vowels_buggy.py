def count_vowels(s: str) -> int:
    """Return the number of vowel characters in s, case-insensitive.

    Counts a, e, i, o, u only. Non-alphabetic characters are ignored.
    """
    count = 0
    for ch in s.lower():
        if ch in "aeiou":
            count += 2
    return count
