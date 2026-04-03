"""Render ir-v1 artifacts to C1+ annotated Python source text.

Reads:
  data/functions/ir/{func_id}.json             (C4 — ir-v1 artifact)

Writes:
  data/functions/annotated_text/{func_id}.py   (C1+ — annotated Python source)

Output schema: annotated Python source file with:
  - PEP 484 inline type annotations derived from ir-v1 type_info
  - a structured docstring with Preconditions / Postconditions / Invariants
    derived from ir-v1 contracts
  - function body reconstructed verbatim from ir-v1 ast

This stage corresponds to condition C1+ in the study.

C1+ is the required information-parity control for C4: the same type and
contract information expressed as Python source text with inline annotations
and a structured docstring.  Format differs from C4; semantic content is
identical.

The ir-v1 artifact is the ONLY authoritative input for this renderer.
This module must NOT read raw contracts, reviewed contracts, diff contracts,
or any other supervision artifact at render time.

Scope constraints (from design constitution §4):
  - Non-recursive, single-function Python only.
  - No class analysis.
  - No multi-file generalization.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IR_SCHEMA = "ir-v1"

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

IR_DIR = _REPO_ROOT / "data" / "functions" / "ir"
ANNOTATED_TEXT_DIR = _REPO_ROOT / "data" / "functions" / "annotated_text"

_INDENT = "    "
_BUILTIN_PREFIX = "builtins."

# ---------------------------------------------------------------------------
# Type annotation helpers
# ---------------------------------------------------------------------------


def _strip_builtin_prefix(mypy_type: str) -> str:
    """Strip the 'builtins.' module prefix from a mypy type string.

    'builtins.float'     -> 'float'
    'builtins.list[Any]' -> 'list[Any]'
    'str'                -> 'str'  (no-op if prefix absent)
    """
    rendered = mypy_type.replace(_BUILTIN_PREFIX, "")
    if rendered == "NoneType":
        return "None"

    # mypy can emit callable signatures like:
    #   def (*Any, **Any) -> Any | None
    # Convert them to a valid Python typing form.
    m = re.match(r"^def\s*\(.*\)\s*->\s*(.+)$", rendered)
    if m:
        return_type = m.group(1).strip().replace("NoneType", "None")
        return f"Callable[..., {return_type}]"

    return rendered


def _collect_rendered_types(type_info: dict) -> list[str]:
    """Return all rendered (prefix-stripped) type strings for a function."""
    types: list[str] = []
    for p in type_info.get("params", []):
        mt = p.get("mypy_type") or ""
        if mt:
            types.append(_strip_builtin_prefix(mt))
    rt = type_info.get("return_type") or ""
    if rt:
        types.append(_strip_builtin_prefix(rt))
    return types


# ---------------------------------------------------------------------------
# IR loading and validation
# ---------------------------------------------------------------------------


def _load_ir(func_id: str) -> dict:
    path = IR_DIR / f"{func_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"IR artifact not found: {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _validate_ir(ir: dict, func_id: str) -> None:
    """Raise ValueError for any ir-v1 validation failure relevant to rendering."""
    if not isinstance(ir, dict):
        raise ValueError("IR artifact is not a JSON object.")
    schema = ir.get("lumen_schema")
    if schema != IR_SCHEMA:
        raise ValueError(f"Expected lumen_schema '{IR_SCHEMA}', got '{schema}'.")
    for key in ("func_id", "source_hash", "type_info", "contracts", "ast"):
        if key not in ir:
            raise ValueError(f"IR missing required field: '{key}'.")
    if ir["func_id"] != func_id:
        raise ValueError(
            f"IR func_id '{ir['func_id']}' does not match expected '{func_id}'."
        )

    # type_info
    ti = ir["type_info"]
    if not isinstance(ti, dict):
        raise ValueError("IR type_info is not an object.")
    if not isinstance(ti.get("params"), list):
        raise ValueError("IR type_info 'params' is missing or not a list.")
    if "return_type" not in ti:
        raise ValueError("IR type_info missing 'return_type'.")
    for p in ti["params"]:
        if not isinstance(p, dict) or "name" not in p or "mypy_type" not in p:
            raise ValueError(f"IR type_info param is malformed: {p!r}")

    # contracts
    c = ir["contracts"]
    if not isinstance(c, dict):
        raise ValueError("IR contracts is not an object.")
    for key in ("preconditions", "postconditions", "invariants"):
        if not isinstance(c.get(key), list):
            raise ValueError(f"IR contracts '{key}' is missing or not a list.")
    if not c["postconditions"]:
        raise ValueError("IR contracts postconditions is empty — not a valid C4 input.")

    # ast
    ir_ast = ir["ast"]
    if not isinstance(ir_ast, dict) or ir_ast.get("_type") != "Module":
        raise ValueError("IR ast is not a Module node.")
    body = ir_ast.get("body", [])
    if not body or not isinstance(body, list):
        raise ValueError("IR ast body is missing or malformed.")
    fdef = None
    for node in body:
        if isinstance(node, dict) and node.get("_type") == "FunctionDef":
            fdef = node
            break
    if fdef is None:
        raise ValueError("IR ast body has no FunctionDef node.")
    if fdef.get("name") != func_id:
        raise ValueError(
            f"IR ast FunctionDef name '{fdef.get('name')}' "
            f"does not match func_id '{func_id}'."
        )


# ---------------------------------------------------------------------------
# AST dict -> Python ast object reconstruction
# ---------------------------------------------------------------------------


def _dict_to_ast_node(node: object) -> object:
    """Recursively convert an ir-v1 AST dict back to a Python ast.AST object.

    The dict representation uses '_type' for the AST node class name and
    stores all field values as nested dicts, lists, or scalars.  This mirrors
    the serialization produced by text_to_ast.py.

    Fails loudly on any unknown node type to prevent silent mis-rendering.
    Only nodes present in the current pilot scope (non-recursive,
    single-function Python) are expected.
    """
    if isinstance(node, dict):
        type_name = node.get("_type")
        if type_name is None:
            raise ValueError(
                f"AST node dict has no '_type'. Keys: {list(node.keys())[:8]}"
            )
        cls = getattr(ast, type_name, None)
        if cls is None:
            raise ValueError(f"Unsupported AST node type: '{type_name}'")
        kwargs = {k: _dict_to_ast_node(v) for k, v in node.items() if k != "_type"}
        return cls(**kwargs)
    elif isinstance(node, list):
        return [_dict_to_ast_node(item) for item in node]
    else:
        # Scalar: int, float, str, bool, None — pass through unchanged.
        return node


# ---------------------------------------------------------------------------
# Signature rendering
# ---------------------------------------------------------------------------


def _render_signature(func_id: str, type_info: dict) -> str:
    """Return the 'def func_id(... : ...) -> ...:' line from ir-v1 type_info.

    Uses mypy_type from type_info.params for parameter annotations and
    return_type for the return annotation.  The 'builtins.' prefix is stripped
    to produce standard PEP 484 annotations.
    """
    param_parts: list[str] = []
    for p in type_info["params"]:
        name: str = p["name"]
        mypy_type: str = p.get("mypy_type") or ""
        if mypy_type:
            param_parts.append(f"{name}: {_strip_builtin_prefix(mypy_type)}")
        else:
            param_parts.append(name)

    return_type: str = type_info.get("return_type") or ""
    return_annotation = (
        f" -> {_strip_builtin_prefix(return_type)}" if return_type else ""
    )
    return f"def {func_id}({', '.join(param_parts)}){return_annotation}:"


# ---------------------------------------------------------------------------
# Contract docstring rendering
# ---------------------------------------------------------------------------


def _render_contract_docstring(contracts: dict) -> str:
    """Render the structured C1+ contract docstring from ir-v1 contracts.

    Always emits Preconditions / Postconditions / Invariants in that order.
    Empty sections render as '- None.' per the C1+ template rules.
    Clause wording is copied verbatim from ir-v1; no paraphrasing.

    Raises ValueError if any clause contains triple-double-quotes, which would
    produce invalid Python syntax.
    """
    sections = (
        ("Preconditions", contracts["preconditions"]),
        ("Postconditions", contracts["postconditions"]),
        ("Invariants", contracts["invariants"]),
    )

    lines: list[str] = [f'{_INDENT}"""']

    for section_name, clauses in sections:
        lines.append(f"{_INDENT}{section_name}:")
        if clauses:
            for clause in clauses:
                if '"""' in clause:
                    raise ValueError(
                        f"Contract clause contains triple-double-quotes which "
                        f"would break the docstring: {clause!r}"
                    )
                lines.append(f"{_INDENT}- {clause}")
        else:
            lines.append(f"{_INDENT}- None.")
        lines.append("")  # blank separator between sections

    # Remove the last trailing blank line before closing the docstring.
    if lines and lines[-1] == "":
        lines.pop()
    lines.append(f'{_INDENT}"""')

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Body statement rendering
# ---------------------------------------------------------------------------


def _is_str_expr_node(node_dict: dict) -> bool:
    """Return True if node_dict is a bare string-expression node (i.e. a docstring)."""
    return (
        node_dict.get("_type") == "Expr"
        and isinstance(node_dict.get("value"), dict)
        and node_dict["value"].get("_type") == "Constant"
        and isinstance(node_dict["value"].get("value"), str)
    )


def _render_body_statements(func_def_dict: dict) -> list[str]:
    """Return indented source lines for all body statements except the leading docstring.

    The original docstring is excluded because it is non-authoritative for
    C1+ output.  The structured contract docstring takes its place.

    Uses ast.unparse() to serialise each reconstructed AST statement node.
    Each statement's output lines are indented by _INDENT (4 spaces).
    """
    body: list[dict] = func_def_dict.get("body", [])

    # Skip the leading docstring node if present.
    start = 1 if (body and _is_str_expr_node(body[0])) else 0
    remaining = body[start:]

    if not remaining:
        raise ValueError(
            f"Function '{func_def_dict.get('name')}' has no body statements "
            "after stripping the original docstring."
        )

    output_lines: list[str] = []
    for stmt_dict in remaining:
        stmt_node = _dict_to_ast_node(stmt_dict)
        # Python 3.11 ast.unparse() accesses node.lineno via get_type_comment().
        # fix_missing_locations() sets default line numbers on any node that
        # lacks them; accuracy is irrelevant since we only need valid Python text.
        ast.fix_missing_locations(stmt_node)
        stmt_src = ast.unparse(stmt_node)
        # Each statement may span multiple lines (e.g. for/if blocks).
        # Add _INDENT prefix to every line.
        for line in stmt_src.splitlines():
            output_lines.append(f"{_INDENT}{line}")

    return output_lines


# ---------------------------------------------------------------------------
# Top-level render function
# ---------------------------------------------------------------------------


def render_function(ir: dict) -> str:
    """Render one validated ir-v1 artifact to a C1+ Python source string.

    Projection rules:
    - Imports: 'from typing import Any' only when 'Any' appears in rendered types.
    - Signature: parameter/return types from type_info, 'builtins.' stripped.
    - Docstring: structured Preconditions/Postconditions/Invariants from contracts.
    - Body: reconstructed from ir-v1 ast, with original docstring excluded.

    This function does not call _validate_ir(); callers are responsible for
    pre-validating the artifact before calling render_function().
    """
    func_id: str = ir["func_id"]
    type_info: dict = ir["type_info"]
    contracts: dict = ir["contracts"]
    module_body: list[dict] = ir["ast"]["body"]  # pre-validated in _validate_ir

    leading_imports: list[dict] = []
    func_def_dict: dict | None = None
    for node in module_body:
        if node.get("_type") in {"Import", "ImportFrom"} and func_def_dict is None:
            leading_imports.append(node)
            continue
        if node.get("_type") == "FunctionDef":
            func_def_dict = node
            break
    if func_def_dict is None:
        raise ValueError("IR ast body has no FunctionDef node for rendering.")

    # Determine if 'from typing import Any' is needed.
    rendered_types = _collect_rendered_types(type_info)
    needs_any_import = any("Any" in t for t in rendered_types)

    lines: list[str] = []

    for imp_dict in leading_imports:
        imp_node = _dict_to_ast_node(imp_dict)
        ast.fix_missing_locations(imp_node)
        lines.append(ast.unparse(imp_node))

    if needs_any_import:
        if lines:
            lines.append("")
        lines.append("from typing import Any")
        lines.append("")

    lines.append(_render_signature(func_id, type_info))
    lines.append(_render_contract_docstring(contracts))
    lines.extend(_render_body_statements(func_def_dict))

    # Join with newlines and ensure a single trailing newline.
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Parse-check
# ---------------------------------------------------------------------------


def _parse_check(source: str, func_id: str) -> None:
    """Raise ValueError if the generated source is not valid Python."""
    try:
        ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(
            f"Generated source for '{func_id}' failed Python parse check: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# File-level entry point
# ---------------------------------------------------------------------------


def convert_file(func_id: str) -> Path:
    """Load, validate, render, parse-check, and write one C1+ annotated text file.

    Returns the path of the written .py file.
    """
    ir = _load_ir(func_id)
    _validate_ir(ir, func_id)

    source = render_function(ir)
    _parse_check(source, func_id)

    ANNOTATED_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ANNOTATED_TEXT_DIR / f"{func_id}.py"
    out_path.write_text(source, encoding="utf-8")
    print(f"  [{func_id}] saved → {out_path}", file=sys.stderr)
    return out_path


# ---------------------------------------------------------------------------
# Batch entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point: render all ir-v1 artifacts to C1+ annotated text."""
    func_ids = sorted(p.stem for p in IR_DIR.glob("*.json"))
    if not func_ids:
        print("No ir-v1 artifacts found in IR_DIR.", file=sys.stderr)
        sys.exit(1)

    print(f"Rendering C1+ annotated text for: {func_ids}", file=sys.stderr)
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
        print("\nAll C1+ annotated text files written successfully.", file=sys.stderr)


if __name__ == "__main__":
    main()
