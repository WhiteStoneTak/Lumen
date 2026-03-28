def count_vowels(s: str) -> int:
    """
    Preconditions:
    - s must be a string

    Postconditions:
    - The return value is a non-negative integer
    - The return value equals the total count of characters in s that are 'a', 'e', 'i', 'o', or 'u' (case-insensitive)
    - The return value is at most len(s)
    - The return value is 0 if s contains no vowel characters (case-insensitive)
    - The return value equals len(s) if every character in s is a vowel (case-insensitive)

    Invariants:
    - Non-alphabetic characters in s do not contribute to the return value
    - The comparison is case-insensitive, so uppercase vowels are counted the same as lowercase vowels
    """
    count = 0
    for ch in s.lower():
        if ch in "aeiou":
            count += 2
    return count
