"""Thin wrapper around the LLM provider API.

All pipeline and experiment modules should call this module rather than
importing the provider SDK directly, to keep the provider swap surface small.
"""

import os

# TODO: choose provider (OpenAI, Anthropic, etc.) and implement call logic
# TODO: implement retry with exponential backoff
# TODO: implement response caching keyed on (prompt_hash, model, temperature)


def call(prompt: str, *, model: str | None = None, temperature: float = 0.0) -> str:
    """Submit *prompt* to the configured LLM and return the response text.

    Model defaults to the LLM_MODEL environment variable.

    # TODO: implement API call.
    """
    raise NotImplementedError


def get_model() -> str:
    """Return the active model identifier from the environment."""
    model = os.environ.get("LLM_MODEL")
    if not model:
        raise EnvironmentError("LLM_MODEL environment variable is not set.")
    return model
