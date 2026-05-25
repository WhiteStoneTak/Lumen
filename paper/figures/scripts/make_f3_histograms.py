#!/usr/bin/env python3
"""Generate F3: T2 score distribution histograms.

Two panels (descriptive count over the frozen confirmatory run; no statistics):
  Left:  per-model raw composite over {0, 1, 2, 3} from the 300 scorer-result
         records in results/runs/full_t2_confirmatory_v2/scores/*.json.
  Right: per-(func, condition) 2-model averaged composite over the 0.5-step
         support {0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0}, computed per (func, cond)
         cell across 30 functions x 5 conditions = 150 cells.

Reads:
    results/runs/full_t2_confirmatory_v2/scores/*.json

Writes:
    paper/figures/F3.pdf

Asserts that left-panel distribution matches paper section 3.7
({0:19, 1:89, 2:192, 3:0}; total 300) and that right-panel supports
2.5 and 3.0 are empty.
"""
from __future__ import annotations

import collections
import glob
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[3]
SCORES_GLOB = str(REPO / "results/runs/full_t2_confirmatory_v2/scores/*.json")
OUT_PDF = REPO / "paper/figures/F3.pdf"

EXPECTED_RAW = {0: 19, 1: 89, 2: 192, 3: 0}


def load_scores() -> tuple[collections.Counter, dict]:
    """Return (raw_per_model_counter, by_func_cond_dict).

    raw_per_model_counter: composite (int) -> count, over all 300 records.
    by_func_cond_dict: (func_id, condition) -> {model_id: score(float)}.
    """
    raw = collections.Counter()
    by_fc: dict[tuple[str, str], dict[str, float]] = collections.defaultdict(dict)
    files = sorted(glob.glob(SCORES_GLOB))
    if len(files) != 300:
        raise AssertionError(f"expected 300 score files, found {len(files)}")
    for fp in files:
        d = json.loads(Path(fp).read_text())
        if d.get("lumen_schema") != "scorer-result-v1":
            continue
        score = int(d["score"])
        raw[score] += 1
        by_fc[(d["func_id"], d["condition"])][d["model_id"]] = float(d["score"])
    return raw, by_fc


def averaged_distribution(by_fc: dict) -> collections.Counter:
    """Compute per-(func, cond) 2-model averaged composite counts.

    Each cell has exactly 2 model scores in the frozen confirmatory run;
    averaged value lies in {0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0}.
    """
    avg = collections.Counter()
    for (_, _), ms in by_fc.items():
        if len(ms) != 2:
            raise AssertionError(f"expected 2 model scores per cell; got {len(ms)}")
        avg[sum(ms.values()) / 2.0] += 1
    return avg


def assert_consistency(raw: collections.Counter, avg: collections.Counter) -> None:
    """Verify against paper section 3.7."""
    for k, expected_count in EXPECTED_RAW.items():
        if raw.get(k, 0) != expected_count:
            raise AssertionError(
                f"raw composite {k}: observed {raw.get(k, 0)}, expected {expected_count}"
            )
    total = sum(raw.values())
    if total != 300:
        raise AssertionError(f"raw composite total: {total}, expected 300")
    if avg.get(2.5, 0) != 0:
        raise AssertionError(f"averaged 2.5 should be empty; observed {avg.get(2.5, 0)}")
    if avg.get(3.0, 0) != 0:
        raise AssertionError(f"averaged 3.0 should be empty; observed {avg.get(3.0, 0)}")
    total_cells = sum(avg.values())
    if total_cells != 150:
        raise AssertionError(f"averaged total cells: {total_cells}, expected 150")


def plot(raw: collections.Counter, avg: collections.Counter, out: Path) -> None:
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(7.5, 3.0))

    # Left: raw composite over {0,1,2,3} (force zero-height bar at 3)
    raw_x = [0, 1, 2, 3]
    raw_y = [raw.get(k, 0) for k in raw_x]
    axL.bar(raw_x, raw_y, color="0.35", edgecolor="black", linewidth=0.5, width=0.7)
    axL.set_xticks(raw_x)
    axL.set_xlabel("per-model raw composite score")
    axL.set_ylabel("count")
    for x, y in zip(raw_x, raw_y):
        if y > 0:
            axL.text(x, y + 4, str(y), ha="center", va="bottom", fontsize=8)
        else:
            axL.text(x, 4, "0", ha="center", va="bottom", fontsize=8, color="0.4")
    axL.set_ylim(0, max(raw_y) * 1.18)
    for s in ["top", "right"]:
        axL.spines[s].set_visible(False)

    # Right: averaged composite over {0.0, 0.5, ..., 3.0}
    avg_x = [i * 0.5 for i in range(7)]
    avg_y = [avg.get(x, 0) for x in avg_x]
    axR.bar(avg_x, avg_y, color="0.35", edgecolor="black", linewidth=0.5, width=0.35)
    axR.set_xticks(avg_x)
    axR.set_xlabel("per-(function, condition) 2-model averaged composite")
    axR.set_ylabel("count")
    for x, y in zip(avg_x, avg_y):
        if y > 0:
            axR.text(x, y + 1.5, str(y), ha="center", va="bottom", fontsize=8)
        else:
            axR.text(x, 1.5, "0", ha="center", va="bottom", fontsize=8, color="0.4")
    axR.set_ylim(0, max(avg_y) * 1.20)
    for s in ["top", "right"]:
        axR.spines[s].set_visible(False)

    for ax in (axL, axR):
        ax.tick_params(axis="both", labelsize=9)

    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    raw, by_fc = load_scores()
    avg = averaged_distribution(by_fc)
    assert_consistency(raw, avg)
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    plot(raw, avg, OUT_PDF)
    print(f"wrote {OUT_PDF}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
