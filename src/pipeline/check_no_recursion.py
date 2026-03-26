"""Verify that a function source contains no direct self-recursion.

This is the static exclusion check required by the design constitution (§4,
"90-day scope restriction: hard boundary"). Any function that contains a
direct self-call in its AST is excluded from the dataset at the curation stage.

Scope boundary:
  - Detects direct self-calls only (a call whose callee Name matches the
    enclosing FunctionDef's name).
  - Indirect / mutual recursion is not detected here; it is excluded by the
    single-function scope constraint (there is no second function to recurse into).
  - Does not analyse recursive data structures in signatures (deferred).
"""

import ast
import json
import sys
from pathlib import Path


def is_recursive(source: str) -> bool:
    """Return True if *source* contains a direct self-recursive call.

    Parses *source*, finds the top-level FunctionDef, then walks its subtree
    for any ast.Call whose callee Name matches the function's own name.

    Raises ValueError if *source* contains no function definition.
    """
    tree = ast.parse(source)

    func_defs = [
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    ]
    if not func_defs:
        raise ValueError("No function definition found in source.")

    # Single-function scope: use the first (and expected only) top-level def.
    func_def = func_defs[0]
    func_name = func_def.name

    for node in ast.walk(func_def):
        if isinstance(node, ast.Call):
            # Direct call: func_name(...)
            if isinstance(node.func, ast.Name) and node.func.id == func_name:
                return True
    return False


def check_file(path: Path) -> dict:
    """Check a single .py file and return a result dict.

    Result fields:
      func_id   : stem of the file
      path      : str path
      recursive : bool
      error     : str or None
    """
    source = path.read_text(encoding="utf-8")
    try:
        recursive = is_recursive(source)
        return {"func_id": path.stem, "path": str(path), "recursive": recursive, "error": None}
    except (SyntaxError, ValueError) as exc:
        return {"func_id": path.stem, "path": str(path), "recursive": None, "error": str(exc)}


def main() -> None:
    """Scan all .py files in data/functions/raw/ and report any recursive ones.

    Exits with code 1 if any recursive (or errored) functions are found.
    """
    repo_root = Path(__file__).resolve().parents[2]
    raw_dir = repo_root / "data" / "functions" / "raw"

    if not raw_dir.exists():
        print(f"ERROR: raw directory not found: {raw_dir}", file=sys.stderr)
        sys.exit(1)

    py_files = sorted(raw_dir.glob("*.py"))
    if not py_files:
        print("No .py files found in data/functions/raw/")
        return

    results = [check_file(f) for f in py_files]

    flagged = [r for r in results if r["recursive"] or r["error"]]

    for r in results:
        status = "RECURSIVE" if r["recursive"] else ("ERROR" if r["error"] else "ok")
        detail = f"  -> {r['error']}" if r["error"] else ""
        print(f"  [{status}] {r['func_id']}{detail}")

    if flagged:
        print(f"\n{len(flagged)} function(s) flagged — exclude before proceeding.")
        sys.exit(1)
    else:
        print(f"\nAll {len(results)} function(s) passed the non-recursion check.")


if __name__ == "__main__":
    main()
