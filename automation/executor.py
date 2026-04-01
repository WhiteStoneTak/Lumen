"""executor.py — Backend orchestration layer for the Lumen automation executor.

This module is the sole call-site for LLM API calls within the automation
layer.  All other modules call executor.call() or executor.execute_with_context()
and never import provider SDKs directly.

Backend selection
-----------------
Set LUMEN_BACKEND env var (or pass backend= explicitly):

    anthropic_direct   Direct Anthropic Messages API.  Requires anthropic SDK + ANTHROPIC_API_KEY.
    openai_direct      Direct OpenAI Chat Completions API.  Requires openai SDK + OPENAI_API_KEY.
    claude_code_cli    Invokes the `claude` CLI as a subprocess.  Requires `claude` in PATH.
    codex_cli          Invokes a codex CLI as a subprocess.  Requires codex tool in PATH.
    mock               Canned stub response.  No dependencies.  For CI / local testing.
    manual             Prints the prompt; reads response from stdin.  Human-in-loop.

If LUMEN_BACKEND is not set, the backend is inferred from the model ID:
    claude-*       → anthropic_direct
    gpt-* / o1 / o3 / o4-*  → openai_direct

Backward compatibility
----------------------
LUMEN_EXECUTOR=live      → same as inferred backend
LUMEN_EXECUTOR=mock      → mock backend
LUMEN_EXECUTOR=manual    → manual backend

Token budget
------------
The old src/utils/llm_client.py path (MAX_TOKENS=1024) is intentionally
NOT used here.  That module enforces the study's protocol token constraint
(§8.2) and is inappropriate for planning / synthesis / review outputs.
Automation always uses the direct SDK path with the budget from models.json
(default 8192).

Extension point
---------------
To add a new backend, add a branch in _dispatch() and a helper function.
Do NOT add backend logic to lumen.py.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context import ExecutionContext

AUTO_DIR = Path(__file__).resolve().parent
REPO_ROOT = AUTO_DIR.parent
CONFIG_PATH = AUTO_DIR / "config" / "models.json"

MOCK_RESPONSE = """\
[MOCK RESPONSE — executor running in mock mode]

This is a placeholder response produced by automation/executor.py in mock mode.
Set LUMEN_BACKEND=anthropic_direct (and configure ANTHROPIC_API_KEY) for real calls.

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


class BackendUnavailableError(RuntimeError):
    """Raised when a requested backend is not available in this environment."""


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _resolve_model_id(key_or_id: str) -> str:
    """Resolve a model key (e.g. 'sonnet') or bare model ID to a concrete ID."""
    cfg = _load_config()
    entry = cfg.get("models", {}).get(key_or_id)
    if entry:
        return entry["model_id"]
    return key_or_id


def _load_call_params(model_id: str) -> dict:
    """Return call parameters for model_id from config, with safe defaults.

    Always returns a max_tokens from models.json (default 4096).
    Never routes through src/utils/llm_client.py (MAX_TOKENS=1024).
    """
    cfg = _load_config()
    for entry in cfg.get("models", {}).values():
        if entry.get("model_id") == model_id:
            return entry.get("call_params", {"temperature": 0.0, "max_tokens": 4096})
    return {"temperature": 0.0, "max_tokens": 4096}


def _infer_backend(model_id: str) -> str:
    """Infer the appropriate backend from the model ID."""
    if model_id.startswith("claude-"):
        return "anthropic_direct"
    if (
        model_id.startswith("gpt-")
        or model_id.startswith("o1")
        or model_id.startswith("o3")
        or model_id.startswith("o4-")
        or model_id.startswith("codex")
    ):
        return "openai_direct"
    return "anthropic_direct"  # safe default


def _active_backend(model_id: str, backend: str | None) -> str:
    """Resolve the backend to use, considering env vars and backward-compat."""
    if backend:
        return backend

    # Check new env var first
    env_backend = os.environ.get("LUMEN_BACKEND", "").strip().lower()
    if env_backend:
        return env_backend

    # Backward-compat: LUMEN_EXECUTOR=mock|manual|live
    legacy = os.environ.get("LUMEN_EXECUTOR", "").strip().lower()
    if legacy == "mock":
        return "mock"
    if legacy == "manual":
        return "manual"
    # "live" or unset → infer from model

    return _infer_backend(model_id)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def call(prompt: str, *, model_id: str, mode: str | None = None) -> str:
    """Submit *prompt* to *model_id* and return the response text.

    This is the simple string-in / string-out interface used by
    lumen.py's planning and synthesis commands (plan, prompt, review,
    next, handoff).

    Args:
        prompt:   The full prompt string.
        model_id: Model key (e.g. "sonnet") or bare model ID.
        mode:     Legacy mode override ("mock" / "manual" / "live").
                  New code should set LUMEN_BACKEND instead.

    Returns:
        Response text as a string.
    """
    resolved_id = _resolve_model_id(model_id)
    # mode= is the legacy --mode / LUMEN_EXECUTOR path; map to backend
    backend = _active_backend(resolved_id, backend=mode if mode in ("mock", "manual") else None)
    return _dispatch(prompt, resolved_id, backend)


def execute_with_context(ctx: "ExecutionContext") -> "result_module.ExecutionResult":
    """Execute a task using a pre-assembled ExecutionContext.

    This is the structured interface used by lumen.py's execute command.
    Returns a normalized ExecutionResult regardless of backend.

    The prompt submitted is ctx.execution_prompt (the primary task prompt).
    """
    # Import here to avoid circular dependency at module level
    if str(AUTO_DIR) not in sys.path:
        sys.path.insert(0, str(AUTO_DIR))
    import result as result_module  # type: ignore[import]

    resolved_id = _resolve_model_id(ctx.model_id)
    backend = _active_backend(resolved_id, ctx.backend if ctx.backend != "auto" else None)

    prompt = ctx.execution_prompt
    if not prompt.strip():
        return result_module.normalize(
            "",
            backend=backend,
            model_id=resolved_id,
            error_message="execution_prompt is empty — run `lumen.py prompt` first",
        )

    try:
        raw = _dispatch(prompt, resolved_id, backend, max_tokens=ctx.max_tokens)
        return result_module.normalize(raw, backend=backend, model_id=resolved_id)
    except BackendUnavailableError as exc:
        return result_module.normalize(
            "",
            backend=backend,
            model_id=resolved_id,
            error_message=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        return result_module.normalize(
            "",
            backend=backend,
            model_id=resolved_id,
            error_message=f"{type(exc).__name__}: {exc}",
        )


# ---------------------------------------------------------------------------
# Backend dispatch
# ---------------------------------------------------------------------------


def _dispatch(prompt: str, model_id: str, backend: str, max_tokens: int | None = None) -> str:
    """Route to the correct backend implementation."""
    if backend == "mock":
        return _call_mock(prompt, model_id)
    if backend == "manual":
        return _call_manual(prompt, model_id)
    if backend == "anthropic_direct":
        return _call_anthropic_direct(prompt, model_id, max_tokens=max_tokens)
    if backend == "openai_direct":
        return _call_openai_direct(prompt, model_id, max_tokens=max_tokens)
    if backend == "claude_code_cli":
        return _call_claude_code_cli(prompt, model_id)
    if backend == "codex_cli":
        return _call_codex_cli(prompt, model_id)
    # legacy "live" value
    if backend == "live":
        return _dispatch(prompt, model_id, _infer_backend(model_id), max_tokens=max_tokens)
    raise ValueError(
        f"Unknown backend: '{backend}'. "
        "Expected: anthropic_direct, openai_direct, claude_code_cli, "
        "codex_cli, mock, manual."
    )


# ---------------------------------------------------------------------------
# Backend implementations
# ---------------------------------------------------------------------------


def _call_mock(prompt: str, model_id: str) -> str:
    lines = [
        MOCK_RESPONSE.strip(),
        "",
        f"[Prompt length: {len(prompt)} chars | Model: {model_id}]",
    ]
    return "\n".join(lines)


def _call_manual(prompt: str, model_id: str) -> str:
    sep = "=" * 72
    print(f"\n{sep}", file=sys.stderr)
    print(f"MANUAL EXECUTION — Model: {model_id}", file=sys.stderr)
    print(sep, file=sys.stderr)
    print(prompt, file=sys.stderr)
    print(sep, file=sys.stderr)
    print("Paste the model response below.", file=sys.stderr)
    print("Enter a line containing only 'END', or press Ctrl+D to finish.", file=sys.stderr)
    print(sep, file=sys.stderr)
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


def _call_anthropic_direct(
    prompt: str, model_id: str, *, max_tokens: int | None = None
) -> str:
    """Direct Anthropic Messages API call.

    Uses the max_tokens from models.json (default 4096).
    Intentionally does NOT route through src/utils/llm_client.py,
    which enforces the study protocol's MAX_TOKENS=1024 constraint.
    """
    try:
        import anthropic
    except ImportError as exc:
        raise ImportError(
            "The 'anthropic' package is required. Install with: pip install anthropic"
        ) from exc

    _maybe_load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set.")

    params = _load_call_params(model_id)
    effective_max_tokens = max_tokens or params.get("max_tokens", 4096)
    temperature = params.get("temperature", 0.0)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model_id,
        max_tokens=effective_max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _call_openai_direct(
    prompt: str, model_id: str, *, max_tokens: int | None = None
) -> str:
    """Direct OpenAI Chat Completions API call.

    Uses the max_tokens from models.json (default 4096).
    Intentionally does NOT route through src/utils/llm_client.py.
    """
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError(
            "The 'openai' package is required. Install with: pip install openai"
        ) from exc

    _maybe_load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set.")

    params = _load_call_params(model_id)
    effective_max_tokens = max_tokens or params.get("max_tokens", 4096)
    temperature = params.get("temperature", 0.0)

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model_id,
        max_completion_tokens=effective_max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def _call_claude_code_cli(prompt: str, model_id: str) -> str:
    """Execute prompt via the `claude` CLI (Claude Code).

    Requires the `claude` CLI to be installed and in PATH.
    Install: https://claude.ai/code

    Raises BackendUnavailableError if the CLI is not found.
    """
    cli = shutil.which("claude")
    if not cli:
        raise BackendUnavailableError(
            "claude_code_cli backend requires the `claude` CLI to be in PATH. "
            "Install Claude Code: https://claude.ai/code"
        )
    # Write prompt to a temp file to avoid shell-quoting issues
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(prompt)
        tmp_path = f.name
    try:
        result = subprocess.run(
            [cli, "--print", "--input-file", tmp_path, "--model", model_id],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"claude CLI exited {result.returncode}: {result.stderr[:500]}"
            )
        return result.stdout
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _call_codex_cli(prompt: str, model_id: str) -> str:
    """Execute prompt via a codex CLI tool.

    Looks for 'codex' or 'openai-codex' in PATH.
    Raises BackendUnavailableError if neither is found.
    """
    cli = shutil.which("codex") or shutil.which("openai-codex")
    if not cli:
        raise BackendUnavailableError(
            "codex_cli backend requires a codex CLI tool in PATH. "
            "Neither 'codex' nor 'openai-codex' was found."
        )
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(prompt)
        tmp_path = f.name
    try:
        result = subprocess.run(
            [cli, "--quiet", tmp_path],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"codex CLI exited {result.returncode}: {result.stderr[:500]}"
            )
        return result.stdout
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _maybe_load_dotenv() -> None:
    """Source .env from repo root into os.environ if keys are not yet set."""
    if os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("OPENAI_API_KEY"):
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
        description=(
            "Lumen executor — submit a prompt to a model backend.\n\n"
            "Backends: anthropic_direct, openai_direct, claude_code_cli, "
            "codex_cli, mock, manual"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--model", required=True,
        help="Model key (sonnet/opus/gpt54/codex) or direct model ID",
    )
    p.add_argument(
        "--backend", default=None,
        choices=["anthropic_direct", "openai_direct", "claude_code_cli",
                 "codex_cli", "mock", "manual"],
        help="Backend to use (default: infer from model)",
    )
    # Legacy --mode for backward compatibility
    p.add_argument(
        "--mode", default=None,
        choices=["live", "mock", "manual"],
        help="Legacy mode flag (use --backend instead)",
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt-file", metavar="FILE",
                       help="Path to a file containing the prompt text")
    group.add_argument("--prompt", metavar="TEXT", help="Inline prompt text")
    return p


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    model_id = _resolve_model_id(args.model)
    backend = args.backend or (
        "mock" if args.mode == "mock" else
        "manual" if args.mode == "manual" else
        None
    )

    if args.prompt_file:
        path = Path(args.prompt_file)
        if not path.exists():
            print(f"ERROR: File not found: {path}", file=sys.stderr)
            sys.exit(1)
        prompt = path.read_text(encoding="utf-8")
    else:
        prompt = args.prompt

    try:
        result = _dispatch(prompt, model_id, _active_backend(model_id, backend))
        print(result)
    except BackendUnavailableError as exc:
        print(f"ERROR: Backend unavailable — {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
