"""Score T1 (program understanding) responses using a holistic LLM-as-judge rubric.

Produces a scalar quality rating (e.g. 1–5) alongside a brief rationale.
"""

# TODO: design holistic scoring prompt and rating scale
# TODO: decide whether to use the same or a separate LLM for judging
# TODO: log judge responses for auditability


def score_response(response: str, reference: str) -> dict:
    """Return a holistic quality score for *response* given *reference* understanding.

    # TODO: implement LLM-as-judge call via llm_client.
    """
    raise NotImplementedError


def main() -> None:
    """Entry point: holistic-score all T1 responses in results/raw/."""
    # TODO: iterate results/raw/, call score_response, write to results/analysis/
    raise NotImplementedError


if __name__ == "__main__":
    main()
