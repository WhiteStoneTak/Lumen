"""Thin wrapper around LLM provider APIs (Anthropic and OpenAI).

All pipeline and experiment modules should call this module rather than
importing the provider SDK directly, to keep the provider swap surface small.

Provider routing:
    - claude-*  →  Anthropic Messages API  (ANTHROPIC_API_KEY)
    - gpt-*     →  OpenAI Chat Completions API  (OPENAI_API_KEY)
    - o1 / o3 / o4-*  →  OpenAI Chat Completions API  (OPENAI_API_KEY)

Default model is read from the LLM_MODEL environment variable.
"""

import os

# Maximum tokens requested from the API for contract generation.
# Recorded in the protocol §8.2 reproducibility record for the contract-generation LLM.
MAX_TOKENS = 1024


def _call_anthropic(prompt: str, model: str, temperature: float) -> str:
    """Send *prompt* through the Anthropic Messages API."""
    try:
        import anthropic
    except ImportError as exc:
        raise ImportError(
            "The 'anthropic' package is required. Install with: pip install anthropic"
        ) from exc

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _call_openai(prompt: str, model: str, temperature: float) -> str:
    """Send *prompt* through the OpenAI Chat Completions API."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError(
            "The 'openai' package is required. Install with: pip install openai"
        ) from exc

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY environment variable is not set.")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        max_completion_tokens=MAX_TOKENS,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def call(prompt: str, *, model: str | None = None, temperature: float = 0.0) -> str:
    """Submit *prompt* to the appropriate provider API and return the response text.

    Routes by model name prefix:
      - ``claude-*``       → Anthropic
      - ``gpt-*``          → OpenAI
      - ``o1``, ``o3``, ``o4-*`` → OpenAI

    Model defaults to the LLM_MODEL environment variable.
    """
    if model is None:
        model = get_model()

    if model.startswith("claude-"):
        return _call_anthropic(prompt, model, temperature)
    if model.startswith("gpt-") or model.startswith("o1") or model.startswith("o3") or model.startswith("o4-"):
        return _call_openai(prompt, model, temperature)

    raise ValueError(
        f"Unknown model family for model '{model}'. "
        "Expected a 'claude-*' or 'gpt-*' / 'o1' / 'o3' / 'o4-*' model identifier."
    )


def get_model() -> str:
    """Return the active model identifier from the environment."""
    model = os.environ.get("LLM_MODEL")
    if not model:
        raise EnvironmentError("LLM_MODEL environment variable is not set.")
    return model
