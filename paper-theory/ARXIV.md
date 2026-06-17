# arXiv submission metadata — theory companion paper

This file is the single source of truth for the arXiv submission of the theory
companion paper (`paper-theory/`). It records the packaging decisions made in
**WOV-277 (T4-4), step 3** so the submission form can be filled without
re-deriving anything. It is shipped inside the source tarball for provenance;
arXiv ignores it during compilation.

## Title

> Structured Representation for Code LLMs: When Format Can and Cannot Help a
> Bounded Learner, and Why

## Authors

Takumi Shiraishi (Independent Researcher) — `takumi@wovol.com`

## Categories

| Role | Category | Reason |
|---|---|---|
| **Primary** | `cs.LG` | The spine is information theory + statistical learning theory (charter §4); the central results are a data-processing / sufficiency argument and a capacity-budget bound on the bounded-learner gap. |
| Cross-list | `stat.ML` | Same theory read statistically (sufficiency, rate–distortion, Fisher-local parity defect). |
| Cross-list | `cs.SE` | The object of study is the representation of *code* for LLMs; the empirical anchor is a software-engineering apparatus (the Lumen C-ladder). |

Decision (charter §0 left the primary "to be decided in T4-4", candidates
cs.LG / stat.ML / cs.SE): **primary `cs.LG`**, cross-list `stat.ML` and `cs.SE`.
The paper is ML-theory flavored, so cs.LG is the home list; the other two are
the audiences it must reach.

## License

arXiv non-exclusive license to distribute (`arXiv perpetual, non-exclusive
license 1.0`). This matches the empirical companion's intended arXiv release:
the Lumen repository code is MIT-licensed (`/LICENSE`), and no broader content
license (e.g. CC BY) is asserted for either manuscript unless the empirical
preprint adopts one first — at which point this file is updated to match so the
two stay consistent.

## Comments (arXiv "Comments" field)

> Theoretical companion to the frozen empirical Lumen preprint (`preprint-v1`),
> which supplies the C-ladder, the three pre-registered outcomes (T1 null, T3
> ceiling, Holm-absorbed T2), and the R4 recovery profile. This paper imports
> three numbers and produces none. Companion preprint arXiv identifier to be
> inserted here once it is posted; until then the empirical anchor is referred
> to by its internal label `preprint-v1` (see §1.x and §7).

## Empirical anchor linkage

The empirical record is referenced throughout as `\texttt{preprint-v1}`
(§1 "Relationship to the empirical preprint", §7 "Empirical anchoring"). It is
**not** yet public, so no arXiv ID / DOI / URL is cited — fabricating one would
violate citation hygiene (charter G5). When the empirical preprint is posted:
1. add its arXiv entry to `theory.bib`,
2. replace the first-mention `\texttt{preprint-v1}` with a `\citep{...}`,
3. fill the arXiv identifier into the Comments field above.

## MSC / ACM classification (optional fields)

- ACM: `I.2.6` (Learning), `F.4.1` (Mathematical Logic / formal methods flavor for §3).
- MSC 2020: `68T05` (Learning and adaptive systems), `94A17` (Measures of information, entropy).

## Build / packaging

```sh
make theory-paper-arxiv      # from repo root
```

Produces `paper-theory/dist/theory-arxiv.tar.gz`, a self-contained source tree:

```
main.tex  notation.tex  theory.bib  main.bbl  ARXIV.md  sections/*.tex
```

`main.bbl` is included because arXiv runs LaTeX but **not** bibtex. No figures
are used (the manuscript is text + tables only), so the tree has no external
asset dependencies. The tarball builds with `tectonic main.tex` and with a
standard TeX Live `pdflatex` + the shipped `.bbl`.
