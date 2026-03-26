"""Lower a typed AST to the Lumen intermediate representation (IR).

Reads typed AST artefacts from data/functions/typed_ast/ and writes
IR artefacts to data/functions/ir/.

This stage corresponds to condition C3 in the study.
"""

# TODO: define IR schema (see design constitution §IR)
# TODO: ensure the IR is semantics-preserving for the non-recursive, single-function scope


def lower_to_ir(typed_ast: dict) -> dict:
    """Convert *typed_ast* to the Lumen IR.

    # TODO: implement lowering pass.
    """
    raise NotImplementedError


def main() -> None:
    """Entry point: batch-process all files in data/functions/typed_ast/."""
    # TODO: iterate typed_ast artefacts, call lower_to_ir, write to data/functions/ir/
    raise NotImplementedError


if __name__ == "__main__":
    main()
