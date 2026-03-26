"""Annotate a parsed AST with type information to produce a typed AST.

Reads AST artefacts from data/functions/ast/ and writes typed AST
artefacts to data/functions/typed_ast/.

This stage corresponds to condition C2 in the study.
"""

# TODO: decide type-inference strategy (mypy API, pyright, manual annotation)
# TODO: define typed AST schema


def annotate_types(ast_dict: dict) -> dict:
    """Return a copy of *ast_dict* enriched with type annotations.

    # TODO: implement type inference / annotation logic.
    """
    raise NotImplementedError


def main() -> None:
    """Entry point: batch-process all files in data/functions/ast/."""
    # TODO: iterate ast artefacts, call annotate_types, write to data/functions/typed_ast/
    raise NotImplementedError


if __name__ == "__main__":
    main()
