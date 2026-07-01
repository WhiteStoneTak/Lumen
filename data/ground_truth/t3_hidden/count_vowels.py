"""Hidden/metamorphic layer for count_vowels T3 (count_vowels.TR01). EXPLORATORY (W-04).

Transform: also count 'y'/'Y' as a vowel (a,e,i,o,u,y), case-insensitive.
"""

from __future__ import annotations


def reference(s: str) -> int:
    return sum(1 for ch in s.lower() if ch in "aeiouy")


HIDDEN_INPUTS = [
    ["rhythm"],       # only y is a vowel -> 1
    ["sky"],          # y -> 1
    ["YyAaEe"],       # mixed case -> 6
    [""],             # empty -> 0
    ["bcdfg"],        # no vowels -> 0
    ["Python3"],      # y + o -> 2
    ["AEIOUY"],       # all upper vowels incl. Y -> 6
    ["mystery yarn"], # multiple y -> y,e,y,a -> 4
]


def _mr_nonneg_le_len(fn) -> bool:
    for s in ["hello", "SKY", "", "aeiouy", "12345"]:
        r = fn(s)
        if not isinstance(r, int) or r < 0 or r > len(s):
            return False
    return True


def _mr_case_insensitive(fn) -> bool:
    for s in ["HeLLo", "Mystery", "AeIoU"]:
        if not (fn(s) == fn(s.upper()) == fn(s.lower())):
            return False
    return True


def _mr_concat_additive(fn) -> bool:
    for a, b in [("hello", "world"), ("sky", "high"), ("", "yay")]:
        if fn(a + b) != fn(a) + fn(b):
            return False
    return True


def _mr_appending_vowel_increments(fn) -> bool:
    for s in ["bcdf", "hello", ""]:
        if fn(s + "a") != fn(s) + 1:
            return False
        if fn(s + "y") != fn(s) + 1:   # y is now a vowel
            return False
    return True


METAMORPHIC = [
    _mr_nonneg_le_len,
    _mr_case_insensitive,
    _mr_concat_additive,
    _mr_appending_vowel_increments,
]
