#!/usr/bin/env python3
"""Generate F1 and F2 forest plots from frozen exploratory_results.json.

F1: H1/T2 per-model rank-biserial across both pairs (4 rows).
F2: H3/T2 per-model rank-biserial across both pairs (4 rows).

Reads:
    results/analysis/exploratory/full_t2_confirmatory_v2/exploratory_results.json
    results/analysis/exploratory/t2_frontier_successor_replication/exploratory_results.json

Writes:
    paper/figures/F1.pdf
    paper/figures/F2.pdf

No statistics are recomputed. r_rb and 95% bootstrap CI are read verbatim
from the analysis artifact and plotted as-is.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[3]
CONF_JSON = REPO / "results/analysis/exploratory/full_t2_confirmatory_v2/exploratory_results.json"
SUCC_JSON = REPO / "results/analysis/exploratory/t2_frontier_successor_replication/exploratory_results.json"
OUT_DIR = REPO / "paper/figures"

# Expected values (from paper Tables 4-6) for assertion. Rank-biserial values
# in the JSON carry full bootstrap precision; we tolerate small rounding.
EXPECTED = {
    "F1": [
        ("claude-opus-4-6", "confirmatory", 30, +0.750, (+0.142, +1.000)),
        ("gpt-5.4",         "confirmatory", 30, +0.394, (-0.250, +0.864)),
        ("claude-opus-4-7", "successor",    30, +0.509, (-0.143, +1.000)),
        ("gpt-5.5",         "successor",    26, +0.600, (-0.333, +1.000)),
    ],
    "F2": [
        ("claude-opus-4-6", "confirmatory", 30, -0.333, (-1.000, +0.333)),
        ("gpt-5.4",         "confirmatory", 30, -0.400, (-1.000, +0.333)),
        ("claude-opus-4-7", "successor",    30, -1.000, (-1.000, -1.000)),
        ("gpt-5.5",         "successor",    28, -0.500, (-1.000, +1.000)),
    ],
}


def load_per_model(json_path: Path, hypothesis: str) -> dict:
    """Return {model_id: (n_pairs, r_rb, ci_low, ci_high)} for the given H."""
    d = json.loads(json_path.read_text())
    out = {}
    for e in d["analyses"]["per_model_split_h1_h2_h3"]:
        if e["hypothesis"] != hypothesis or e["task"] != "T2":
            continue
        out[e["model"]] = (e["n_pairs"], e["r_rb"], e["ci_low"], e["ci_high"])
    return out


def build_rows(hypothesis: str) -> list[tuple]:
    """Return list of (label, pair, n, r, lo, hi) in paper-table order."""
    conf = load_per_model(CONF_JSON, hypothesis)
    succ = load_per_model(SUCC_JSON, hypothesis)
    order = [
        ("claude-opus-4-6", "confirmatory", conf),
        ("gpt-5.4",         "confirmatory", conf),
        ("claude-opus-4-7", "successor",    succ),
        ("gpt-5.5",         "successor",    succ),
    ]
    rows = []
    for model, pair, src in order:
        if model not in src:
            raise KeyError(f"missing per-model entry for {model} in {pair} JSON")
        n, r, lo, hi = src[model]
        rows.append((model, pair, n, r, lo, hi))
    return rows


def assert_match(figname: str, rows: list[tuple]) -> None:
    """Assert observed rows match the values cited in the paper tables."""
    for obs, exp in zip(rows, EXPECTED[figname]):
        model_o, pair_o, n_o, r_o, lo_o, hi_o = obs
        model_e, pair_e, n_e, r_e, (lo_e, hi_e) = exp
        if model_o != model_e or pair_o != pair_e:
            raise AssertionError(f"{figname}: row order mismatch: {obs} vs {exp}")
        if n_o != n_e:
            raise AssertionError(f"{figname}: {model_o} n mismatch: {n_o} vs {n_e}")
        for label, o, e in [("r", r_o, r_e), ("ci_low", lo_o, lo_e), ("ci_high", hi_o, hi_e)]:
            if abs(o - e) > 5e-3:
                raise AssertionError(
                    f"{figname}: {model_o} {label} mismatch: observed {o:.6f}, expected {e:.3f}"
                )


def forest_plot(rows: list[tuple], title_hint: str, out_pdf: Path) -> None:
    """Draw a 4-row forest plot of (r, CI) with a zero line.

    Confirmatory-pair rows on top, successor-pair rows on bottom; rows ordered
    top-to-bottom in paper-table order, so we plot in reversed Y for that.
    """
    fig, ax = plt.subplots(figsize=(5.2, 2.9))

    # y-positions: top of plot is row 0
    y_positions = list(range(len(rows)))[::-1]  # so row 0 is at the top
    labels = []
    for (model, pair, n, r, lo, hi), y in zip(rows, y_positions):
        lo_err = r - lo
        hi_err = hi - r
        ax.errorbar(
            [r], [y],
            xerr=[[lo_err], [hi_err]],
            fmt="o",
            color="black",
            ecolor="black",
            elinewidth=1.0,
            capsize=3,
            markersize=5,
        )
        labels.append((y, f"{model}  (n={n})"))

    ax.axvline(0.0, color="0.4", linestyle="--", linewidth=0.8)

    # group separator between confirmatory (top two rows) and successor (bottom two)
    sep_y = (y_positions[1] + y_positions[2]) / 2
    ax.axhline(sep_y, color="0.85", linestyle="-", linewidth=0.6)

    # group annotations on the right margin
    ax.text(1.04, (y_positions[0] + y_positions[1]) / 2, "confirmatory",
            transform=ax.get_yaxis_transform(), ha="left", va="center",
            fontsize=8, color="0.35")
    ax.text(1.04, (y_positions[2] + y_positions[3]) / 2, "successor",
            transform=ax.get_yaxis_transform(), ha="left", va="center",
            fontsize=8, color="0.35")

    labels.sort()  # ascending y, then label
    ax.set_yticks([y for y, _ in labels])
    ax.set_yticklabels([s for _, s in labels])
    ax.set_xlim(-1.08, 1.08)
    ax.set_xlabel(r"rank-biserial $r_{\mathrm{rb}}$ (95% bootstrap CI)")
    ax.set_ylim(-0.6, len(rows) - 0.4)

    # cosmetic: thin spines
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="both", labelsize=9)

    fig.tight_layout()
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows_h1 = build_rows("H1")
    assert_match("F1", rows_h1)
    forest_plot(rows_h1, "H1/T2", OUT_DIR / "F1.pdf")
    print(f"wrote {OUT_DIR / 'F1.pdf'}")

    rows_h3 = build_rows("H3")
    assert_match("F2", rows_h3)
    forest_plot(rows_h3, "H3/T2", OUT_DIR / "F2.pdf")
    print(f"wrote {OUT_DIR / 'F2.pdf'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
