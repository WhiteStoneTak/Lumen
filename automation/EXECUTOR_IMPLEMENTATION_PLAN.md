# Executor Implementation Plan

**Date:** 2026-04-01
**Scope:** Production-ready state-aware executor layer for the Lumen automation scaffold

---

## 1. Current Executor Architecture

### What exists

```
lumen.py  →  execute_prompt(prompt, model_id) → str
                  ↓
            executor.call(prompt, model_id, mode)
                  ↓
            mode dispatch:
              mock    → canned string
              manual  → stdin read
              live    → _call_via_repo_client() ← BUG (see below)
                           if ImportError → _call_anthropic_direct()
                                            _call_openai_direct()
```

### Identified problems

| # | Problem | Severity | Fix |
|---|---------|----------|-----|
| 1 | `_call_via_repo_client` routes through `src/utils/llm_client.py` which hardcodes `MAX_TOKENS=1024`. This is the experiment's protocol constraint, NOT a general limit. Planning/synthesis/review outputs require 4k–8k tokens. | **Critical** | Remove repo-client path from automation executor; always use direct path. |
| 2 | No `execute` command in `lumen.py`. The loop has a gap between `execution_prompt.md` and `execution_result.md` — user must manually copy/paste. | **High** | Add `cmd_execute` to lumen.py. |
| 3 | `executor.call()` returns a plain `str`. No structured result — status, files touched, test counts, blockers are all lost. | **High** | Add `ExecutionResult` dataclass + `normalize()`. |
| 4 | No state-aware context assembly. The prompt is assembled ad hoc in each lumen.py command. | **Medium** | Add `context.py` with `ExecutionContext` + `build_from_state()`. |
| 5 | No backend abstraction. `claude_code_cli` and `codex_cli` are not implemented. | **Medium** | Add adapters with graceful failure. |
| 6 | Token budgets hardcoded per model only. No task-type differentiation. | **Low** | Add `token_budgets` section to `models.json`. |

---

## 2. Real Backend Targets

### Available in this environment

| Backend | Status | Notes |
|---------|--------|-------|
| `anthropic_direct` | **Available** | `anthropic==0.86.0` installed, `ANTHROPIC_API_KEY` set. Primary real backend. |
| `openai_direct` | **Available** | `openai==2.30.0` installed, `OPENAI_API_KEY` set. Secondary real backend. |
| `claude_code_cli` | **Not available** | `claude` CLI not found in PATH. Adapter with graceful failure. |
| `codex_cli` | **Not available** | No CLI found. Adapter with graceful failure. |
| `mock` | **Available** | No deps, always works. For CI/testing. |
| `manual` | **Available** | No deps, human-in-loop. |

### Backend selection

New env var `LUMEN_BACKEND` selects the backend. If unset:
- `claude-*` model → `anthropic_direct`
- `gpt-*` / `o1` / `o3` / `o4-*` model → `openai_direct`
- Explicit `claude_code_cli` or `codex_cli` values → those adapters

The old `LUMEN_EXECUTOR=live` path is preserved for backward compatibility by mapping to the appropriate direct backend.

---

## 3. State-Aware Execution Context Assembly

### New: `automation/context.py`

```
ExecutionContext {
  task_brief         ← state/task_brief.md
  execution_prompt   ← state/execution_prompt.md
  structure_design   ← state/structure_design.md
  constraints        ← state/constraints.md
  previous_decisions ← state/previous_decisions.md
  session_id         ← state/session.json
  phase              ← state/session.json
  model_id           ← from config/args
  backend            ← from env/args
  max_tokens         ← from config token_budgets[phase]
  temperature        ← from config
  assembled_at       ← now()
}
```

`build_from_state(state_dir, model_id, backend)` reads all of the above
deterministically. Never fails if files are missing. Output is fully
reconstructible from files alone — no chat context dependency.

---

## 4. Normalized Execution Result

### New: `automation/result.py`

```
ExecutionResult {
  status              # success | partial | failed | error
  raw_output          # full backend text
  summary             # 2-4 sentences
  files_touched       # extracted from output
  tests_run           # extracted if pytest-style output
  tests_passed
  tests_failed
  unresolved_issues   # TODO/FIXME/BLOCKING markers
  blocker             # primary blocking issue
  suggested_next      # optional hint
  retryable           # bool
  backend             # which backend
  model_id            # which model
  timestamp           # ISO
  prompt_tokens       # if reported
  completion_tokens   # if reported
  error_message       # if status == error
}
```

Saved as both:
- `state/execution_result.json` — machine-readable, feeds `review`
- `state/execution_result.md` — human-readable Markdown

---

## 5. Token Budget Policy

### Problem
`src/utils/llm_client.py` MAX_TOKENS=1024 is a study protocol constraint
(§8.2 reproducibility record). It is NOT a general token limit. The
automation executor must never route through this path.

### Fix

1. Remove `_call_via_repo_client` from `executor._call_live()`.
2. Always use direct SDK calls for automation, respecting `call_params.max_tokens`
   from `models.json` (default 8192).
3. Add `token_budgets` section to `models.json` with per-phase defaults:

```json
"token_budgets": {
  "planning":        8192,
  "prompt_synthesis": 8192,
  "execution":       8192,
  "review":          8192,
  "handoff":         8192,
  "next_task":       4096,
  "default":         4096
}
```

4. `build_from_state()` looks up the budget by phase and passes it to the executor.

---

## 6. New `execute` Command (lumen.py)

```
lumen.py execute [--model MODEL] [--backend BACKEND]
```

1. Reads execution_prompt from state (requires prompt to have been run first)
2. Assembles `ExecutionContext` via `context.build_from_state()`
3. Calls `executor.execute_with_context(ctx)` → `ExecutionResult`
4. Saves:
   - `state/execution_result.json` (machine-readable)
   - `state/execution_result.md` (human-readable, also consumed by `review`)
5. Archives both to history
6. Advances phase to `result_ingest`

---

## 7. Minimal Verifiable Real Loop

Using `anthropic_direct` backend (available):

```
init
  ↓
plan --execute  (anthropic_direct, model=sonnet)
  ↓
prompt --execute --model sonnet  (anthropic_direct)
  ↓
execute --model sonnet  (anthropic_direct)  ← NEW
  ↓
review --execute  (anthropic_direct)
  ↓
next --execute
  ↓
handoff --execute
```

All steps use real Anthropic API calls. Loop is verified by running it
with a simple test task brief and checking all state artifacts are written.

---

## 8. Intentionally Deferred

- Claude Code CLI backend (CLI not in PATH; adapter boundary implemented)
- Codex CLI backend (same)
- OpenClaw channel integration
- Automatic result application (code patches, file writes from LLM output)
- Retry logic / exponential backoff
- Streaming responses
- Multi-turn conversation state
- Parallel execution of multiple tasks
