"""result.py — Normalized execution result for the Lumen automation layer.

All executor backends produce an ExecutionResult.  The normalize()
function converts raw text output into a structured result regardless
of which backend produced it.

Outputs are saved as both:
  - execution_result.json  (machine-readable, feeds review prompt context)
  - execution_result.md    (human-readable, also consumed by review template)

Usage:
    from result import ExecutionResult, normalize, to_json, to_markdown
    result = normalize(raw_text, backend="anthropic_direct", model_id="claude-sonnet-4-6")
    # or on error:
    result = normalize("", backend="anthropic_direct", model_id="...", error_message="...")
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class ExecutionResult:
    """Normalized output from any executor backend.

    All fields are always present.  Numeric fields are None when the
    backend did not report them.  Lists are empty when nothing was found.
    """

    # --- Outcome ---
    status: str                  # "success" | "partial" | "failed" | "error"
    raw_output: str              # Full raw text from the backend
    summary: str                 # 2–4 sentence human-readable summary

    # --- Artifact tracking ---
    files_touched: list[str]     # Files created or modified (extracted or reported)

    # --- Test results (None when not applicable) ---
    tests_run: int | None
    tests_passed: int | None
    tests_failed: int | None

    # --- Issues ---
    unresolved_issues: list[str]  # TODO / FIXME / BLOCKING markers found in output
    blocker: str | None           # Primary blocking issue (prevents completion)

    # --- Next step hint ---
    suggested_next: str | None    # Brief hint for the next task (optional)

    # --- Execution metadata ---
    retryable: bool               # Whether re-running is safe and useful
    backend: str                  # Backend that produced this result
    model_id: str                 # Model that was used
    timestamp: str                # ISO-8601 UTC

    # --- Token accounting (None when backend does not report) ---
    prompt_tokens: int | None
    completion_tokens: int | None

    # --- Error detail ---
    error_message: str | None     # Populated only when status == "error"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def normalize(
    raw_output: str,
    *,
    backend: str,
    model_id: str,
    error_message: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
) -> ExecutionResult:
    """Convert raw backend output to a normalized ExecutionResult.

    For text outputs (live/manual backends), does best-effort extraction
    of structured fields.  Never crashes — always returns a valid result.
    """
    if error_message:
        return ExecutionResult(
            status="error",
            raw_output=raw_output or "",
            summary=f"Execution failed: {error_message}",
            files_touched=[],
            tests_run=None,
            tests_passed=None,
            tests_failed=None,
            unresolved_issues=[error_message[:200]],
            blocker=error_message[:200],
            suggested_next=None,
            retryable=True,
            backend=backend,
            model_id=model_id,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            error_message=error_message,
        )

    files = _extract_files(raw_output)
    tests_run, tests_passed, tests_failed = _extract_test_counts(raw_output)
    status = _infer_status(raw_output, tests_failed)
    summary = _extract_summary(raw_output)

    return ExecutionResult(
        status=status,
        raw_output=raw_output,
        summary=summary,
        files_touched=files,
        tests_run=tests_run,
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        unresolved_issues=_extract_issues(raw_output),
        blocker=_extract_blocker(raw_output),
        suggested_next=None,
        retryable=status in ("partial", "failed"),
        backend=backend,
        model_id=model_id,
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        error_message=None,
    )


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def to_json(result: ExecutionResult) -> str:
    """Serialize ExecutionResult to a JSON string (indented, UTF-8 safe)."""
    return json.dumps(asdict(result), indent=2, ensure_ascii=False)


def from_json(data: str | dict) -> ExecutionResult:
    """Deserialize ExecutionResult from a JSON string or dict."""
    if isinstance(data, str):
        data = json.loads(data)
    return ExecutionResult(**data)


def to_markdown(result: ExecutionResult) -> str:
    """Render ExecutionResult as human-readable Markdown.

    This is the content written to execution_result.md, which is consumed
    by the `review` template as {execution_result}.
    """
    lines: list[str] = [
        "# Execution Result",
        "",
        f"**Status:** `{result.status}`  ",
        f"**Backend:** {result.backend}  ",
        f"**Model:** {result.model_id}  ",
        f"**Time:** {result.timestamp}",
    ]

    if result.prompt_tokens is not None:
        lines.append(
            f"**Tokens:** {result.prompt_tokens} prompt / "
            f"{result.completion_tokens} completion"
        )

    lines += ["", "## Summary", "", result.summary, ""]

    if result.files_touched:
        lines += ["## Files Touched", ""]
        for f in result.files_touched:
            lines.append(f"- `{f}`")
        lines.append("")

    if result.tests_run is not None:
        lines += [
            "## Test Results",
            "",
            f"- Run: {result.tests_run}",
            f"- Passed: {result.tests_passed}",
            f"- Failed: {result.tests_failed}",
            "",
        ]

    if result.unresolved_issues:
        lines += ["## Unresolved Issues", ""]
        for issue in result.unresolved_issues:
            lines.append(f"- {issue}")
        lines.append("")

    if result.blocker:
        lines += ["## Blocker", "", result.blocker, ""]

    if result.error_message:
        lines += ["## Error", "", f"```\n{result.error_message}\n```", ""]

    # Cap raw output at 6000 chars to keep state files manageable
    raw = result.raw_output
    if len(raw) > 6000:
        raw = raw[:6000] + f"\n\n... [truncated — {len(result.raw_output)} total chars]"

    lines += ["## Raw Output", "", "```", raw, "```", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Extraction helpers (best-effort, never crash)
# ---------------------------------------------------------------------------


def _extract_files(text: str) -> list[str]:
    """Extract file paths mentioned as created / modified / saved."""
    found: list[str] = []
    patterns = [
        # "Created automation/foo.py", "Saved `data/x.json`"
        r"(?:Created|Modified|Added|Wrote|Updated|Saved|Written)"
        r"(?:\s+file)?\s*[:`]?\s*['\"`]?([^\s\n'\"`,]+\.[a-zA-Z]{1,10})['\"`]?",
        # backtick-wrapped paths containing a slash or dot
        r"`([a-zA-Z0-9_./ -]+\.[a-zA-Z]{2,10})`",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            candidate = m.group(1).strip()
            # Require at least one path separator or recognisable extension
            if ("/" in candidate or candidate.count(".") == 1) and candidate not in found:
                found.append(candidate)
    return found[:20]


def _extract_test_counts(text: str) -> tuple[int | None, int | None, int | None]:
    """Extract pytest-style test counts: 'N passed', 'N failed'."""
    m_pass = re.search(r"(\d+)\s+passed", text)
    m_fail = re.search(r"(\d+)\s+failed", text)
    passed = int(m_pass.group(1)) if m_pass else None
    failed = int(m_fail.group(1)) if m_fail else None
    if passed is not None or failed is not None:
        run = (passed or 0) + (failed or 0)
        return (run or None), passed, failed
    return None, None, None


def _infer_status(text: str, tests_failed: int | None) -> str:
    if tests_failed and tests_failed > 0:
        return "partial"
    lower = text.lower()
    error_signals = [
        "traceback (most recent call last)",
        "syntaxerror",
        "nameerror",
        "importerror",
        "filenotfounderror",
        "error:",
        "failed to",
        "cannot proceed",
        "unable to",
    ]
    if any(s in lower for s in error_signals):
        return "partial"
    return "success"


def _extract_summary(text: str) -> str:
    """Extract or synthesize a brief summary from raw output."""
    # Look for explicit summary section
    for header in ["## Summary", "# Summary", "**Summary**", "Summary:"]:
        idx = text.find(header)
        if idx >= 0:
            after = text[idx + len(header):].strip()
            sentences = re.split(r"(?<=[.!?])\s+", after)
            snippet = " ".join(s.strip() for s in sentences[:3] if s.strip())
            if snippet:
                return snippet[:400]
    # Fallback: first substantive non-heading paragraph
    lines = [
        ln.strip()
        for ln in text.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if lines:
        return " ".join(lines[:3])[:400]
    return "No summary available."


def _extract_issues(text: str) -> list[str]:
    """Extract TODO / FIXME / BLOCKING markers."""
    issues: list[str] = []
    for pat in [
        r"(?:TODO|FIXME|HACK):\s*(.+)",
        r"\[BLOCKING\]\s*(.+)",
        r"(?:Issue|Problem|Bug):\s*(.+)",
    ]:
        for m in re.finditer(pat, text, re.IGNORECASE):
            item = m.group(1).strip()[:120]
            if item and item not in issues:
                issues.append(item)
    return issues[:5]


def _extract_blocker(text: str) -> str | None:
    """Extract the primary blocking issue if explicitly stated."""
    for pat in [
        r"\[BLOCKING\]\s*(.+)",
        r"BLOCKED BY:\s*(.+)",
        r"Cannot proceed[,\s]+because[:\s]+(.+)",
        r"BLOCKER:\s*(.+)",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:200]
    return None
