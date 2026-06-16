"""Pre-collection power analysis for the R5 confirmatory studies (T1 and T3).

Constitution v0.3 decision 5 requires, before any R5 collection: the assumed
effect size, the target power, and the resulting minimum n (functions), with a
justification of the chosen dataset size (n = 30).

Design: one-sided Wilcoxon signed-rank on per-function paired differences
(C4 - C1+ for the primary H1), aggregated per function across the two frozen
models, in a 9-test Holm-Bonferroni family (constitution / governance).

Two thresholds are reported:
  * nominal      alpha = 0.05            (optimistic: H1 enters Holm at the
                                           least-stringent step)
  * Bonferroni   alpha' = 0.05 / 9       (conservative: worst-case Holm step
                            = 0.005556     for the primary test)

Method:
  1. Closed form: paired one-sided z-test n, inflated by the Wilcoxon
     asymptotic relative efficiency (ARE = 3/pi ~= 0.9549 under normal shift),
     parameterized by Cohen's dz = mean(D)/sd(D).
  2. Simulation cross-check: draw paired differences and run scipy's exact
     one-sided Wilcoxon, estimating power at each n.

Reference effect: the frozen T2/H1 confirmatory result is rank-biserial
r_rb = 0.581 (large). Probability-of-superiority p+ = (r_rb + 1) / 2 ~= 0.79.

Run: python3 scripts/r5_power_analysis.py
"""

from __future__ import annotations

import math

from scipy.stats import norm, wilcoxon
import numpy as np

ARE = 3.0 / math.pi  # Wilcoxon-vs-t asymptotic relative efficiency, normal shift
ALPHAS = {"nominal_0.05": 0.05, "bonferroni_0.05/9": 0.05 / 9.0}
POWERS = (0.80, 0.90)
DZ_GRID = (0.3, 0.4, 0.5, 0.6, 0.8, 1.0)


def closed_form_n(dz: float, alpha: float, power: float) -> int:
    """Min n for a one-sided paired test at (alpha, power), Wilcoxon-adjusted."""
    z_a = norm.ppf(1.0 - alpha)
    z_b = norm.ppf(power)
    n_t = ((z_a + z_b) / dz) ** 2          # paired one-sided z/t-test
    n_w = n_t / ARE                         # Wilcoxon inflation
    return math.ceil(n_w)


def detectable_dz(n: int, alpha: float, power: float) -> float:
    """Smallest dz a Wilcoxon test on n pairs can detect at (alpha, power)."""
    z_a = norm.ppf(1.0 - alpha)
    z_b = norm.ppf(power)
    return (z_a + z_b) / math.sqrt(n * ARE)


def simulate_power(n: int, dz: float, alpha: float, n_sims: int = 4000,
                   seed: int = 20260616) -> float:
    """Estimate one-sided Wilcoxon power for normal-shift paired diffs ~ N(dz, 1)."""
    rng = np.random.default_rng(seed)
    rejects = 0
    for _ in range(n_sims):
        d = rng.normal(loc=dz, scale=1.0, size=n)
        nz = d[d != 0.0]
        if len(nz) < 2:
            continue
        p = wilcoxon(nz, alternative="greater", zero_method="wilcox").pvalue
        if p < alpha:
            rejects += 1
    return rejects / n_sims


def main() -> None:
    print("=" * 72)
    print("R5 PRE-COLLECTION POWER ANALYSIS")
    print(f"Wilcoxon ARE (normal shift) = {ARE:.4f}")
    print("=" * 72)

    print("\n[1] Minimum n (functions) by Cohen's dz, closed-form (Wilcoxon-adjusted)\n")
    header = "  dz   | " + " | ".join(
        f"{name} p={p:.2f}" for name in ALPHAS for p in POWERS
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    for dz in DZ_GRID:
        cells = []
        for name, a in ALPHAS.items():
            for p in POWERS:
                cells.append(f"{closed_form_n(dz, a, p):>{len(name)+5}d}")
        print(f"  {dz:>4.1f} | " + " | ".join(cells))

    print("\n[2] Smallest detectable dz at the frozen n = 30\n")
    for name, a in ALPHAS.items():
        for p in POWERS:
            dz = detectable_dz(30, a, p)
            print(f"  alpha={name:18s} power={p:.2f}  ->  detectable dz = {dz:.3f}")

    print("\n[3] Simulation cross-check (normal-shift paired diffs), n = 30\n")
    for dz in (0.5, 0.6, 0.8):
        for name, a in ALPHAS.items():
            pw = simulate_power(30, dz, a)
            print(f"  n=30 dz={dz:.1f} alpha={name:18s} -> simulated power = {pw:.3f}")

    print("\n[4] Reference: frozen T2/H1 confirmatory effect")
    r_rb = 0.581
    p_sup = (r_rb + 1) / 2
    # dz implied by a probability-of-superiority p_sup under a normal-shift model:
    # p_sup = Phi(dz / sqrt(2))  ->  dz = sqrt(2) * Phi^{-1}(p_sup)
    dz_implied = math.sqrt(2) * norm.ppf(p_sup)
    print(f"  r_rb(T2/H1) = {r_rb}  ->  p_superiority ~= {p_sup:.3f}"
          f"  ->  implied dz ~= {dz_implied:.2f} (large)")
    print(f"  n=30 simulated power at dz={dz_implied:.2f}:")
    for name, a in ALPHAS.items():
        print(f"    alpha={name:18s} -> {simulate_power(30, dz_implied, a):.3f}")


if __name__ == "__main__":
    main()
