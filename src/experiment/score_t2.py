"""Score T2 (bug detection) responses.

Measures precision, recall, and F1 against ground-truth bug labels stored
in data/ground_truth/bugs/.
"""

# TODO: define bug label schema (bug id, location, description)
# TODO: implement LLM response parser to extract predicted bug locations


def score_response(response: str, ground_truth: list[dict]) -> dict:
    """Compute precision, recall, and F1 for *response* against *ground_truth*.

    # TODO: implement matching logic.
    """
    raise NotImplementedError


def main() -> None:
    """Entry point: score all T2 responses in results/raw/."""
    # TODO: iterate results/raw/, call score_response, write to results/analysis/
    raise NotImplementedError


if __name__ == "__main__":
    main()
