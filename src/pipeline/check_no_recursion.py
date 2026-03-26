"""Verify that a function contains no direct or indirect recursion.

Used as a pre-processing gate to enforce the non-recursive scope constraint.
Functions that fail this check are excluded from the dataset.
"""

import ast


def is_recursive(source: str) -> bool:
    """Return True if *source* contains any recursive call.

    Checks for direct self-calls only (indirect recursion is out of scope
    for the current single-function constraint).

    # TODO: extend to detect mutual recursion if scope widens.
    """
    # TODO: implement using ast.walk + call graph analysis
    raise NotImplementedError


def main() -> None:
    """Entry point: scan all files in data/functions/raw/ and report recursive ones."""
    # TODO: iterate raw sources, call is_recursive, log / exclude flagged functions
    raise NotImplementedError


if __name__ == "__main__":
    main()
