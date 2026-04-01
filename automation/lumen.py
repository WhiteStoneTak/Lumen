"""lumen.py — Orchestration controller for the Lumen research workflow.

State machine:
    intake → planning → prompt_synthesis → execution → result_ingest
           → review → next_task → handoff (optional)

Commands:
    init      Start or reset a session
    status    Show current session state and available state files
    plan      Render the structure-design prompt (→ planning phase)
    prompt    Render the execution-prompt synthesis prompt (→ prompt_synthesis)
    ingest    Save an execution result from an external file (→ result_ingest)
    review    Render the execution-result review prompt (→ review)
    next      Render the next-task generation prompt (→ intake)
    handoff   Render the context handoff-summary prompt (→ handoff)

Each command:
    1. Loads current session state
    2. Loads the relevant template
    3. Renders it with context from state files
    4. Saves the rendered prompt to automation/state/<command>_prompt.md
    5. Archives to automation/history/<session_id>/<ts>_<file>
    6. Advances the session phase
    7. Prints the rendered prompt to stdout (copy-paste ready)

With --execute:
    The rendered prompt is submitted to the configured model via executor.py,
    the response is saved as the corresponding output artifact, and the phase
    advances one step further.

Executor mode:
    Set LUMEN_EXECUTOR=mock for local testing without API keys.
    Set LUMEN_EXECUTOR=manual for human-in-loop (paste response at terminal).
    Default (LUMEN_EXECUTOR=live or unset) makes real API calls.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
AUTO_DIR = Path(__file__).resolve().parent
STATE_DIR = AUTO_DIR / "state"
HISTORY_DIR = AUTO_DIR / "history"
TEMPLATES_DIR = AUTO_DIR / "templates"
SCHEMAS_DIR = AUTO_DIR / "schemas"
CONFIG_DIR = AUTO_DIR / "config"

# ---------------------------------------------------------------------------
# Workflow phases (ordered for reference; state machine is enforced by convention)
# ---------------------------------------------------------------------------

PHASES: list[str] = [
    "intake",
    "planning",
    "prompt_synthesis",
    "execution",
    "result_ingest",
    "review",
    "next_task",
    "handoff",
]

# ---------------------------------------------------------------------------
# State I/O
# ---------------------------------------------------------------------------


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def save_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


def session_path() -> Path:
    return STATE_DIR / "session.json"


def load_session() -> dict[str, Any]:
    return load_json(session_path())


def save_session(session: dict[str, Any]) -> None:
    session["last_updated"] = datetime.now(tz=timezone.utc).isoformat()
    save_json(session_path(), session)


def require_session() -> dict[str, Any]:
    """Load the active session or exit with a clear message."""
    s = load_session()
    if not s:
        raise SystemExit("No active session. Run: python automation/lumen.py init")
    return s


def new_session_id() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")


def archive(session_id: str, filename: str, content: str) -> Path:
    """Write content to automation/history/<session_id>/<ts>_<filename>."""
    dest_dir = HISTORY_DIR / session_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = dest_dir / f"{ts}_{filename}"
    dest.write_text(content, encoding="utf-8")
    return dest


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------


def load_template(name: str) -> str:
    path = TEMPLATES_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(
            f"Template not found: {path}\n"
            f"Expected one of: {[p.stem for p in TEMPLATES_DIR.glob('*.md')]}"
        )
    return path.read_text(encoding="utf-8")


def render(template: str, context: dict[str, str]) -> str:
    """Replace {{key}} placeholders with values.

    Uses str.replace() per key to avoid conflicts with literal braces in content
    (e.g., JSON examples or code blocks in task briefs).
    """
    result = template
    for key, value in context.items():
        result = result.replace("{" + key + "}", value)
    return result


# ---------------------------------------------------------------------------
# Model routing
# ---------------------------------------------------------------------------


def load_model_config() -> dict[str, Any]:
    return load_json(CONFIG_DIR / "models.json")


def resolve_model_id(key_or_id: str | None, cfg: dict[str, Any]) -> str | None:
    """Resolve a model key or bare model ID to a concrete model ID string."""
    if key_or_id is None:
        return None
    models = cfg.get("models", {})
    if key_or_id in models:
        return models[key_or_id]["model_id"]
    return key_or_id  # treat as a direct model ID


def default_model(role: str, cfg: dict[str, Any]) -> str | None:
    """Return the model ID for a named role (planner / synthesizer / executor)."""
    key = cfg.get("defaults", {}).get(role)
    return resolve_model_id(key, cfg)


# ---------------------------------------------------------------------------
# Context helpers
# ---------------------------------------------------------------------------


def repo_context() -> str:
    return "\n".join([
        f"Repository: {REPO_ROOT.name}",
        "Protocol: docs/experimental-protocol.md (binding; superseded only by design-constitution)",
        "Dataset manifest: data/dataset/functions_manifest.json",
        "Candidate tracker: data/dataset/candidates.json",
        "LLM client: src/utils/llm_client.py (Anthropic + OpenAI)",
        "Experiment runs: results/runs/{run_id}/",
        "Screening helpers: scripts/screen.sh, Makefile",
    ])


def extract_title(brief_path: Path) -> str:
    """Extract the first H1 heading or first non-empty line from a task brief."""
    if not brief_path.exists():
        return "unnamed"
    for line in brief_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
        if stripped and not stripped.startswith("#"):
            return stripped[:60]
    return "unnamed"


def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def today() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Executor bridge
# ---------------------------------------------------------------------------


def execute_prompt(prompt: str, model_id: str) -> str:
    """Submit prompt to model via automation/executor.py."""
    if str(AUTO_DIR) not in sys.path:
        sys.path.insert(0, str(AUTO_DIR))
    import executor as _exec  # type: ignore[import]
    return _exec.call(prompt, model_id=model_id)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> None:
    existing = load_session()

    if existing and not getattr(args, "force", False):
        print(f"Active session : {existing['session_id']}")
        print(f"Phase          : {existing['phase']}")
        print("Use --force to archive this session and start fresh.")
        return

    if existing:
        sid = existing["session_id"]
        for f in STATE_DIR.glob("*.md"):
            archive(sid, f.name, f.read_text(encoding="utf-8"))
        archive(sid, "session.json", json.dumps(existing, indent=2))
        print(f"Archived session {sid} → automation/history/{sid}/")

    sid = new_session_id()
    session: dict[str, Any] = {
        "session_id": sid,
        "created": now_iso(),
        "last_updated": now_iso(),
        "phase": "intake",
        "task_history": [],
    }
    save_session(session)

    brief_path = STATE_DIR / "task_brief.md"
    if not brief_path.exists():
        schema = load_json(SCHEMAS_DIR / "task_brief.json")
        save_text(brief_path, schema.get("blank_template", "# Task Brief\n\n"))

    print(f"Session initialized : {sid}")
    print(f"Edit task brief     : automation/state/task_brief.md")
    print(f"Then run            : python automation/lumen.py plan")


def cmd_status(args: argparse.Namespace) -> None:
    session = load_session()
    if not session:
        print("No active session. Run: python automation/lumen.py init")
        return

    history = session.get("task_history", [])
    print(f"Session  : {session['session_id']}")
    print(f"Phase    : {session['phase']}")
    print(f"Updated  : {session.get('last_updated', '?')}")
    print(f"Tasks    : {len(history)} completed")
    if history:
        last = history[-1]
        print(f"Last     : {last.get('name', '?')}  ({last.get('completed', '?')[:10]})")

    state_mds = sorted(
        f.name for f in STATE_DIR.glob("*.md") if f.stat().st_size > 0
    )
    if state_mds:
        print(f"State    : {', '.join(state_mds)}")

    print()
    print("Commands : plan → prompt → ingest FILE → review → next → handoff")


def cmd_plan(args: argparse.Namespace) -> None:
    session = require_session()
    template = load_template("plan")

    ctx: dict[str, str] = {
        "task_brief": load_text(STATE_DIR / "task_brief.md")
            or "(no task brief — edit automation/state/task_brief.md)",
        "repo_context": repo_context(),
        "session_id": session["session_id"],
        "date": today(),
        "constraints": load_text(STATE_DIR / "constraints.md")
            or "(none yet — add to automation/state/constraints.md)",
        "previous_decisions": load_text(STATE_DIR / "previous_decisions.md")
            or "(none recorded)",
    }
    rendered = render(template, ctx)
    save_text(STATE_DIR / "plan_prompt.md", rendered)
    archive(session["session_id"], "plan_prompt.md", rendered)
    session["phase"] = "planning"
    save_session(session)

    if getattr(args, "execute", False):
        cfg = load_model_config()
        model_id = (
            resolve_model_id(getattr(args, "model", None), cfg)
            or default_model("planner", cfg)
        )
        if not model_id:
            _die("No planner model configured. Set defaults.planner in models.json or pass --model.")
        _info(f"Submitting to planner model: {model_id}")
        result = execute_prompt(rendered, model_id)
        save_text(STATE_DIR / "structure_design.md", result)
        archive(session["session_id"], "structure_design.md", result)
        session["phase"] = "prompt_synthesis"
        save_session(session)
        print(result)
        _info("Saved → automation/state/structure_design.md")
    else:
        print(rendered)
        _info("Saved → automation/state/plan_prompt.md")
        _info("Pass --execute to submit to the planner model.")


def cmd_prompt(args: argparse.Namespace) -> None:
    session = require_session()
    template = load_template("prompt")
    cfg = load_model_config()

    model_key = getattr(args, "model", None) or cfg.get("defaults", {}).get("executor", "sonnet")
    model_id = resolve_model_id(model_key, cfg) or model_key
    model_info = cfg.get("models", {}).get(model_key, {})
    model_description = model_info.get("description", model_id)
    model_strengths = ", ".join(model_info.get("strengths", ["general code generation"]))

    ctx: dict[str, str] = {
        "task_brief": load_text(STATE_DIR / "task_brief.md")
            or "(no task brief — run `init` then edit automation/state/task_brief.md)",
        "structure_design": load_text(STATE_DIR / "structure_design.md")
            or "(no structure design — run `plan` first)",
        "target_model": model_id,
        "target_model_key": model_key,
        "model_description": model_description,
        "model_strengths": model_strengths,
        "repo_context": repo_context(),
        "date": today(),
    }
    rendered = render(template, ctx)
    save_text(STATE_DIR / "prompt_prompt.md", rendered)
    archive(session["session_id"], "prompt_prompt.md", rendered)
    session["phase"] = "prompt_synthesis"
    save_session(session)

    if getattr(args, "execute", False):
        synth_id = default_model("synthesizer", cfg)
        if not synth_id:
            _die("No synthesizer model configured. Set defaults.synthesizer in models.json.")
        _info(f"Submitting to synthesizer model: {synth_id}")
        result = execute_prompt(rendered, synth_id)
        save_text(STATE_DIR / "execution_prompt.md", result)
        archive(session["session_id"], "execution_prompt.md", result)
        session["phase"] = "execution"
        save_session(session)
        print(result)
        _info("Saved → automation/state/execution_prompt.md")
    else:
        print(rendered)
        _info("Saved → automation/state/prompt_prompt.md")
        _info("Pass --execute to synthesize the execution prompt via a model.")


def cmd_ingest(args: argparse.Namespace) -> None:
    session = require_session()
    source = Path(args.file)
    if not source.exists():
        _die(f"File not found: {source}")

    content = source.read_text(encoding="utf-8")
    save_text(STATE_DIR / "execution_result.md", content)
    archive(session["session_id"], "execution_result.md", content)
    session["phase"] = "result_ingest"
    save_session(session)

    print(f"Ingested: {source} → automation/state/execution_result.md")
    print("Next: python automation/lumen.py review")


def cmd_review(args: argparse.Namespace) -> None:
    session = require_session()
    template = load_template("review")

    ctx: dict[str, str] = {
        "execution_prompt": load_text(STATE_DIR / "execution_prompt.md")
            or "(no execution prompt on record — was prompt run and saved?)",
        "execution_result": load_text(STATE_DIR / "execution_result.md")
            or "(no execution result — run `ingest FILE` first)",
        "task_brief": load_text(STATE_DIR / "task_brief.md")
            or "(no task brief)",
        "repo_context": repo_context(),
        "constraints": load_text(STATE_DIR / "constraints.md")
            or "(none recorded)",
        "date": today(),
        "session_id": session["session_id"],
    }
    rendered = render(template, ctx)
    save_text(STATE_DIR / "review_prompt.md", rendered)
    archive(session["session_id"], "review_prompt.md", rendered)
    session["phase"] = "review"
    save_session(session)

    if getattr(args, "execute", False):
        cfg = load_model_config()
        model_id = (
            resolve_model_id(getattr(args, "model", None), cfg)
            or default_model("planner", cfg)
        )
        if not model_id:
            _die("No planner model configured. Set defaults.planner in models.json or pass --model.")
        _info(f"Submitting to model: {model_id}")
        result = execute_prompt(rendered, model_id)
        save_text(STATE_DIR / "review.md", result)
        archive(session["session_id"], "review.md", result)
        session["phase"] = "next_task"
        save_session(session)
        print(result)
        _info("Saved → automation/state/review.md")
        _info("Next: python automation/lumen.py next")
    else:
        print(rendered)
        _info("Saved → automation/state/review_prompt.md")
        _info("Pass --execute to submit to the planner model.")


def cmd_next(args: argparse.Namespace) -> None:
    session = require_session()
    template = load_template("next")

    ctx: dict[str, str] = {
        "review": load_text(STATE_DIR / "review.md")
            or load_text(STATE_DIR / "execution_result.md")
            or "(no review available — run `review` first)",
        "task_brief": load_text(STATE_DIR / "task_brief.md")
            or "(no task brief)",
        "structure_design": load_text(STATE_DIR / "structure_design.md")
            or "(no structure design)",
        "constraints": load_text(STATE_DIR / "constraints.md")
            or "(none recorded)",
        "repo_context": repo_context(),
        "date": today(),
        "task_history_count": str(len(session.get("task_history", []))),
    }
    rendered = render(template, ctx)
    save_text(STATE_DIR / "next_prompt.md", rendered)
    archive(session["session_id"], "next_prompt.md", rendered)
    session["phase"] = "next_task"
    save_session(session)

    if getattr(args, "execute", False):
        cfg = load_model_config()
        model_id = (
            resolve_model_id(getattr(args, "model", None), cfg)
            or default_model("planner", cfg)
        )
        if not model_id:
            _die("No planner model configured. Set defaults.planner in models.json or pass --model.")
        _info(f"Submitting to model: {model_id}")
        result = execute_prompt(rendered, model_id)
        save_text(STATE_DIR / "next_steps.md", result)
        archive(session["session_id"], "next_steps.md", result)
        # Record completed task in history
        session.setdefault("task_history", []).append({
            "name": extract_title(STATE_DIR / "task_brief.md"),
            "completed": now_iso(),
        })
        session["phase"] = "intake"
        save_session(session)
        print(result)
        _info("Saved → automation/state/next_steps.md")
        _info("Update automation/state/task_brief.md with the proposed next task, then run `plan`.")
    else:
        print(rendered)
        _info("Saved → automation/state/next_prompt.md")
        _info("Pass --execute to submit to the planner model.")


def cmd_handoff(args: argparse.Namespace) -> None:
    session = require_session()
    template = load_template("handoff")

    history_dir = HISTORY_DIR / session["session_id"]
    artifact_count = len(list(history_dir.glob("*"))) if history_dir.exists() else 0

    ctx: dict[str, str] = {
        "session_id": session["session_id"],
        "created": session.get("created", "?"),
        "date": today(),
        "current_phase": session.get("phase", "?"),
        "task_history_count": str(len(session.get("task_history", []))),
        "history_artifact_count": str(artifact_count),
        "task_brief": load_text(STATE_DIR / "task_brief.md")
            or "(no task brief)",
        "structure_design": load_text(STATE_DIR / "structure_design.md")
            or "(no structure design)",
        "execution_result": load_text(STATE_DIR / "execution_result.md")
            or "(no execution result)",
        "next_steps": load_text(STATE_DIR / "next_steps.md")
            or "(no next steps generated yet)",
        "constraints": load_text(STATE_DIR / "constraints.md")
            or "(none explicitly recorded)",
        "repo_context": repo_context(),
    }
    rendered = render(template, ctx)
    save_text(STATE_DIR / "handoff_prompt.md", rendered)
    archive(session["session_id"], "handoff_prompt.md", rendered)
    session["phase"] = "handoff"
    save_session(session)

    if getattr(args, "execute", False):
        cfg = load_model_config()
        model_id = (
            resolve_model_id(getattr(args, "model", None), cfg)
            or default_model("planner", cfg)
        )
        if not model_id:
            _die("No planner model configured. Set defaults.planner in models.json or pass --model.")
        _info(f"Submitting to model: {model_id}")
        result = execute_prompt(rendered, model_id)
        save_text(STATE_DIR / "handoff_summary.md", result)
        archive(session["session_id"], "handoff_summary.md", result)
        print(result)
        _info("Saved → automation/state/handoff_summary.md")
        _info("Start a fresh session: python automation/lumen.py init --force")
    else:
        print(rendered)
        _info("Saved → automation/state/handoff_prompt.md")
        _info("Pass --execute to generate the handoff summary via a model.")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _info(msg: str) -> None:
    print(f"[{msg}]", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lumen",
        description=(
            "Lumen orchestration controller — structure-driven research workflow.\n\n"
            "Loop: init → plan → prompt → ingest FILE → review → next → (repeat)\n"
            "      handoff generates a fresh-context summary at any point."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", required=True)

    # init
    p_init = sub.add_parser("init", help="Start or reset a session")
    p_init.add_argument("--force", action="store_true",
                        help="Archive the current session and start fresh")

    # status
    sub.add_parser("status", help="Show current session state")

    # plan
    p_plan = sub.add_parser("plan", help="Render structure-design prompt (planning phase)")
    p_plan.add_argument("--execute", action="store_true",
                        help="Submit to the planner model (requires API key)")
    p_plan.add_argument("--model", default=None,
                        help="Model key (sonnet/opus/gpt54/codex) or bare model ID")

    # prompt
    p_prompt = sub.add_parser("prompt", help="Render execution-prompt synthesis prompt")
    p_prompt.add_argument("--execute", action="store_true",
                          help="Submit to the synthesizer model")
    p_prompt.add_argument("--model", default=None,
                          help="Target executor model key or ID")

    # ingest
    p_ingest = sub.add_parser("ingest", help="Save an execution result file into state")
    p_ingest.add_argument("file", help="Path to the execution result file")

    # review
    p_review = sub.add_parser("review", help="Render execution-result review prompt")
    p_review.add_argument("--execute", action="store_true",
                          help="Submit to the planner model")
    p_review.add_argument("--model", default=None,
                          help="Model key or bare model ID")

    # next
    p_next = sub.add_parser("next", help="Render next-task generation prompt")
    p_next.add_argument("--execute", action="store_true",
                        help="Submit to the planner model")
    p_next.add_argument("--model", default=None,
                        help="Model key or bare model ID")

    # handoff
    p_handoff = sub.add_parser("handoff", help="Render context handoff-summary prompt")
    p_handoff.add_argument("--execute", action="store_true",
                           help="Submit to the planner model")
    p_handoff.add_argument("--model", default=None,
                           help="Model key or bare model ID")

    return p


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    dispatch = {
        "init": cmd_init,
        "status": cmd_status,
        "plan": cmd_plan,
        "prompt": cmd_prompt,
        "ingest": cmd_ingest,
        "review": cmd_review,
        "next": cmd_next,
        "handoff": cmd_handoff,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
