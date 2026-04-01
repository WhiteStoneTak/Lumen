"""executor.py — Thin model executor for the Lumen automation layer.

This is the sole call-site for LLM API calls within the automation layer.
All other modules import and call `executor.call()` — they do not touch
provider SDKs directly.

Execution modes (set via LUMEN_EXECUTOR env var or --mode flag):
    live    Default. Real API call via Anthropic or OpenAI.
    mock    Returns a canned stub response. For local testing without API keys.
    manual  Prints the prompt and reads the response from stdin. For human-in-loop.

Model routing:
    - Model keys ("sonnet", "opus", "gpt54", "codex") are resolved to model IDs
      via automation/config/models.json.
    - Bare model IDs (e.g. "claude-sonnet-4-6") are used directly.
    - For `live` mode, delegates to src/utils/llm_client.py when available,
      falling back to direct API calls if the repo package is not installed.

Extension point:
    To add a new provider or execution backend (e.g. Claude Code SDK, batch API),
    add a new mode branch in `call()` and a helper function below.
    Do NOT add provider logic to lumen.py.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

AUTO_DIR = Path(__file__).resolve().parent
REPO_ROOT = AUTO_DIR.parent
CONFIG_PATH = AUTO_DIR / "config" / "models.json"

MOCK_RESPONSE = """\
[MOCK RESPONSE — executor running in mock mode]

This is a placeholder response produced by automation/executor.py in mock mode.
Set LUMEN_EXECUTOR=live (and configure API keys) to run against a real model.

Structure Design sections would appear here:
- Problem Restatement
- Scope Boundary
- Constraints Analysis
- Data Model / State
- Component Breakdown
- Dependencies
- Open Questions
- Execution Notes
"""


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _resolve_model_id(key_or_id: str) -> str:
    """Resolve a model key (e.g. 'sonnet') or bare model ID to a concrete model ID."""
    cfg = _load_config()
    models = cfg.get("models", {})
    if key_or_id in models:
        return models[key_or_id]["model_id"]
    return key_or_id


def _load_call_params(model_id: str) -> dict:
    """Return call parameters for model_id from config, with safe defaults."""
    cfg = _load_config()
    for entry in cfg.get("models", {}).values():
        if entry.get("model_id") == model_id:
            return entry.get("call_params", {"temperature": 0.0, "max_tokens": 4096})
    return {"temperature": 0.0, "max_tokens": 4096}


def _executor_mode() -> str:
    """Return the active executor mode from the environment (default: live)."""
    return os.environ.get("LUMEN_EXECUTOR", "live").lower()


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def call(prompt: str, *, model_id: str, mode: str | None = None) -> str:
    """Submit *prompt* to *model_id* and return the response text.

    Args:
        prompt:   The full prompt string.
        model_id: Resolved model ID (e.g. "claude-sonnet-4-6") or key ("sonnet").
        mode:     Execution mode override. If None, reads LUMEN_EXECUTOR env var.

    Returns:
        Response text as a string.
    """
    resolved_id = _resolve_model_id(model_id)
    active_mode = mode or _executor_mode()

    if active_mode == "mock":
        return _call_mock(prompt, resolved_id)
    if active_mode == "manual":
        return _call_manual(prompt, resolved_id)
    if active_mode == "live":
        return _call_live(prompt, resolved_id)

    raise ValueError(
        f"Unknown executor mode: '{active_mode}'. "
        "Expected 'live', 'mock', or 'manual'."
    )


# ---------------------------------------------------------------------------
# Mode implementations
# ---------------------------------------------------------------------------


def _call_mock(prompt: str, model_id: str) -> str:
    """Return a canned stub response without making any API call."""
    lines = [
        MOCK_RESPONSE.strip(),
        "",
        f"[Prompt length: {len(prompt)} chars | Model: {model_id}]",
    ]
    return "\n".join(lines)


def _call_manual(prompt: str, model_id: str) -> str:
    """Print the prompt and read the response from stdin."""
    separator = "=" * 72
    print(f"\n{separator}", file=sys.stderr)
    print(f"MANUAL EXECUTION — Model: {model_id}", file=sys.stderr)
    print(separator, file=sys.stderr)
    print(prompt, file=sys.stderr)
    print(separator, file=sys.stderr)
    print("Paste the model response below. Enter a line containing only", file=sys.stderr)
    print("'END' to finish, or press Ctrl+D / Ctrl+Z to submit.", file=sys.stderr)
    print(separator, file=sys.stderr)

    lines: list[str] = []
    try:
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
    except EOFError:
        pass

    return "\n".join(lines)


def _call_live(prompt: str, model_id: str) -> str:
    """Submit prompt via a live API call.

    Tries src/utils/llm_client.py first (repo's constrained client).
    Falls back to direct API calls if the package is not importable.
    """
    params = _load_call_params(model_id)
    _maybe_load_dotenv()

    try:
        return _call_via_repo_client(prompt, model_id, params)
    except (ImportError, ModuleNotFoundError):
        pass

    if model_id.startswith("claude-"):
        return _call_anthropic_direct(prompt, model_id, params)
    if (
        model_id.startswith("gpt-")
        or model_id.startswith("o1")
        or model_id.startswith("o3")
        or model_id.startswith("o4-")
        or model_id.startswith("codex")
    ):
        return _call_openai_direct(prompt, model_id, params)

    raise ValueError(
        f"Unknown model family: '{model_id}'. "
        "Expected claude-*, gpt-*, o1, o3, o4-*, or codex*."
    )


def _call_via_repo_client(prompt: str, model_id: str, params: dict) -> str:
    """Delegate to src/utils/llm_client.py."""
    src_path = str(REPO_ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from utils.llm_client import call as _llm_call  # type: ignore[import]
    return _llm_call(prompt, model=model_id, temperature=params.get("temperature", 0.0))


def _call_anthropic_direct(prompt: str, model_id: str, params: dict) -> str:
    """Direct Anthropic Messages API call."""
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
        model=model_id,
        max_tokens=params.get("max_tokens", 4096),
        temperature=params.get("temperature", 0.0),
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _call_openai_direct(prompt: str, model_id: str, params: dict) -> str:
    """Direct OpenAI Chat Completions API call."""
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
        model=model_id,
        max_completion_tokens=params.get("max_tokens", 4096),
        temperature=params.get("temperature", 0.0),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def _maybe_load_dotenv() -> None:
    """Load API keys from .env if not already in environment."""
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"):
        return
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


# ---------------------------------------------------------------------------
# CLI (for direct testing)
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="executor",
        description="Lumen executor — submit a prompt to a model (or mock).",
    )
    p.add_argument(
        "--model", required=True,
        help="Model key (sonnet/opus/gpt54/codex) or direct model ID",
    )
    p.add_argument(
        "--mode", choices=["live", "mock", "manual"], default=None,
        help="Execution mode (overrides LUMEN_EXECUTOR env var; default: live)",
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--prompt-file", metavar="FILE",
        help="Path to a file containing the prompt text",
    )
    group.add_argument(
        "--prompt", metavar="TEXT",
        help="Inline prompt text",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    model_id = _resolve_model_id(args.model)

    if args.prompt_file:
        path = Path(args.prompt_file)
        if not path.exists():
            print(f"ERROR: File not found: {path}", file=sys.stderr)
            sys.exit(1)
        prompt = path.read_text(encoding="utf-8")
    else:
        prompt = args.prompt

    result = call(prompt, model_id=model_id, mode=args.mode)
    print(result)


if __name__ == "__main__":
    main()
