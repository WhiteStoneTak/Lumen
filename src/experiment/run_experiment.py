"""Orchestrate a full experiment run across all conditions and task types.

For each function in the dataset and each condition (C1, C1+, C2, C3, C4),
submits the appropriate prompt to the LLM and stores raw outputs under
results/raw/.
"""

# TODO: define run configuration schema (conditions, task types, model, seed)
# TODO: implement prompt assembly per condition and task type
# TODO: implement output persistence with stable filenames / hashes


def run_condition(function_id: str, condition: str, task_type: str) -> dict:
    """Submit one LLM call and return the raw response dict.

    # TODO: implement using llm_client.
    """
    raise NotImplementedError


def main() -> None:
    """Entry point: run the full experiment grid."""
    # TODO: load dataset, iterate (function × condition × task), call run_condition
    raise NotImplementedError


if __name__ == "__main__":
    main()
