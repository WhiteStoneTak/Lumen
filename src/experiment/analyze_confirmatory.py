"""Run pre-registered confirmatory analyses on collected results.

All analyses in this file are frozen prior to data collection.
Do not add post-hoc analyses here; use analyze_exploratory.py instead.

Reads from results/analysis/ and writes summary tables and figures to
results/analysis/ and results/figures/.
"""

# TODO: specify confirmatory hypotheses and statistical tests (see experimental protocol)
# TODO: implement effect size calculations (e.g. Cohen's d, eta-squared)
# TODO: implement correction for multiple comparisons if applicable


def run_confirmatory_analyses(results_dir: str) -> dict:
    """Load scored results from *results_dir* and run all confirmatory tests.

    # TODO: implement.
    """
    raise NotImplementedError


def main() -> None:
    """Entry point: run confirmatory analyses and write outputs."""
    # TODO: call run_confirmatory_analyses, write tables and figures
    raise NotImplementedError


if __name__ == "__main__":
    main()
