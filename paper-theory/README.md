# paper-theory — Theory Companion Paper

Theory-first companion to the frozen empirical preprint (`preprint-v1`).
Governed by [`docs/theory-paper-charter.md`](../docs/theory-paper-charter.md).
This manuscript is **separate** from the empirical paper under `paper/`; it
does not modify the Constitution, scorers, runners, datasets, or frozen
analysis scripts.

**Working title:** *Structured Representation for Code LLMs: When Format Can
and Cannot Help a Bounded Learner, and Why.*

## Status

`ARXIV-READY` (T4-4, WOV-277). The manuscript compiles end to end with all
theorem cross-references resolving. Every section is drafted: the abstract,
§1 (introduction), the mathematical spine §2–§8, §9 (related work, T4-2),
§10 (limitations and honesty — the integrity gate, T4-3), §11 (conclusion),
and the appendix proofs. The internal red-team against overclaim (T4-3) has
been run; its checklist and findings are recorded in §10. T4-4 is complete:
the independent proof-check (60 formal environments + 5 predictions, ledger in
[`PROOF-CHECK.md`](PROOF-CHECK.md)) found all results sound with four
proof-hygiene fixes applied; the notation / cross-reference / table-consistency
pass is done (all labels unique, all references resolve, no raw-symbol drift);
and the arXiv submission metadata and packaging are fixed in
[`ARXIV.md`](ARXIV.md) (primary `cs.LG`, cross-list `stat.ML` / `cs.SE`).

## Layout

```
paper-theory/
  main.tex            # document root: packages, theorem envs, spine
  notation.tex        # single source of truth for symbols (all four areas)
  theory.bib          # bibliography (starts near-empty; G5 citation hygiene)
  sections/
    01-introduction.tex .. 11-conclusion.tex
    appendix-proofs.tex
  README.md
```

Section files map 1:1 onto the charter §4 spine and the §6 issue map, so each
T1/T2 issue edits one file.

## Go/no-go sections

`§3` (category theory, T1-4→T2-3) and `§6` (OT + information geometry,
T1-5→T2-5) are provisional. Each carries a `\gonogo{...}` banner and survives
only if it earns a theorem (charter §2). The decision is recorded in the
corresponding T2 Linear issue.

## Honesty guardrails (binding)

G1–G6 from charter §3 are enforced in-source: `\idealization{...}` discloses
every use of the irrelevance theorem (G3), `\gonogo{...}` marks the
provisional sections (G4), and the bib header restates citation hygiene (G5).
T4-3 (`§10`) is the integrity gate and must not be skipped.

## Build

Primary tool is [tectonic](https://tectonic-typesetting.github.io/)
(self-contained, resolves `natbib`/`bibtex` automatically):

```sh
make theory-paper        # from repo root
# or directly:
cd paper-theory && tectonic main.tex
```

Fallback with a TeX Live install:

```sh
cd paper-theory && pdflatex main && bibtex main && pdflatex main && pdflatex main
```

Output: `paper-theory/main.pdf`.

## arXiv packaging

```sh
make theory-paper-arxiv   # from repo root
```

Builds the PDF, emits the resolved `main.bbl` (arXiv runs LaTeX but not
bibtex), and assembles a self-contained source tarball at
`paper-theory/dist/theory-arxiv.tar.gz`. Submission categories, license, and
the empirical-anchor linkage are documented in [`ARXIV.md`](ARXIV.md).
