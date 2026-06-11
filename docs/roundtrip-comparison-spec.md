# Round-trip comparison-normalization spec (R4-1)

Linear: WOV-243 (R4-1 / W-03); paper §3.3 + Appendix D. Defines exactly what
"the same node / clause / type" means when comparing C4 against the
re-derived C4′. Implementation: `src/experiment/roundtrip.py`.

## Round trip

```
C4 (data/functions/ir/{func_id}.json)
  → C1+   render_function(ir)               # pipeline.ir_to_annotated_text
  → C4′   from the C1+ TEXT ONLY:
            AST       = parse_function(c1plus)            # pipeline.text_to_ast
            contracts = parse_contracts_from_docstring(c1plus)   # roundtrip.py
            types     = annotations recovered from the C1+ AST
```

`parse_contracts_from_docstring` is required because the production
`typed_ast_to_ir` reads the *authoritative reviewed contract*, not the C1+
docstring; a text-only round trip must recover contracts from the docstring.

## "Same node" / normalization rules

- **AST node** identity = its `_type` string (the dict key emitted by
  `text_to_ast._node_to_dict`). Comparisons are over the AST-as-dict, not live
  `ast` objects.
- **node-kind retention** = multiset overlap fraction
  `Σ_k min(count_C4(k), count_C4′(k)) / Σ_k count_C4(k)` over `_type` values.
  Extra kinds in C4′ (e.g. the docstring `Expr`/`Constant` that C1+ introduces)
  do not lower it; only *missing* C4 kinds do.
- **parent–child retention** = the same multiset-overlap fraction over labeled
  edges `(parent._type, child._type)` for every dict→(dict|list-of-dict) link.
- **type-annotation retention** = fraction of the reference set
  `{(param_name, base_type)} ∪ {("__return__", base_type)}` recovered, where
  `base_type` strips module/`builtins.` prefixes and any `[...]` generic args
  (e.g. `builtins.list[builtins.int]` → `list`; recovered annotation `list`).
- **contract-clause retention** = per kind (preconditions / postconditions /
  invariants, counted separately) the fraction of C4 clauses present in C4′,
  comparing clauses after whitespace-collapse + lowercase (`_norm_clause`).
- **cross-reference retention** = let `shared(clauses)` be the identifier
  tokens (`[A-Za-z_][A-Za-z0-9_]*`) occurring in ≥ 2 distinct contract clauses;
  retention = `|shared_C4 ∩ shared_C4′| / |shared_C4|`. This proxies the
  "cross-references between contract clauses" (shared variables/return refs).
- **canonical-hash agreement** = boolean: `sha256(json.dumps(ast, sort_keys))`
  equal for C4 and C4′. Because C1+ adds a structured docstring node, exact
  agreement is *expected to be False* for real functions even when every
  retention metric is 1.0 — the flag isolates "byte-identical AST" from
  "structure recovered".

Empty reference sets return retention 1.0 (vacuously perfect); a `- None.`
docstring bullet parses to an empty contract list.

## Interpreting the metrics

High retention with `canonical_hash_agreement = false` is the typical C1+
result: the *content* survives (kinds, edges, types, clauses) but the IR is not
byte-reconstructible, consistent with the §3.3 disclosure that C1+ is a
lossy-but-information-preserving projection. The aggregate over all 30 functions
is the R4-2 deliverable (Appendix D).
