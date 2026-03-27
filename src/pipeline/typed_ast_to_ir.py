"""Lower C3 typed AST + authoritative reviewed contract → C4 IR (ir-v1).

Reads:
  data/functions/typed_ast/{func_id}.json    (C3 — typed_ast-v1 artifact)
  data/contracts/reviewed/{func_id}.json     (authoritative contract-reviewed-v1 artifact)

Writes:
  data/functions/ir/{func_id}.json           (C4 — ir-v1 artifact)

Output schema: ir-v1 (see docs/experimental-protocol.md §4.7).

This stage corresponds to condition C4 in the study.

The ir-v1 artifact is the experimental prototype C4 representation (constitution §14:
"prototype ancestor of a Lumen Core IR"). It is not the final long-term canonical
Core IR. No canonicalization, graph normalization, or custom contract DSL is applied.

Lowering is conservative assembly only:
  - type_info copied verbatim from typed_ast-v1
  - contracts copied from reviewed contract (preconditions/postconditions/invariants only)
  - ast copied verbatim from typed_ast-v1

Scope constraints (from design constitution §4):
  - Non-recursive, single-function Python only.
  - No class analysis.
  - No multi-file type resolution.

Input isolation:
  - Reads only typed AST and reviewed contract.
  - Must NOT read raw contracts, diff contracts, T1 checklists, T2 bug annotations,
    T3 tests, or any other supervision artifact.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "ir-v1"

# ---------------------------------------------------------------------------
# Repository paths
# ---------------------------------------------------------------------------

# Two levels up from src/pipeline/ → repository root.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

TYPED_AST_DIR = _REPO_ROOT / "data" / "functions" / "typed_ast"
REVIEWED_CONTRACT_DIR = _REPO_ROOT / "data" / "contracts" / "reviewed"
IR_DIR = _REPO_ROOT / "data" / "functions" / "ir"

# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _load_typed_ast(func_id: str) -> dict:
    path = TYPED_AST_DIR / f"{func_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Typed AST not found: {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _load_reviewed_contract(func_id: str) -> dict:
    path = REVIEWED_CONTRACT_DIR / f"{func_id}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Reviewed contract not found: {path}\n"
            f"  Author review must be completed before C4 lowering can proceed."
        )
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_typed_ast(typed_ast: dict) -> None:
    """Raise ValueError if the typed AST is not a valid typed_ast-v1 artifact."""
    if not isinstance(typed_ast, dict):
        raise ValueError("Typed AST is not a JSON object.")
    schema = typed_ast.get("lumen_schema")
    if schema != "typed_ast-v1":
        raise ValueError(
            f"Expected lumen_schema 'typed_ast-v1', got '{schema}'."
        )
    for key in ("func_id", "source_hash", "type_info", "ast"):
        if key not in typed_ast:
            raise ValueError(f"Typed AST missing required field: '{key}'.")


def _validate_reviewed_contract(reviewed_contract: dict) -> None:
    """Raise ValueError if the reviewed contract is not valid or is a placeholder.

    A reviewed contract with empty postconditions is not a valid lowering input
    (see protocol §4.7 and §6).
    """
    if not isinstance(reviewed_contract, dict):
        raise ValueError("Reviewed contract is not a JSON object.")
    schema = reviewed_contract.get("lumen_schema")
    if schema != "contract-reviewed-v1":
        raise ValueError(
            f"Expected lumen_schema 'contract-reviewed-v1', got '{schema}'."
        )
    for key in ("preconditions", "postconditions", "invariants"):
        if key not in reviewed_contract:
            raise ValueError(
                f"Reviewed contract missing required field: '{key}'."
            )
        if not isinstance(reviewed_contract[key], list):
            raise ValueError(
                f"Reviewed contract field '{key}' is not a list."
            )
        if not all(isinstance(item, str) for item in reviewed_contract[key]):
            raise ValueError(
                f"Reviewed contract field '{key}' contains non-string items."
            )
    if not reviewed_contract["postconditions"]:
        raise ValueError(
            "Reviewed contract has empty postconditions. "
            "Author review must be completed and postconditions populated "
            "before C4 lowering can proceed."
        )


# ---------------------------------------------------------------------------
# Lineage verification
# ---------------------------------------------------------------------------


def _verify_lineage(
    func_id: str, typed_ast: dict, reviewed_contract: dict
) -> None:
    """Raise ValueError if func_id or source_hash do not match across artifacts."""
    ta_func_id = typed_ast.get("func_id")
    if ta_func_id != func_id:
        raise ValueError(
            f"func_id mismatch: typed_ast has '{ta_func_id}', expected '{func_id}'."
        )
    rc_func_id = reviewed_contract.get("func_id")
    if rc_func_id != func_id:
        raise ValueError(
            f"func_id mismatch: reviewed_contract has '{rc_func_id}', "
            f"expected '{func_id}'."
        )
    ta_hash = typed_ast.get("source_hash", "")
    rc_hash = reviewed_contract.get("source_hash", "")
    if ta_hash != rc_hash:
        raise ValueError(
            f"source_hash mismatch for '{func_id}': "
            f"typed_ast has {ta_hash[:16]}… but reviewed_contract has {rc_hash[:16]}…"
        )

# ---------------------------------------------------------------------------
# Lowering
# ---------------------------------------------------------------------------


def lower_to_ir(typed_ast: dict, reviewed_contract: dict) -> dict:
    """Assemble an ir-v1 artifact from validated upstream artifacts.

    This is conservative assembly only — no transformation of AST or contracts.
    """
    return {
        "lumen_schema": SCHEMA_VERSION,
        "func_id": typed_ast["func_id"],
        "source_hash": typed_ast["source_hash"],
        "type_info": typed_ast["type_info"],
        "contracts": {
            "preconditions": reviewed_contract["preconditions"],
            "postconditions": reviewed_contract["postconditions"],
            "invariants": reviewed_contract["invariants"],
        },
        "ast": typed_ast["ast"],
    }


# ---------------------------------------------------------------------------
# File-level entry point
# ---------------------------------------------------------------------------


def convert_file(func_id: str) -> Path:
    """Lower one function from typed AST + reviewed contract to ir-v1.

    Returns the path of the written ir-v1 artifact.
    Raises on any validation or lineage failure.
    """
    typed_ast = _load_typed_ast(func_id)
    reviewed_contract = _load_reviewed_contract(func_id)

    _validate_typed_ast(typed_ast)
    _validate_reviewed_contract(reviewed_contract)
    _verify_lineage(func_id, typed_ast, reviewed_contract)

    artifact = lower_to_ir(typed_ast, reviewed_contract)

    IR_DIR.mkdir(parents=True, exist_ok=True)
    out_path = IR_DIR / f"{func_id}.json"
    out_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"  [{func_id}] saved → {out_path}", file=sys.stderr)
    return out_path


# ---------------------------------------------------------------------------
# Batch entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point: lower all typed AST artifacts to ir-v1."""
    func_ids = sorted(p.stem for p in TYPED_AST_DIR.glob("*.json"))
    if not func_ids:
        print("No typed AST artifacts found in TYPED_AST_DIR.", file=sys.stderr)
        sys.exit(1)

    print(f"Lowering to ir-v1: {func_ids}", file=sys.stderr)
    failed: list[str] = []

    for func_id in func_ids:
        try:
            convert_file(func_id)
        except Exception as exc:
            print(f"FAILED {func_id}: {exc}", file=sys.stderr)
            failed.append(func_id)

    if failed:
        print(f"\nFailed functions: {failed}", file=sys.stderr)
        sys.exit(1)
    else:
        print("\nAll ir-v1 artifacts written successfully.", file=sys.stderr)


if __name__ == "__main__":
    main()
