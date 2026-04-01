# Automation Scaffold — Implementation Audit

**Date:** 2026-03-31
**Auditor:** Automated inspection pass prior to completion sprint
**Scope:** `automation/` directory and integration points

---

## 1. What Exists

| File | Status | Notes |
|------|--------|-------|
| `lumen.py` | Complete — functional | 7 commands: init, status, plan, prompt, ingest, next, handoff. Session management, state I/O, template rendering, model routing all present. |
| `executor.py` | Functional, incomplete | Real API calls work (Anthropic + OpenAI). No mock/manual mode — blocks local testing without live keys. |
| `config/models.json` | Complete | 4 models: sonnet, opus, gpt54, codex. Defaults set. |
| `templates/plan.md` | Complete | Structure design prompt. 8-section output spec. Good quality. |
| `templates/prompt.md` | Complete | Execution prompt synthesis. Uses {target_model}, {structure_design}. Good quality. |
| `schemas/task_brief.json` | Complete | Has `blank_template` field used by `init`. |
| `schemas/structure_design.json` | Complete | Output schema only (no blank_template — correct, it's an output). |
| `schemas/execution_result.json` | Complete | Accepts free-form or structured text via `ingest`. |
| `state/` | Directory exists, empty | No .gitkeep. No session yet. |
| `history/` | Directory exists, empty | No .gitkeep. |

---

## 2. What Is Incomplete

| Gap | Impact | Fix |
|-----|--------|-----|
| `templates/next.md` — missing | `next` command crashes at template load | Create |
| `templates/handoff.md` — missing | `handoff` command crashes at template load | Create |
| `templates/review.md` — missing | `review` command not yet wired | Create + wire |
| `schemas/execution_prompt.json` — missing | No schema contract for execution_prompt state artifact | Create |
| `schemas/next_steps.json` — missing | No schema contract for next_steps artifact | Create |
| `schemas/handoff_summary.json` — missing | No schema contract for handoff_summary artifact | Create |
| `executor.py` — no mock/manual mode | Cannot test CLI locally without live API keys | Add LUMEN_EXECUTOR_MODE |
| `lumen.py` — no `review` command | Task spec requires plan/prompt/review/handoff as four primary modes | Add cmd_review |
| `state/.gitkeep` — missing | git rm -rf may remove the state dir | Create |
| `history/.gitkeep` — missing | Same | Create |
| `tests/test_automation.py` — missing | No automated verification of scaffold | Create |
| `IMPLEMENTATION_AUDIT.md` — missing | This file | ✓ Done |

---

## 3. What Is Ambiguous or Risky

| Item | Risk Level | Decision |
|------|-----------|----------|
| `cmd_next` in lumen.py advances phase to "review" but the command is named "next" | Low — naming confusion | Resolved: rename phase advance to "intake" post-next, add distinct "review" command that sets phase to "review" |
| executor.py `_call_via_repo_client` uses `src/utils/llm_client.py` which enforces MAX_TOKENS=1024 | Medium — planning outputs need more tokens | Resolved: executor direct-call path uses `call_params.max_tokens` (8192) from config; repo client path uses its own limit (acceptable for initial use) |
| Templates use `{variable}` substitution — Python's `.format()` would break any `{` in task brief content (e.g., JSON examples) | Medium — runtime crash on malformed briefs | Resolved: `_render()` uses manual `.replace()` loop, not `.format_map()` — safe |
| `state/` files are NOT gitignored — session state will appear in git status | Low — working state clutters commits | Accepted: state is intentionally tracked (enables resuming across machines). `.gitkeep` keeps dirs. |
| No validation that required template vars are present before rendering | Low — renders silently with unfilled placeholders | Acceptable for MVP: missing vars produce visible `{var}` tokens which are easy to spot |

---

## 4. What Is Intentionally Deferred

- OpenClaw control-plane integration (wire later as a channel on top of this scaffold)
- Claude Code SDK / subprocess execution (executor abstraction already has the extension point)
- Automated execution loop (plan → execute → ingest → next without human gate)
- Constraint extraction from execution results (currently manual via `constraints.md`)
- Browser/GUI automation — excluded permanently from this layer

---

## 5. Post-Audit Action Plan

Completed in the same session as this audit:

1. ✓ Write this audit document
2. Create `templates/next.md`, `templates/handoff.md`, `templates/review.md`
3. Create `schemas/execution_prompt.json`, `schemas/next_steps.json`, `schemas/handoff_summary.json`
4. Add `mock` and `manual` modes to `executor.py`
5. Add `review` command to `lumen.py`
6. Add `.gitkeep` to `state/` and `history/`
7. Write `tests/test_automation.py`
8. Run end-to-end verification pass
