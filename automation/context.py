"""context.py — State-aware execution context builder for the Lumen automation layer.

Assembles all relevant state files into a coherent ExecutionContext that
can be passed to an executor backend. This makes execution deterministic
and reconstructible from persisted files alone — no implicit chat context.

Usage:
    from context import build_from_state, ExecutionContext
    ctx = build_from_state(STATE_DIR, model_id="claude-sonnet-4-6", backend="anthropic_direct")
    # ctx.execution_prompt contains the full prompt to submit
    # ctx.max_tokens is the correct budget for this phase
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUTO_DIR = Path(__file__).resolve().parent
CONFIG_PATH = AUTO_DIR / "config" / "models.json"

# Default token budgets by workflow phase.
# Override by adding a "token_budgets" section to models.json.
_DEFAULT_TOKEN_BUDGETS: dict[str, int] = {
    "intake": 4096,
    "planning": 8192,
    "prompt_synthesis": 8192,
    "execution": 8192,
    "result_ingest": 4096,
    "review": 8192,
    "next_task": 4096,
    "handoff": 8192,
    "default": 4096,
}


@dataclass
class ExecutionContext:
    """All context needed to execute a task deterministically.

    Every field is sourced from a persisted file.  No field is inferred
    from conversation history or implicit state.
    """

    # Core task artifacts
    task_brief: str            # state/task_brief.md
    execution_prompt: str      # state/execution_prompt.md (primary input to executor)

    # Supporting context (empty string when file not yet generated)
    structure_design: str      # state/structure_design.md
    constraints: str           # state/constraints.md
    previous_decisions: str    # state/previous_decisions.md

    # Session metadata
    session_id: str
    phase: str

    # Routing
    model_id: str
    backend: str

    # Token budget for this execution phase (sourced from config)
    max_tokens: int
    temperature: float

    # Assembly timestamp
    assembled_at: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )


def build_from_state(
    state_dir: Path,
    model_id: str,
    backend: str,
    *,
    temperature: float = 0.0,
    max_tokens_override: int | None = None,
) -> ExecutionContext:
    """Assemble an ExecutionContext from persisted state files.

    Never raises if files are missing — returns empty strings for optional
    files that do not yet exist.

    Args:
        state_dir:           Path to automation/state/
        model_id:            Resolved model ID (e.g. "claude-sonnet-4-6")
        backend:             Backend key (e.g. "anthropic_direct")
        temperature:         Sampling temperature (default: 0.0)
        max_tokens_override: If set, overrides config-derived token budget.
    """

    def _read(name: str) -> str:
        p = state_dir / name
        return p.read_text(encoding="utf-8") if p.exists() else ""

    session_data: dict[str, Any] = {}
    session_path = state_dir / "session.json"
    if session_path.exists():
        with session_path.open(encoding="utf-8") as f:
            session_data = json.load(f)

    phase = session_data.get("phase", "default")
    max_tokens = max_tokens_override or _resolve_token_budget(phase)

    return ExecutionContext(
        task_brief=_read("task_brief.md"),
        execution_prompt=_read("execution_prompt.md"),
        structure_design=_read("structure_design.md"),
        constraints=_read("constraints.md"),
        previous_decisions=_read("previous_decisions.md"),
        session_id=session_data.get("session_id", "unknown"),
        phase=phase,
        model_id=model_id,
        backend=backend,
        max_tokens=max_tokens,
        temperature=temperature,
    )


def _resolve_token_budget(phase: str) -> int:
    """Return the token budget for *phase*, reading models.json if available."""
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open(encoding="utf-8") as f:
            cfg = json.load(f)
        budgets: dict[str, int] = cfg.get("token_budgets", {})
        if phase in budgets:
            return budgets[phase]
        if "default" in budgets:
            return budgets["default"]
    return _DEFAULT_TOKEN_BUDGETS.get(phase, _DEFAULT_TOKEN_BUDGETS["default"])


def to_dict(ctx: ExecutionContext) -> dict[str, Any]:
    """Serialize ExecutionContext to a dict suitable for logging / archiving.

    Truncates large text fields to lengths only — does not include full
    prompt content, which can be large.
    """
    return {
        "session_id": ctx.session_id,
        "phase": ctx.phase,
        "model_id": ctx.model_id,
        "backend": ctx.backend,
        "max_tokens": ctx.max_tokens,
        "temperature": ctx.temperature,
        "assembled_at": ctx.assembled_at,
        "task_brief_chars": len(ctx.task_brief),
        "execution_prompt_chars": len(ctx.execution_prompt),
        "structure_design_chars": len(ctx.structure_design),
        "constraints_present": bool(ctx.constraints.strip()),
        "previous_decisions_present": bool(ctx.previous_decisions.strip()),
    }


def to_json(ctx: ExecutionContext) -> str:
    return json.dumps(to_dict(ctx), indent=2, ensure_ascii=False)
