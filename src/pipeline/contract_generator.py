"""Generate behavioral contracts for pilot functions via the contract-generation LLM.

Raw contract outputs are written to data/contracts/raw/.
Human-reviewed contracts are stored separately in data/contracts/reviewed/.
Diffs between raw and reviewed are stored in data/contracts/diffs/.

Contracts are used in conditions C1+ and C4.
C1+ contracts are derived from C4 to preserve information parity.

Contract-generation LLM: Anthropic Claude Sonnet 4.6 (designated per protocol §8.1).
This module MUST NOT be used with test-subject models (GPT-5.4, Claude Opus 4.6).

Scope constraints (from design constitution):
  - Non-recursive, single-function Python only.
  - Input to the LLM: raw source + typed AST type info.
  - Input must NOT include T1 checklists, T2 bug annotations, T3 tests, or any
    other ground-truth supervision artifact.
  - This module stops at raw artifact generation; author review and diff
    generation are separate steps.

Retry policy (protocol §6):
  Up to MAX_ATTEMPTS total per function. Retry only on mechanical failures
  (invalid JSON, missing sections, empty postconditions). If all attempts are
  exhausted, the function is excluded and the failure is logged; the caller
  must record the exclusion.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Protocol constants
# ---------------------------------------------------------------------------

# Designated contract-generation model per experimental protocol §8.1.
# Do NOT substitute a test-subject model here.
CONTRACT_GENERATION_MODEL = "claude-sonnet-4-6"
CONTRACT_GENERATION_PROVIDER = "Anthropic"

# Maximum total attempts per function (protocol §6: up to 2 regeneration attempts).
MAX_ATTEMPTS = 3

# ---------------------------------------------------------------------------
# Repository paths
# ---------------------------------------------------------------------------

# Two levels up from src/pipeline/ → repository root.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

RAW_FUNCTIONS_DIR = _REPO_ROOT / "data" / "functions" / "raw"
TYPED_AST_DIR = _REPO_ROOT / "data" / "functions" / "typed_ast"
RAW_CONTRACTS_DIR = _REPO_ROOT / "data" / "contracts" / "raw"

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_CONTRACT_PROMPT_TEMPLATE = """\
You are generating a behavioral contract for a Python function.

A behavioral contract consists of three parts:
- preconditions: assertions about the function inputs that must hold for correct behavior
- postconditions: assertions about the return value, given that preconditions hold
- invariants: properties that are always true regardless of input

Rules:
- Base all assertions solely on the function source code and type signature provided below.
- Do not introduce domain knowledge or assumptions not directly inferable from the code.
- Do not describe implementation details (loop structure, variable names, etc.).
- Write each assertion as a concise, independently checkable English sentence.
- postconditions must be non-empty: the return value must be described.

Function source:
```python
{source}
```

Type signature: {type_signature}

Respond with ONLY a JSON object in exactly this format, with no other text before or after:
{{
  "preconditions": ["<assertion>", ...],
  "postconditions": ["<assertion>", ...],
  "invariants": ["<assertion>", ...]
}}
"""

# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _load_raw_source(func_id: str) -> str:
    path = RAW_FUNCTIONS_DIR / f"{func_id}.py"
    if not path.exists():
        raise FileNotFoundError(f"Raw source not found: {path}")
    return path.read_text(encoding="utf-8")


def _load_typed_ast(func_id: str) -> dict:
    path = TYPED_AST_DIR / f"{func_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Typed AST not found: {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Lineage verification
# ---------------------------------------------------------------------------


def _verify_lineage(func_id: str, typed_ast: dict, source: str) -> None:
    """Raise ValueError if func_id or source_hash in typed_ast does not match."""
    if typed_ast.get("func_id") != func_id:
        raise ValueError(
            f"func_id mismatch: typed_ast has '{typed_ast.get('func_id')}', "
            f"expected '{func_id}'"
        )
    computed = hashlib.sha256(source.encode("utf-8")).hexdigest()
    recorded = typed_ast.get("source_hash", "")
    if computed != recorded:
        raise ValueError(
            f"source_hash mismatch for '{func_id}': "
            f"computed {computed[:16]}… != recorded {recorded[:16]}…"
        )


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def _build_prompt(source: str, typed_ast: dict) -> str:
    type_sig = (
        typed_ast.get("type_info", {}).get("func_type")
        or "(type signature unavailable)"
    )
    return _CONTRACT_PROMPT_TEMPLATE.format(
        source=source.rstrip(),
        type_signature=type_sig,
    )


# ---------------------------------------------------------------------------
# Response parsing and mechanical validation
# ---------------------------------------------------------------------------


def _parse_json_response(response_text: str) -> tuple[dict | None, str | None]:
    """Parse the LLM response as JSON. Returns (parsed_dict, error_message).

    Strips a markdown code-fence wrapper if the model ignored the instruction.
    """
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        inner_lines = lines[1:]  # drop opening ```[json]
        inner = "\n".join(inner_lines)
        if inner.rstrip().endswith("```"):
            inner = inner.rstrip()[:-3].rstrip()
        text = inner.strip()
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, f"JSON parse error: {exc}"


def _validate_raw_contract(data: object) -> list[str]:
    """Return a list of mechanical validation errors; empty list means valid."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["response is not a JSON object"]
    for key in ("preconditions", "postconditions", "invariants"):
        if key not in data:
            errors.append(f"missing required key: '{key}'")
        elif not isinstance(data[key], list):
            errors.append(f"'{key}' is not a JSON array")
        elif not all(isinstance(item, str) for item in data[key]):
            errors.append(f"'{key}' contains non-string items")
    if not errors and not data.get("postconditions"):
        errors.append("postconditions array is empty")
    return errors


# ---------------------------------------------------------------------------
# LLM call (delegates to llm_client)
# ---------------------------------------------------------------------------


def _call_llm(prompt: str) -> str:
    """Call the contract-generation LLM via llm_client."""
    # Add src/ to path for development use (no-op if the package is installed).
    _src_dir = str(Path(__file__).resolve().parent.parent)
    if _src_dir not in sys.path:
        sys.path.insert(0, _src_dir)

    from utils import llm_client  # type: ignore[import]

    return llm_client.call(
        prompt,
        model=CONTRACT_GENERATION_MODEL,
        temperature=0.0,
    )


# ---------------------------------------------------------------------------
# Main generation entry point
# ---------------------------------------------------------------------------


def generate_raw_contract(func_id: str) -> Path:
    """Generate and save a raw contract artifact for *func_id*.

    Attempts up to MAX_ATTEMPTS times on mechanical failures (invalid JSON,
    missing sections, empty postconditions). Returns the path to the saved
    artifact on success. Raises RuntimeError if all attempts are exhausted
    (caller must log the exclusion per protocol §6).
    """
    source = _load_raw_source(func_id)
    typed_ast = _load_typed_ast(func_id)
    _verify_lineage(func_id, typed_ast, source)

    source_hash: str = typed_ast["source_hash"]
    prompt = _build_prompt(source, typed_ast)
    last_error = ""

    for attempt in range(MAX_ATTEMPTS):
        print(f"  [{func_id}] attempt {attempt} …", file=sys.stderr)
        response_text = _call_llm(prompt)

        parsed, parse_error = _parse_json_response(response_text)
        if parse_error:
            last_error = f"attempt {attempt}: {parse_error}"
            print(f"  [{func_id}] {last_error}", file=sys.stderr)
            continue

        validation_errors = _validate_raw_contract(parsed)
        if validation_errors:
            last_error = (
                f"attempt {attempt}: validation failed — "
                + "; ".join(validation_errors)
            )
            print(f"  [{func_id}] {last_error}", file=sys.stderr)
            continue

        # Mechanical validation passed — write artifact.
        artifact = {
            "lumen_schema": "contract-raw-v1",
            "func_id": func_id,
            "source_hash": source_hash,
            "generation_model": CONTRACT_GENERATION_MODEL,
            "generation_provider": CONTRACT_GENERATION_PROVIDER,
            "generation_attempt": attempt,
            "generation_temperature": 0.0,
            "preconditions": parsed["preconditions"],
            "postconditions": parsed["postconditions"],
            "invariants": parsed["invariants"],
        }

        out_path = RAW_CONTRACTS_DIR / f"{func_id}.json"
        out_path.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"  [{func_id}] saved → {out_path}", file=sys.stderr)
        return out_path

    raise RuntimeError(
        f"Contract generation failed for '{func_id}' after {MAX_ATTEMPTS} attempts. "
        f"Last error: {last_error}"
    )


def main() -> None:
    """Entry point: generate raw contracts for all pilot functions."""
    func_ids = sorted(p.stem for p in RAW_FUNCTIONS_DIR.glob("*.py"))
    if not func_ids:
        print("No function source files found in RAW_FUNCTIONS_DIR.", file=sys.stderr)
        sys.exit(1)

    print(f"Generating raw contracts for: {func_ids}", file=sys.stderr)
    failed: list[str] = []

    for func_id in func_ids:
        try:
            generate_raw_contract(func_id)
        except RuntimeError as exc:
            print(f"EXCLUDED {func_id}: {exc}", file=sys.stderr)
            failed.append(func_id)
        except Exception as exc:
            print(f"ERROR {func_id}: {exc}", file=sys.stderr)
            failed.append(func_id)

    if failed:
        print(f"\nFailed / excluded functions: {failed}", file=sys.stderr)
        sys.exit(1)
    else:
        print("\nAll raw contracts generated successfully.", file=sys.stderr)


if __name__ == "__main__":
    main()
