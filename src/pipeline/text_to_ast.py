"""Convert a raw Python function source file to deterministic AST JSON (C2).

Reads .py files from data/functions/raw/, serialises the Python AST to a
canonical JSON dict, and writes the output to data/functions/ast/{func_id}.json.

Output schema: ast-v1 (see docs/experimental-protocol.md §4.1).

Each function is checked for self-recursion before conversion; recursive
functions are skipped and logged (they must be excluded at curation time).

Hashing: SHA-256 of the raw .py source (UTF-8), stored in source_hash.
The hash is computed inline (no package install required for the thin slice).
"""

import ast
import hashlib
import json
import sys
from pathlib import Path

from check_no_recursion import is_recursive  # sibling module; run from src/pipeline/


SCHEMA_VERSION = "ast-v1"


# ---------------------------------------------------------------------------
# AST serialisation
# ---------------------------------------------------------------------------

def _node_to_dict(node: object) -> object:
    """Recursively convert an ast.AST node (or list/scalar) to a JSON-safe value.

    Each AST node becomes {"_type": "<ClassName>", "<field>": ...}.
    Lists are converted element-wise.
    Scalars (int, float, str, bool, None) are returned as-is.
    """
    if isinstance(node, ast.AST):
        result: dict = {"_type": type(node).__name__}
        for field, value in ast.iter_fields(node):
            result[field] = _node_to_dict(value)
        return result
    if isinstance(node, list):
        return [_node_to_dict(item) for item in node]
    # Scalar: int, float, str, bool, None, bytes
    if isinstance(node, bytes):
        return node.decode("utf-8", errors="replace")
    return node


def parse_function(source: str) -> dict:
    """Parse *source* and return a JSON-serialisable AST dict (ast-v1 schema).

    Does not include func_id or source_hash — those are added by the caller.
    Raises SyntaxError if source does not parse.
    """
    tree = ast.parse(source)
    return _node_to_dict(tree)


# ---------------------------------------------------------------------------
# File-level operations
# ---------------------------------------------------------------------------

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def convert_file(raw_path: Path, ast_dir: Path) -> dict:
    """Convert one raw .py file to AST JSON and write to *ast_dir*.

    Returns a result dict with keys: func_id, status, output_path, error.
    """
    func_id = raw_path.stem
    source = raw_path.read_text(encoding="utf-8")

    # Scope boundary: skip recursive functions.
    try:
        if is_recursive(source):
            return {
                "func_id": func_id,
                "status": "skipped_recursive",
                "output_path": None,
                "error": None,
            }
    except (SyntaxError, ValueError) as exc:
        return {
            "func_id": func_id,
            "status": "error",
            "output_path": None,
            "error": f"recursion check failed: {exc}",
        }

    # Convert.
    try:
        ast_dict = parse_function(source)
    except SyntaxError as exc:
        return {
            "func_id": func_id,
            "status": "error",
            "output_path": None,
            "error": f"parse error: {exc}",
        }

    artifact = {
        "lumen_schema": SCHEMA_VERSION,
        "func_id": func_id,
        "source_hash": _sha256(source),
        "ast": ast_dict,
    }

    out_path = ast_dir / f"{func_id}.json"
    out_path.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "func_id": func_id,
        "status": "ok",
        "output_path": str(out_path),
        "error": None,
    }


def main() -> None:
    """Batch-convert all .py files in data/functions/raw/ to AST JSON.

    Writes outputs to data/functions/ast/.
    Exits with code 1 if any file fails or is skipped due to recursion.
    """
    repo_root = Path(__file__).resolve().parents[2]
    raw_dir = repo_root / "data" / "functions" / "raw"
    ast_dir = repo_root / "data" / "functions" / "ast"

    if not raw_dir.exists():
        print(f"ERROR: {raw_dir} does not exist.", file=sys.stderr)
        sys.exit(1)

    ast_dir.mkdir(parents=True, exist_ok=True)

    py_files = sorted(raw_dir.glob("*.py"))
    if not py_files:
        print("No .py files found in data/functions/raw/")
        return

    results = [convert_file(f, ast_dir) for f in py_files]

    ok = [r for r in results if r["status"] == "ok"]
    skipped = [r for r in results if r["status"] == "skipped_recursive"]
    errors = [r for r in results if r["status"] == "error"]

    for r in results:
        if r["status"] == "ok":
            print(f"  [ok]      {r['func_id']} -> {r['output_path']}")
        elif r["status"] == "skipped_recursive":
            print(f"  [skipped] {r['func_id']} (recursive — excluded)")
        else:
            print(f"  [error]   {r['func_id']}: {r['error']}")

    print(f"\n{len(ok)} converted, {len(skipped)} skipped, {len(errors)} errors.")

    if skipped or errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
