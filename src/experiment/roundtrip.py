"""C4 -> C1+ -> C4' round-trip recovery metrics (R4-1 / W-03; paper Appendix D).

Measures how much of the Core IR (C4) survives projection to information-parity
annotated text (C1+) and re-derivation back to IR (C4'). This operationalises
the §3.3 disclosure that C1+ does not preserve all C4 structure.

Pipeline
--------
    C4  = data/functions/ir/{func_id}.json
      -> C1+  via pipeline.ir_to_annotated_text.render_function (annotated source
              + structured Preconditions/Postconditions/Invariants docstring)
      -> C4'  by re-deriving ONLY from the C1+ text:
                 * AST   via pipeline.text_to_ast.parse_function (C1+ source)
                 * contracts via parse_contracts_from_docstring (THIS module —
                   the existing typed_ast_to_ir reads the authoritative reviewed
                   contract, not the docstring, so a docstring->contract parser
                   is required for a faithful text-only round trip)
                 * types via the C1+ annotations recovered from the AST
      -> compare C4 vs C4'

Comparison normalization is specified in docs/roundtrip-comparison-spec.md.
This module reads only C4 IR + the C1+ projection; it never consults the
reviewed contract, so it measures genuine text->structure recovery. It does not
modify any frozen artifact.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
_PIPELINE = REPO_ROOT / "src" / "pipeline"
for _p in (str(REPO_ROOT / "src"), str(_PIPELINE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from pipeline.ir_to_annotated_text import render_function  # noqa: E402
from pipeline.text_to_ast import parse_function  # noqa: E402

SCHEMA = "roundtrip-recovery-v1"
_CONTRACT_KINDS = ("preconditions", "postconditions", "invariants")


# ---------------------------------------------------------------------------
# Docstring -> contract parser (required; see module docstring)
# ---------------------------------------------------------------------------

_SECTION_HEADERS = {
    "preconditions:": "preconditions",
    "postconditions:": "postconditions",
    "invariants:": "invariants",
}


def parse_contracts_from_docstring(source: str) -> dict[str, list[str]]:
    """Recover {preconditions, postconditions, invariants} from a C1+ docstring.

    The C1+ docstring uses ``Preconditions:`` / ``Postconditions:`` /
    ``Invariants:`` headers followed by ``- clause`` bullets; an empty section
    is rendered as a single ``- None.`` bullet (parsed to an empty list).
    """
    import ast as _ast

    out: dict[str, list[str]] = {k: [] for k in _CONTRACT_KINDS}
    try:
        tree = _ast.parse(source)
    except SyntaxError:
        return out
    doc = None
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            doc = _ast.get_docstring(node, clean=True)
            break
    if not doc:
        return out

    current: str | None = None
    for raw in doc.splitlines():
        line = raw.strip()
        if not line:
            continue
        header = _SECTION_HEADERS.get(line.lower())
        if header is not None:
            current = header
            continue
        if current and line.startswith("-"):
            clause = line[1:].strip()
            if clause and clause.lower() not in ("none.", "none"):
                out[current].append(clause)
    return out


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _node_kinds(node: Any, acc: list[str]) -> None:
    if isinstance(node, dict):
        if "_type" in node:
            acc.append(node["_type"])
        for v in node.values():
            _node_kinds(v, acc)
    elif isinstance(node, list):
        for v in node:
            _node_kinds(v, acc)


def _labeled_edges(node: Any, acc: list[tuple[str, str]]) -> None:
    """Parent-kind -> child-kind edges over the AST-as-dict."""
    if isinstance(node, dict):
        parent = node.get("_type")
        for v in node.values():
            if isinstance(v, dict) and "_type" in v and parent:
                acc.append((parent, v["_type"]))
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict) and "_type" in item and parent:
                        acc.append((parent, item["_type"]))
            _labeled_edges(v, acc)
    elif isinstance(node, list):
        for v in node:
            _labeled_edges(v, acc)


def _func_def(ast_dict: dict) -> dict | None:
    for node in ast_dict.get("body", []):
        if isinstance(node, dict) and node.get("_type") in ("FunctionDef", "AsyncFunctionDef"):
            return node
    return None


def _annotation_base(ann: Any) -> str | None:
    """Base type name from an annotation node: Name.id, Subscript value base,
    or Attribute attr. (e.g. ``list[int]`` -> ``list``, ``t.List`` -> ``List``).
    Mirrors _base_type's "strip generics/prefix" normalization on the AST side."""
    if not isinstance(ann, dict):
        return None
    kind = ann.get("_type")
    if kind == "Name":
        return ann.get("id")
    if kind == "Subscript":
        return _annotation_base(ann.get("value"))
    if kind == "Attribute":
        return ann.get("attr")
    if kind == "Constant" and ann.get("value") is None:
        return "None"
    return None


def _recovered_type_info(ast_dict: dict) -> dict[str, Any]:
    """Recover param->annotation and return annotation from a C1+ AST."""
    fd = _func_def(ast_dict)
    if fd is None:
        return {"params": {}, "return_type": None}
    args = fd.get("args", {}).get("args", [])
    params: dict[str, str] = {}
    for a in args:
        base = _annotation_base(a.get("annotation"))
        if base is not None:
            params[a["arg"]] = base
    return {"params": params, "return_type": _annotation_base(fd.get("returns"))}


def _base_type(mypy_type: str) -> str:
    """builtins.float -> float; strip module prefixes for comparison."""
    t = (mypy_type or "").split("[")[0].strip()
    return t.rsplit(".", 1)[-1]


# ---------------------------------------------------------------------------
# Clause / cross-reference normalization
# ---------------------------------------------------------------------------

def _norm_clause(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _shared_identifiers(clauses: list[str]) -> set[str]:
    """Identifier tokens that appear in >=2 distinct clauses (cross-refs)."""
    from collections import Counter

    per_clause_sets = [set(_IDENT.findall(c.lower())) for c in clauses]
    counts: Counter = Counter()
    for s in per_clause_sets:
        counts.update(s)
    return {tok for tok, n in counts.items() if n >= 2}


def _retention(reference: set, recovered: set) -> float:
    if not reference:
        return 1.0
    return len(reference & recovered) / len(reference)


def _multiset_retention(ref: list, rec: list) -> float:
    from collections import Counter

    cref, crec = Counter(ref), Counter(rec)
    if not cref:
        return 1.0
    overlap = sum(min(n, crec.get(k, 0)) for k, n in cref.items())
    return overlap / sum(cref.values())


# ---------------------------------------------------------------------------
# Round trip
# ---------------------------------------------------------------------------

def _ast_hash(ast_dict: dict) -> str:
    # default=repr keeps the hash total over non-JSON literals (e.g. Ellipsis).
    return hashlib.sha256(
        json.dumps(ast_dict, sort_keys=True, ensure_ascii=False, default=repr).encode("utf-8")
    ).hexdigest()


def roundtrip_recover(ir: dict) -> dict[str, Any]:
    """C4 -> C1+ -> C4'. Returns the C1+ text and the recovered C4' fields."""
    c1plus = render_function(ir)
    ast_prime = parse_function(c1plus)
    contracts_prime = parse_contracts_from_docstring(c1plus)
    type_info_prime = _recovered_type_info(ast_prime)
    return {"c1plus": c1plus, "ast": ast_prime,
            "contracts": contracts_prime, "type_info": type_info_prime}


def recovery_metrics(ir: dict, recovered: dict) -> dict[str, Any]:
    c4_ast, c4p_ast = ir["ast"], recovered["ast"]

    # 1. node-kind retention
    kref: list[str] = []; _node_kinds(c4_ast, kref)
    krec: list[str] = []; _node_kinds(c4p_ast, krec)
    node_kind = _multiset_retention(kref, krec)

    # 2. type-annotation retention (params + return)
    c4_params = {p["name"]: _base_type(p.get("mypy_type", "")) for p in ir.get("type_info", {}).get("params", [])}
    c4_ret = _base_type(ir.get("type_info", {}).get("return_type", ""))
    rec_params = recovered["type_info"]["params"]
    rec_ret = recovered["type_info"]["return_type"] or ""
    ref_type = set(c4_params.items()) | {("__return__", c4_ret)}
    rec_type = set(rec_params.items()) | {("__return__", rec_ret)}
    type_ann = _retention(ref_type, rec_type)

    # 3. contract-clause retention (pre/post/invariant separately)
    contract_ret: dict[str, Any] = {}
    c4_contracts = ir.get("contracts", {})
    for kind in _CONTRACT_KINDS:
        ref = {_norm_clause(c) for c in c4_contracts.get(kind, [])}
        rec = {_norm_clause(c) for c in recovered["contracts"].get(kind, [])}
        contract_ret[kind] = _retention(ref, rec)

    # 4. parent-child structural retention (labeled-edge overlap)
    eref: list = []; _labeled_edges(c4_ast, eref)
    erec: list = []; _labeled_edges(c4p_ast, erec)
    edge_ret = _multiset_retention(eref, erec)

    # 5. cross-reference retention between contract clauses
    all_ref_clauses = [c for k in _CONTRACT_KINDS for c in c4_contracts.get(k, [])]
    all_rec_clauses = [c for k in _CONTRACT_KINDS for c in recovered["contracts"].get(k, [])]
    xref = _retention(_shared_identifiers(all_ref_clauses), _shared_identifiers(all_rec_clauses))

    # 6. canonical-hash agreement (exact AST match flag)
    hash_match = _ast_hash(c4_ast) == _ast_hash(c4p_ast)

    return {
        "node_kind_retention": round(node_kind, 6),
        "type_annotation_retention": round(type_ann, 6),
        "contract_clause_retention": {k: round(v, 6) for k, v in contract_ret.items()},
        "parent_child_retention": round(edge_ret, 6),
        "cross_reference_retention": round(xref, 6),
        "canonical_hash_agreement": hash_match,
    }


def run_func(func_id: str) -> dict[str, Any]:
    ir = json.loads((REPO_ROOT / "data" / "functions" / "ir" / f"{func_id}.json").read_text())
    recovered = roundtrip_recover(ir)
    metrics = recovery_metrics(ir, recovered)
    return {"lumen_schema": SCHEMA, "func_id": func_id, "metrics": metrics}


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="roundtrip", description="C4->C1+->C4' recovery metrics (R4-1).")
    parser.add_argument("--func-id", required=True, help="Function id (data/functions/ir/{func_id}.json).")
    parser.add_argument("--output-json", default=None)
    args = parser.parse_args(argv)

    result = run_func(args.func_id)
    text = json.dumps(result, indent=2)
    if args.output_json:
        Path(args.output_json).write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
