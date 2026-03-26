"""Generate behavioral contracts for each function via an LLM.

Raw contract outputs are written to data/contracts/raw/.
Human-reviewed contracts are stored separately in data/contracts/reviewed/.
Diffs between raw and reviewed are stored in data/contracts/diffs/.

Contracts are used in conditions C1+ and C4.
C1+ contracts are derived from C4 to preserve information parity.
"""

# TODO: design contract prompt template (see design constitution §Contracts)
# TODO: define contract schema (preconditions, postconditions, invariants)
# TODO: implement diff generation between raw and reviewed contracts


def generate_contract(source: str) -> dict:
    """Call the LLM to generate a behavioral contract for *source*.

    # TODO: implement using llm_client.
    """
    raise NotImplementedError


def main() -> None:
    """Entry point: batch-generate contracts for all raw functions."""
    # TODO: iterate data/functions/raw/, call generate_contract, write to data/contracts/raw/
    raise NotImplementedError


if __name__ == "__main__":
    main()
