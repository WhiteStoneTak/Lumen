"""Score T1 (program understanding) responses using a binary checklist rubric.

Each checklist item is scored 0 or 1. The total score is the sum of items
marked correct.

Ground-truth checklists are read from data/ground_truth/checklists/.
"""

# TODO: define checklist item schema
# TODO: implement automated scoring (LLM-as-judge or keyword matching)
# TODO: compute inter-rater reliability if human scoring is involved


def score_response(response: str, checklist: list[dict]) -> dict:
    """Score *response* against *checklist*.

    Returns a dict of item-level scores and an aggregate total.

    # TODO: implement scoring logic.
    """
    raise NotImplementedError


def main() -> None:
    """Entry point: score all T1 responses in results/raw/."""
    # TODO: iterate results/raw/, call score_response, write to results/analysis/
    raise NotImplementedError


if __name__ == "__main__":
    main()
