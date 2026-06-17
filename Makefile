# Lumen experiment runner — Makefile
#
# Prerequisites:
#   - .env file in the repo root with ANTHROPIC_API_KEY and OPENAI_API_KEY
#   - pip install -e . (or pip install anthropic)
#
# Common usage:
#   make summarize-candidates
#   make t2-screen-wave1 SCREEN_FUNC_IDS="my_func another_func"
#   make ingest-stage2
#   make t3-screen-wave1 SCREEN_FUNC_IDS="my_func"
#   make ingest-stage3

# ---------------------------------------------------------------------------
# Configurable defaults
# ---------------------------------------------------------------------------

# Model used for screening runs.  Override: make t2-screen-wave1 SCREEN_MODEL=claude-opus-4-6
SCREEN_MODEL ?= gpt-5.4

# Space-separated list of func_ids for screening.
# If empty, the wrapper auto-detects eligible candidates from the tracker.
SCREEN_FUNC_IDS ?=

# Run IDs for the two screening waves.
T2_SCREEN_RUN_ID ?= t2_screen_wave1
T3_SCREEN_RUN_ID ?= t3_screen_wave1

# ---------------------------------------------------------------------------
# Phony targets
# ---------------------------------------------------------------------------

.PHONY: t2-screen-wave1 t3-screen-wave1 \
        ingest-stage2 ingest-stage3 \
        summarize-candidates init-candidates \
        list-candidates validate-candidates \
        test theory-paper theory-paper-clean theory-paper-arxiv

# ---------------------------------------------------------------------------
# Candidate tracker tooling
# ---------------------------------------------------------------------------

init-candidates:
	PYTHONPATH=src python -m experiment.init_candidates --seed-anchors

summarize-candidates:
	PYTHONPATH=src python -m experiment.summarize_candidates

# Candidate management (manual intake and Stage 1 workflow)
# Add a candidate:  make add-candidate ID=my_func SOURCE="authored" LINES=14
# Update Stage 1:   make stage1 ID=my_func RESULT=PASS
#                   make stage1 ID=my_func RESULT=EXCLUDE REASON="Too trivial"
list-candidates:
	PYTHONPATH=src python -m experiment.manage_candidates list

validate-candidates:
	PYTHONPATH=src python -m experiment.manage_candidates validate

# ---------------------------------------------------------------------------
# Screening runs
#
# .env is sourced in the same shell as the python command so that API keys
# are available.  All recipe lines are joined with && so they run in a single
# shell process.
#
# If SCREEN_FUNC_IDS is not set, auto-detect from tracker.
# ---------------------------------------------------------------------------

t2-screen-wave1:
	@set -a && source .env && set +a && \
	if [ -z "$(SCREEN_FUNC_IDS)" ]; then \
	  FUNC_IDS=$$(PYTHONPATH=src python -m experiment.summarize_candidates --list stage2-eligible 2>/dev/null || true); \
	else \
	  FUNC_IDS="$(SCREEN_FUNC_IDS)"; \
	fi && \
	if [ -z "$$FUNC_IDS" ]; then \
	  echo "No Stage 2-eligible candidates found. Add and approve candidates first." >&2; exit 1; \
	fi && \
	echo "Running T2 C1 screen for: $$FUNC_IDS" && \
	PYTHONPATH=src python -m experiment.run_pilot \
	  --run-mode full \
	  --tasks T2 \
	  --conditions C1 \
	  --models $(SCREEN_MODEL) \
	  --run-id $(T2_SCREEN_RUN_ID) \
	  --func-ids $$FUNC_IDS

t3-screen-wave1:
	@set -a && source .env && set +a && \
	if [ -z "$(SCREEN_FUNC_IDS)" ]; then \
	  FUNC_IDS=$$(PYTHONPATH=src python -m experiment.summarize_candidates --list stage3-eligible 2>/dev/null || true); \
	else \
	  FUNC_IDS="$(SCREEN_FUNC_IDS)"; \
	fi && \
	if [ -z "$$FUNC_IDS" ]; then \
	  echo "No Stage 3-eligible candidates found. Run Stage 2 screen first." >&2; exit 1; \
	fi && \
	echo "Running T3 C2 screen for: $$FUNC_IDS" && \
	PYTHONPATH=src python -m experiment.run_pilot \
	  --run-mode full \
	  --tasks T3 \
	  --conditions C2 \
	  --models $(SCREEN_MODEL) \
	  --run-id $(T3_SCREEN_RUN_ID) \
	  --func-ids $$FUNC_IDS

# ---------------------------------------------------------------------------
# Result ingestion
# ---------------------------------------------------------------------------

ingest-stage2:
	PYTHONPATH=src python -m experiment.update_candidates_from_run \
	  --run-id $(T2_SCREEN_RUN_ID) \
	  --stage 2 \
	  --model $(SCREEN_MODEL)

ingest-stage3:
	PYTHONPATH=src python -m experiment.update_candidates_from_run \
	  --run-id $(T3_SCREEN_RUN_ID) \
	  --stage 3 \
	  --model $(SCREEN_MODEL)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

test:
	python3 -m unittest discover -s tests -v

# ---------------------------------------------------------------------------
# Theory companion paper (paper-theory/, WOV-261 T0-2)
#
# Builds the theory-paper skeleton to PDF. Prefers tectonic (self-contained,
# resolves natbib/bibtex automatically); falls back to a pdflatex+bibtex
# cycle if tectonic is absent.
# ---------------------------------------------------------------------------

theory-paper:
	@cd paper-theory && \
	if command -v tectonic >/dev/null 2>&1; then \
	  echo "Building with tectonic..." && tectonic main.tex; \
	elif command -v pdflatex >/dev/null 2>&1; then \
	  echo "tectonic not found; falling back to pdflatex+bibtex..." && \
	  pdflatex -interaction=nonstopmode main.tex && \
	  bibtex main || true && \
	  pdflatex -interaction=nonstopmode main.tex && \
	  pdflatex -interaction=nonstopmode main.tex; \
	else \
	  echo "No LaTeX engine found (need tectonic or pdflatex)." >&2; exit 1; \
	fi && \
	echo "Built paper-theory/main.pdf"

theory-paper-clean:
	@cd paper-theory && rm -f main.aux main.bbl main.blg main.log main.out \
	  main.toc main.pdf sections/*.aux
	@echo "Cleaned paper-theory build artifacts."

# ---------------------------------------------------------------------------
# Assembles a self-contained arXiv submission tarball (WOV-277, T4-4 step 3).
# arXiv runs its own LaTeX but does NOT run bibtex, so the resolved main.bbl
# must be shipped alongside the sources. tectonic --keep-intermediates emits
# it. Output: paper-theory/dist/theory-arxiv.tar.gz containing exactly the
# files arXiv needs (no .aux/.log/.pdf, no repo metadata).
# ---------------------------------------------------------------------------

theory-paper-arxiv:
	@command -v tectonic >/dev/null 2>&1 || { echo "tectonic required for arXiv packaging." >&2; exit 1; }
	@cd paper-theory && \
	  echo "Building + emitting main.bbl..." && \
	  tectonic --keep-intermediates main.tex >/dev/null && \
	  test -f main.bbl || { echo "main.bbl was not produced." >&2; exit 1; }
	@cd paper-theory && rm -rf dist && mkdir -p dist/theory-arxiv/sections && \
	  cp main.tex notation.tex theory.bib main.bbl dist/theory-arxiv/ && \
	  cp sections/*.tex dist/theory-arxiv/sections/ && \
	  cp ARXIV.md dist/theory-arxiv/ && \
	  ( cd dist && tar czf theory-arxiv.tar.gz theory-arxiv ) && \
	  rm -rf dist/theory-arxiv
	@echo "Wrote paper-theory/dist/theory-arxiv.tar.gz (self-contained arXiv source)."
