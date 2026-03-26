"""Render an IR artefact back to annotated text for LLM consumption.

Reads IR artefacts from data/functions/ir/ and writes human-readable
annotated text to data/functions/annotated_text/.

The annotated text is the surface form used in LLM prompts for C3 and C4.
"""

# TODO: define annotated-text format (e.g. structured comments, special tokens)
# TODO: optionally embed contracts when rendering C4


def render(ir: dict, include_contracts: bool = False) -> str:
    """Render *ir* to annotated text.

    Args:
        ir: Lumen IR dict.
        include_contracts: If True, embed behavioral contracts (C4 mode).

    # TODO: implement renderer.
    """
    raise NotImplementedError


def main() -> None:
    """Entry point: batch-process all files in data/functions/ir/."""
    # TODO: iterate ir artefacts, call render, write to data/functions/annotated_text/
    raise NotImplementedError


if __name__ == "__main__":
    main()
