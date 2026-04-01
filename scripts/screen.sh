#!/usr/bin/env bash
# Lumen candidate management and screening helper script
#
# Usage:
#   ./scripts/screen.sh <command> [options]
#
# Candidate intake / Stage 1 (manual):
#   list                  List all candidates (add --state pending|pass-blocked|pass-ready|...)
#   add --id ID ...       Add a new candidate (use --help for full options)
#   update-stage1 ID ...  Set Stage 1 result (--result PASS|EXCLUDE|DEFER [--reason ...])
#   show ID               Show all details for one candidate
#   validate-candidates   Validate the tracker file
#
# Screening runs (automated):
#   t2-screen-wave1   Run T2 C1 screening for pass-ready candidates
#   t3-screen-wave1   Run T3 C2 screening for Stage 2-INCLUDE candidates
#   ingest-stage2     Ingest T2 screening results into the candidate tracker
#   ingest-stage3     Ingest T3 screening results into the candidate tracker
#   summarize         Show full tracker summary (includes workflow readiness)
#   init              Create or normalize the candidate tracker
#
# Environment variables:
#   SCREEN_MODEL      Model to use for screening (default: gpt-5.4)
#   FUNC_IDS          Space-separated list of func_ids (overrides auto-detect)
#   T2_RUN_ID         Run ID for T2 screen (default: t2_screen_wave1)
#   T3_RUN_ID         Run ID for T3 screen (default: t3_screen_wave1)
#
# Examples:
#   ./scripts/screen.sh list --state pending
#   ./scripts/screen.sh add --id my_func --source "authored" --lines 14 --complexity medium
#   ./scripts/screen.sh update-stage1 my_func --result PASS
#   ./scripts/screen.sh update-stage1 bad_func --result EXCLUDE --reason "Too trivial"
#   ./scripts/screen.sh summarize
#   ./scripts/screen.sh t2-screen-wave1
#   FUNC_IDS="my_func another" ./scripts/screen.sh t2-screen-wave1
#   ./scripts/screen.sh ingest-stage2
#   SCREEN_MODEL=claude-opus-4-6 ./scripts/screen.sh t2-screen-wave1

set -euo pipefail

# Always run from the repo root
cd "$(dirname "$0")/.."

# Source .env if present (provides ANTHROPIC_API_KEY, OPENAI_API_KEY)
if [ -f .env ]; then
    set -a
    # shellcheck source=/dev/null
    source .env
    set +a
else
    echo "WARNING: .env file not found. API calls may fail." >&2
fi

COMMAND="${1:-help}"
SCREEN_MODEL="${SCREEN_MODEL:-gpt-5.4}"
FUNC_IDS="${FUNC_IDS:-}"
T2_RUN_ID="${T2_RUN_ID:-t2_screen_wave1}"
T3_RUN_ID="${T3_RUN_ID:-t3_screen_wave1}"

# ---------------------------------------------------------------------------
_get_stage2_eligible() {
    PYTHONPATH=src python -m experiment.summarize_candidates --list stage2-eligible 2>/dev/null || true
}

_get_stage3_eligible() {
    PYTHONPATH=src python -m experiment.summarize_candidates --list stage3-eligible 2>/dev/null || true
}
# ---------------------------------------------------------------------------

case "$COMMAND" in

    t2-screen-wave1)
        if [ -z "$FUNC_IDS" ]; then
            FUNC_IDS=$(_get_stage2_eligible)
        fi
        if [ -z "$FUNC_IDS" ]; then
            echo "ERROR: No Stage 2-eligible candidates found." >&2
            echo "  Add candidates (stage1_result=PASS) to data/dataset/candidates.json first." >&2
            exit 1
        fi
        echo "Running T2 C1 screen (model=${SCREEN_MODEL}, run_id=${T2_RUN_ID})"
        echo "  Candidates: ${FUNC_IDS}"
        # shellcheck disable=SC2086
        PYTHONPATH=src python -m experiment.run_pilot \
            --run-mode full \
            --tasks T2 \
            --conditions C1 \
            --models "${SCREEN_MODEL}" \
            --run-id "${T2_RUN_ID}" \
            --func-ids $FUNC_IDS
        ;;

    t3-screen-wave1)
        if [ -z "$FUNC_IDS" ]; then
            FUNC_IDS=$(_get_stage3_eligible)
        fi
        if [ -z "$FUNC_IDS" ]; then
            echo "ERROR: No Stage 3-eligible candidates found." >&2
            echo "  Run Stage 2 screening and ingest results first." >&2
            exit 1
        fi
        echo "Running T3 C2 screen (model=${SCREEN_MODEL}, run_id=${T3_RUN_ID})"
        echo "  Candidates: ${FUNC_IDS}"
        # shellcheck disable=SC2086
        PYTHONPATH=src python -m experiment.run_pilot \
            --run-mode full \
            --tasks T3 \
            --conditions C2 \
            --models "${SCREEN_MODEL}" \
            --run-id "${T3_RUN_ID}" \
            --func-ids $FUNC_IDS
        ;;

    ingest-stage2)
        echo "Ingesting Stage 2 results from run '${T2_RUN_ID}' (model=${SCREEN_MODEL})"
        PYTHONPATH=src python -m experiment.update_candidates_from_run \
            --run-id "${T2_RUN_ID}" \
            --stage 2 \
            --model "${SCREEN_MODEL}"
        ;;

    ingest-stage3)
        echo "Ingesting Stage 3 results from run '${T3_RUN_ID}' (model=${SCREEN_MODEL})"
        PYTHONPATH=src python -m experiment.update_candidates_from_run \
            --run-id "${T3_RUN_ID}" \
            --stage 3 \
            --model "${SCREEN_MODEL}"
        ;;

    summarize)
        PYTHONPATH=src python -m experiment.summarize_candidates
        ;;

    init)
        PYTHONPATH=src python -m experiment.init_candidates --seed-anchors
        ;;

    # --- candidate management (manual intake / Stage 1) -------------------

    list)
        # Usage: ./scripts/screen.sh list [--state STATE]
        PYTHONPATH=src python -m experiment.manage_candidates list "${@:2}"
        ;;

    add)
        # Usage: ./scripts/screen.sh add --id my_func --source "authored" [...]
        PYTHONPATH=src python -m experiment.manage_candidates add "${@:2}"
        ;;

    update-stage1)
        # Usage: ./scripts/screen.sh update-stage1 my_func --result PASS
        #        ./scripts/screen.sh update-stage1 my_func --result EXCLUDE --reason "..."
        PYTHONPATH=src python -m experiment.manage_candidates update-stage1 "${@:2}"
        ;;

    show)
        # Usage: ./scripts/screen.sh show my_func
        PYTHONPATH=src python -m experiment.manage_candidates show "${@:2}"
        ;;

    validate-candidates)
        PYTHONPATH=src python -m experiment.manage_candidates validate
        ;;

    help|--help|-h)
        sed -n '2,30p' "$0"
        exit 0
        ;;

    *)
        echo "ERROR: Unknown command '${COMMAND}'" >&2
        echo "Run './scripts/screen.sh help' for usage." >&2
        exit 1
        ;;
esac
