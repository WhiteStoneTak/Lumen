You are a senior technical writer producing a context handoff document.

This document will be pasted as the opening message in a **new, empty conversation** with no prior context. The reader is a capable engineer who knows nothing about what has happened in this session. The document must be complete enough that they can continue the work without asking any clarifying questions.

Every omission is a defect. Every vague statement is a defect. Keep it compact — but do not sacrifice completeness for brevity.

---

## Session Metadata

Session ID: {session_id}
Started: {created}
Date of handoff: {date}
Phase at handoff: {current_phase}
Tasks completed this session: {task_history_count}
History artifacts: {history_artifact_count}

---

## Current Task Brief

{task_brief}

---

## Latest Structure Design

{structure_design}

---

## Last Execution Result

{execution_result}

---

## Next Steps (if generated)

{next_steps}

---

## Active Constraints

{constraints}

---

## Repository Context

{repo_context}

---

## Instructions

Produce a **Handoff Summary** with exactly these sections. The document must stand alone.

---

# Handoff Summary — {session_id}

## Project State

(3–5 sentences maximum. Answer: What is Lumen? What experiment phase is it in? What is the current focus area? What is the blocking problem or next milestone?)

## Session Accomplishments

(Bulleted list. Each item is a concrete artifact created, a decision made, or a constraint confirmed. Format: "· [ARTIFACT|DECISION|CONSTRAINT] — description". No vague entries like "made progress on X".)

## Active Constraints

(Numbered list. Every constraint the next engineer must respect. Be exhaustive — omitting a constraint here causes protocol violations downstream. For each: state the constraint, its source, and whether it was confirmed or updated this session.)

## Decisions Made This Session

(Table format:)

| Decision | Rationale | Impact |
|---|---|---|
| (what was decided) | (why) | (what it changes going forward) |

If no decisions were made, write "No architectural or protocol decisions made this session."

## Open Items

(Bulleted list of unresolved questions, blockers, or deferred work. For each: state what it is and whether it is BLOCKING the next task or BACKGROUND.)

## Critical Files

(Bulleted list of files a fresh context must read before proceeding. For each:)
- `path/to/file` — why it matters and what to look for

## Next Action

(Exactly one item. Format as a mini task brief:)
**Title:** (short label)
**Goal:** (one sentence — what must be true when this action is done)
**Model preference:** (sonnet / opus / gpt54 / codex)
**First step:** (the very first thing the executor should do)

---

Date: {date}
