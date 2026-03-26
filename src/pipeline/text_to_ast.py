"""Parse raw Python source text into an AST representation.

Reads raw function source from data/functions/raw/ and writes
serialised AST artefacts to data/functions/ast/.

Scope: non-recursive, single-function Python only.
"""

# TODO: decide serialisation format (json / pickle / custom)
# TODO: validate that each function is non-recursive before emitting
# TODO: handle parse errors gracefully and log failures


def parse_function(source: str) -> dict:
    """Parse *source* and return a serialisable AST dict.

    # TODO: implement using the stdlib `ast` module.
    """
    raise NotImplementedError


def main() -> None:
    """Entry point: batch-process all files in data/functions/raw/."""
    # TODO: iterate raw sources, call parse_function, write to data/functions/ast/
    raise NotImplementedError


if __name__ == "__main__":
    main()
