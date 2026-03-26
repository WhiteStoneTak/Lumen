"""Enrich the C2 AST with mypy-derived type annotations to produce the C3 typed AST.

Reads:
  data/functions/ast/{func_id}.json       (C2 — ast-v1 artifact)
  data/functions/raw/{func_id}.py         (raw source, needed for mypy)

Writes:
  data/functions/typed_ast/{func_id}.json (C3 — typed_ast-v1 artifact)

Output schema: typed_ast-v1 (see docs/experimental-protocol.md §4.2).

Type extraction method:
  mypy.build.build() is called on the raw source file with incremental mode
  disabled.  Parameter types and the return type are extracted from the
  FuncDef node in the mypy AST.  These correspond to explicit PEP 484
  annotations in the source, confirmed and resolved by mypy.

Known limitation:
  The mypy build API in this usage mode does not run the full type-checker
  over function bodies.  Local variable types (inferred from assignments,
  for-loop targets, etc.) are therefore NOT included.  This limitation is
  recorded in extraction_notes of every artifact so it is visible to
  downstream consumers and to anyone inspecting the data.

  If mypy is not installed, extraction fails gracefully: extraction_status
  is set to "failed" and extraction_notes explains the cause.  The artifact
  is still written so the pipeline can proceed in stub form.

Scope constraints (from design constitution §4):
  - Non-recursive, single-function Python only.
  - No class analysis.
  - No multi-file type resolution.
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


SCHEMA_VERSION = "typed_ast-v1"

# ---------------------------------------------------------------------------
# mypy availability check
# ---------------------------------------------------------------------------

def _mypy_available() -> bool:
    return importlib.util.find_spec("mypy") is not None


def _mypy_version() -> str:
    try:
        import mypy.version
        return mypy.version.__version__
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Type extraction
# ---------------------------------------------------------------------------

def _serialize_type(t) -> str | None:
    """Convert a mypy type object to a stable string.  Returns None on failure."""
    if t is None:
        return None
    try:
        return str(t)
    except Exception:
        return None


def extract_type_info(source: str, func_id: str) -> dict:
    """Run mypy on *source* and extract function signature types.

    Returns a type_info dict with keys:
      extraction_status  : "ok" | "partial" | "failed"
      extraction_notes   : list of strings
      func_type          : str or None
      params             : list of {name, mypy_type, has_explicit_annotation}
      return_type        : str or None

    Never raises — failures are returned as extraction_status "failed".
    """
    if not _mypy_available():
        return {
            "extraction_status": "failed",
            "extraction_notes": [
                "mypy is not installed; install with: pip install mypy",
                "local variable types: not extracted (see module docstring)",
            ],
            "func_type": None,
            "params": [],
            "return_type": None,
        }

    try:
        return _run_mypy_extraction(source, func_id)
    except Exception as exc:
        return {
            "extraction_status": "failed",
            "extraction_notes": [
                f"mypy extraction raised an unexpected error: {exc}",
                "local variable types: not extracted (see module docstring)",
            ],
            "func_type": None,
            "params": [],
            "return_type": None,
        }


def _run_mypy_extraction(source: str, func_id: str) -> dict:
    """Inner implementation — may raise; caller catches."""
    from mypy.options import Options
    from mypy.build import build, BuildSource
    import mypy.nodes as mn

    opts = Options()
    opts.incremental = False
    opts.ignore_missing_imports = True
    # Silence all output; we only want the type data.
    opts.no_silence_site_packages = False

    # Write source to a temp directory so mypy can resolve the module.
    tmpdir = tempfile.mkdtemp()
    try:
        fname = f"{func_id}.py"
        fpath = os.path.join(tmpdir, fname)
        Path(fpath).write_text(source, encoding="utf-8")

        sources = [BuildSource(fpath, func_id, None)]
        result = build(sources, opts)

        mypy_file = result.files.get(func_id)
        if mypy_file is None:
            return {
                "extraction_status": "failed",
                "extraction_notes": [
                    f"mypy did not produce a file entry for module '{func_id}'",
                    "local variable types: not extracted (see module docstring)",
                ],
                "func_type": None,
                "params": [],
                "return_type": None,
            }

        # Find the single top-level function definition.
        func_def = None
        for name, sym in mypy_file.names.items():
            if name.startswith("__"):
                continue
            if isinstance(sym.node, mn.FuncDef):
                func_def = sym.node
                break

        if func_def is None:
            return {
                "extraction_status": "failed",
                "extraction_notes": [
                    "mypy found no top-level FuncDef in the module",
                    "local variable types: not extracted (see module docstring)",
                ],
                "func_type": None,
                "params": [],
                "return_type": None,
            }

        # Extract parameter types.
        params = []
        any_null = False
        for arg in func_def.arguments:
            t = _serialize_type(arg.variable.type)
            if t is None:
                any_null = True
            params.append({
                "name": arg.variable.name,
                "mypy_type": t,
                "has_explicit_annotation": arg.variable.type is not None,
            })

        # Extract return type.
        return_type = None
        if func_def.type is not None and hasattr(func_def.type, "ret_type"):
            return_type = _serialize_type(func_def.type.ret_type)
        if return_type is None:
            any_null = True

        # Full function type string.
        func_type_str = _serialize_type(func_def.type)

        status = "partial" if any_null else "ok"
        notes = ["local variable types: not extracted (see module docstring)"]

        return {
            "extraction_status": status,
            "extraction_notes": notes,
            "func_type": func_type_str,
            "params": params,
            "return_type": return_type,
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# File-level operations
# ---------------------------------------------------------------------------

def convert_file(ast_path: Path, raw_dir: Path, typed_ast_dir: Path) -> dict:
    """Convert one ast-v1 JSON file to a typed_ast-v1 JSON file.

    Returns a result dict: func_id, status, output_path, error.
    """
    func_id = ast_path.stem
    raw_path = raw_dir / f"{func_id}.py"

    # Load the C2 artifact.
    try:
        c2 = json.loads(ast_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"func_id": func_id, "status": "error", "output_path": None,
                "error": f"failed to read ast artifact: {exc}"}

    # Read raw source.
    if not raw_path.exists():
        return {"func_id": func_id, "status": "error", "output_path": None,
                "error": f"raw source not found: {raw_path}"}

    source = raw_path.read_text(encoding="utf-8")

    # Verify source_hash matches the C2 artifact to catch stale data.
    import hashlib
    actual_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if actual_hash != c2.get("source_hash"):
        return {"func_id": func_id, "status": "error", "output_path": None,
                "error": (f"source_hash mismatch: raw source has changed since "
                          f"ast artifact was generated. Re-run text_to_ast.py first.")}

    # Extract type info.
    type_info = extract_type_info(source, func_id)

    artifact = {
        "lumen_schema": SCHEMA_VERSION,
        "func_id": func_id,
        "source_hash": c2["source_hash"],
        "mypy_version": _mypy_version(),
        "type_info": type_info,
        "ast": c2["ast"],
    }

    out_path = typed_ast_dir / f"{func_id}.json"
    out_path.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "func_id": func_id,
        "status": type_info["extraction_status"],  # ok / partial / failed
        "output_path": str(out_path),
        "error": (type_info["extraction_notes"][0]
                  if type_info["extraction_status"] == "failed" else None),
    }


def main() -> None:
    """Batch-convert all ast-v1 files to typed_ast-v1.

    Exits with code 1 if any file fails.
    """
    repo_root = Path(__file__).resolve().parents[2]
    ast_dir = repo_root / "data" / "functions" / "ast"
    raw_dir = repo_root / "data" / "functions" / "raw"
    typed_ast_dir = repo_root / "data" / "functions" / "typed_ast"

    if not ast_dir.exists():
        print(f"ERROR: {ast_dir} does not exist.", file=sys.stderr)
        sys.exit(1)

    typed_ast_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(ast_dir.glob("*.json"))
    if not json_files:
        print("No .json files found in data/functions/ast/")
        return

    results = [convert_file(f, raw_dir, typed_ast_dir) for f in json_files]

    ok = [r for r in results if r["status"] == "ok"]
    partial = [r for r in results if r["status"] == "partial"]
    failed = [r for r in results if r["status"] in ("failed", "error")]

    for r in results:
        if r["status"] == "ok":
            print(f"  [ok]      {r['func_id']} -> {r['output_path']}")
        elif r["status"] == "partial":
            print(f"  [partial] {r['func_id']} -> {r['output_path']} (some types null)")
        else:
            print(f"  [failed]  {r['func_id']}: {r['error']}")

    print(f"\n{len(ok)} ok, {len(partial)} partial, {len(failed)} failed.")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
