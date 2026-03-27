"""Thin wrapper around the Anthropic LLM provider API.

All pipeline and experiment modules should call this module rather than
importing the provider SDK directly, to keep the provider swap surface small.

Requirements:
    pip install anthropic
    ANTHROPIC_API_KEY environment variable set

Default model is read from the LLM_MODEL environment variable.
"""

import os

# Maximum tokens requested from the API for contract generation.
# Recorded in the protocol §8.2 reproducibility record for the contract-generation LLM.
MAX_TOKENS = 1024


def call(prompt: str, *, model: str | None = None, temperature: float = 0.0) -> str:
    """Submit *prompt* to the Anthropic Messages API and return the response text.

    Model defaults to the LLM_MODEL environment variable.
    Raises ImportError if the 'anthropic' package is not installed.
    Raises EnvironmentError if ANTHROPIC_API_KEY is not set.
    """
    try:
        import anthropic
    except ImportError as exc:
        raise ImportError(
            "The 'anthropic' package is required. Install with: pip install anthropic"
        ) from exc

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")

    if model is None:
        model = get_model()

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def get_model() -> str:
    """Return the active model identifier from the environment."""
    model = os.environ.get("LLM_MODEL")
    if not model:
        raise EnvironmentError("LLM_MODEL environment variable is not set.")
    return model
