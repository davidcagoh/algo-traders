#!/usr/bin/env python3
"""
Generate wiki/assets/pareto.png — three-panel Pareto-frontier publication chart.

Panel 1 (left):   Calmar (y) vs MDD% (x). Upper-left = best risk-adjusted.
Panel 2 (middle): Martin ratio (y) vs Ulcer Index (x). Upper-left = best path-quality.
Panel 3 (right): MDB-rp (y) vs corr_to_T3 (x). Upper-left = best portfolio-additive.

Markers:
  ★ filled diamond — paper-trade candidate (in current book or graduating)
  ▲ filled triangle — research frontier (non-dominated geometrically AND DSR/MDB-positive)
  ~ hollow circle — upper-bound only (look-ahead / not tradeable)
  ✗ red X — killed (K1 breached without portfolio justification, or MDB-negative robust)
  · grey dot — baseline / placeholder

Family color: T (trend) = blue, R (regime) = green, C (carry) = orange, R∧T = purple, R∧C = pink.

Data is sourced from A1.5 common-window backtests (`scripts/run_correlation_mdb.py` JSON
and ZIP metadata). Edit STRATEGIES below when adding a new datapoint.

Usage:
    ./freqtrade/.venv/bin/python scripts/generate_pareto_chart.py
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "wiki" / "assets" / "pareto.png"


FAMILY_COLOR = {
    "T":   "#1f77b4",   # blue (trend)
    "R":   "#2ca02c",   # green (regime)
    "C":   "#ff7f0e",   # orange (carry)
    "R∧T": "#9467bd",   # purple (regime × trend)
    "R∧C": "#e377c2",   # pink (regime × carry)
    "X":   "#8c564b",   # brown (cross-sectional / pairs)
    "F":   "#17becf",   # cyan (funding MR)
}

# Marker spec by status tag.
STATUS_MARKER = {
    "★": dict(marker="D", facecolor=None, edgecolor="black", size=180, alpha=1.0),
    "▲": dict(marker="^", facecolor=None, edgecolor="black", size=140, alpha=0.9),
    "~": dict(marker="o", facecolor="none", edgecolor=None, size=140, alpha=0.7),
    "✗": dict(marker="X", facecolor="#d62728", edgecolor="black", size=120, alpha=0.85),
    "·": dict(marker=".", facecolor="grey", edgecolor=None, size=80, alpha=0.5),
}


@dataclass
class Strategy:
    code: str        # taxonomy code (T3, R∧T2, etc.)
    label: str       # short label for plot
    family: str      # T / R / C / R∧T / R∧C
    status: str      # ★ / ▲ / ~ / ✗ / ·
    calmar: float
    sqn: float
    mdd: float       # %
    ulcer: float
    martin: float
    corr_to_t3: float
    mdb_rp: float


# A1.5 common-window data (Binance 2020-09 → 2026-05, 5-coin or BTC-only).
# All numbers from `_correlation_table.json` + `_index.md` common-window leaderboard.
STRATEGIES = [
    Strategy("T3",   "T3 SmaRegime180",       "T",   "★",
             calmar=8.76,  sqn=1.78, mdd=2.21,  ulcer=1.30,  martin=+2.51,
             corr_to_t3=1.00, mdb_rp=0.0),
    Strategy("R∧T2", "R∧T2 HmmSmaSlopeV2",    "R∧T", "★",
             calmar=30.23, sqn=2.73, mdd=6.05,  ulcer=2.87,  martin=+7.41,
             corr_to_t3=+0.07, mdb_rp=+0.55),
    Strategy("R∧T1", "R∧T1 HmmSmaSlope",      "R∧T", "▲",
             calmar=25.01, sqn=2.97, mdd=8.21,  ulcer=3.82,  martin=+6.00,
             corr_to_t3=+0.07, mdb_rp=+0.57),
    Strategy("R∧T3", "R∧T3 HmmSmaSlopeV3",    "R∧T", "▲",
             calmar=27.28, sqn=2.79, mdd=6.91,  ulcer=3.30,  martin=+6.58,
             corr_to_t3=+0.07, mdb_rp=+0.57),
    Strategy("T2",   "T2 SmaRegime720",       "T",   "▲",
             calmar=5.39,  sqn=1.74, mdd=3.57,  ulcer=1.75,  martin=+1.82,
             corr_to_t3=+0.65, mdb_rp=+0.06),
    Strategy("T1",   "T1 TrendFilter200",     "T",   "▲",
             calmar=1.69,  sqn=1.10, mdd=8.54,  ulcer=3.79,  martin=+0.67,
             corr_to_t3=-0.00, mdb_rp=+0.09),
    Strategy("R1~",  "R1 HmmRegime4 (LA)",    "R",   "~",
             calmar=9.16,  sqn=3.88, mdd=2.94,  ulcer=1.09,  martin=+4.24,
             corr_to_t3=+0.00, mdb_rp=+0.14),
    Strategy("R2",   "R2 HmmRegime4Rolling",  "R",   "✗",
             calmar=0.47,  sqn=0.39, mdd=7.65,  ulcer=4.01,  martin=+0.17,
             corr_to_t3=+0.01, mdb_rp=+0.02),
    Strategy("R2x",  "R2x R2 5-coin",         "R",   "✗",
             calmar=3.79,  sqn=1.66, mdd=21.47, ulcer=10.25, martin=+1.15,
             corr_to_t3=-0.01, mdb_rp=+0.13),
    Strategy("C1",   "C1 FundingCarry",       "C",   "✗",
             calmar=1.37,  sqn=1.28, mdd=8.52,  ulcer=2.80,  martin=+0.76,
             corr_to_t3=-0.09, mdb_rp=-0.28),
    Strategy("R∧C1", "R∧C1 HmmCarry",         "R∧C", "✗",
             calmar=0.08,  sqn=0.14, mdd=35.46, ulcer=9.57,  martin=+0.04,
             corr_to_t3=+0.00, mdb_rp=-0.00),
    Strategy("T0",   "T0 LongOnly",           "T",   "·",
             calmar=-0.37, sqn=-0.58, mdd=10.17, ulcer=6.26, martin=-0.11,
             corr_to_t3=-0.00, mdb_rp=-0.009),
    Strategy("X1",   "X1 PairsZScore",        "X",   "✗",
             calmar=2.08, sqn=0.5, mdd=4.03, ulcer=1.5, martin=+1.5,
             corr_to_t3=+0.00, mdb_rp=-0.898),
    Strategy("X2",   "X2 CrossSectMomentum",  "X",   "▲",
             calmar=2.5, sqn=1.0, mdd=13.04, ulcer=4.0, martin=+1.3,
             corr_to_t3=+0.00, mdb_rp=+0.048),
    Strategy("F1",   "F1 FundingExtremeMR",   "F",   "✗",
             calmar=-0.56, sqn=-1.5, mdd=29.94, ulcer=11.0, martin=-0.4,
             corr_to_t3=-0.01, mdb_rp=-1.845),
]


def _scatter(ax, s: Strategy, x: float, y: float) -> None:
    spec = STATUS_MARKER[s.status]
    fc = spec["facecolor"]
    if fc is None:  # filled with family color
        fc = FAMILY_COLOR[s.family]
    ec = spec["edgecolor"] if spec["edgecolor"] is not None else FAMILY_COLOR[s.family]
    ax.scatter(
        x, y,
        marker=spec["marker"],
        s=spec["size"],
        c=fc,
        edgecolors=ec,
        linewidths=1.5,
        alpha=spec["alpha"],
        zorder=3,
    )


def _annotate(ax, s: Strategy, x: float, y: float, xytext=(7, 5)) -> None:
    ax.annotate(
        s.code,
        (x, y),
        xytext=xytext,
        textcoords="offset points",
        fontsize=8,
        zorder=4,
    )


def _frontier_upper_left(points: list[tuple[float, float, Strategy]]):
    """Return points on the upper-left Pareto frontier (low x, high y)."""
    frontier = []
    for i, (x, y, s) in enumerate(points):
        dominated = False
        for j, (xj, yj, _sj) in enumerate(points):
            if i == j:
                continue
            if xj <= x and yj >= y and (xj < x or yj > y):
                dominated = True
                break
        if not dominated:
            frontier.append((x, y, s))
    return sorted(frontier, key=lambda t: t[0])


def _draw_legend(ax) -> None:
    handles = []
    for code, color in FAMILY_COLOR.items():
        handles.append(Line2D([0], [0], marker="o", color="none", markerfacecolor=color,
                              markeredgecolor=color, markersize=9, label=f"{code} family"))
    handles.append(Line2D([0], [0], marker="D", color="none", markerfacecolor="white",
                          markeredgecolor="black", markersize=10, label="★ paper-trade"))
    handles.append(Line2D([0], [0], marker="^", color="none", markerfacecolor="white",
                          markeredgecolor="black", markersize=10, label="▲ frontier (research)"))
    handles.append(Line2D([0], [0], marker="o", color="none", markerfacecolor="none",
                          markeredgecolor="black", markersize=10, label="~ upper bound (LA)"))
    handles.append(Line2D([0], [0], marker="X", color="none", markerfacecolor="#d62728",
                          markeredgecolor="black", markersize=10, label="✗ killed"))
    ax.legend(handles=handles, loc="upper right", fontsize=7, framealpha=0.85)


def main() -> None:
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))

    # Panel 1 — Calmar vs MDD%. Upper-left is best.
    pts1 = [(s.mdd, s.calmar, s) for s in STATEGIES_excluding_LA()]
    for x, y, s in pts1:
        _scatter(ax1, s, x, y)
        _annotate(ax1, s, x, y)
    fx1 = _frontier_upper_left(pts1)
    if len(fx1) >= 2:
        xs, ys = zip(*[(p[0], p[1]) for p in fx1])
        ax1.plot(xs, ys, ":", color="grey", alpha=0.5, zorder=2)
    ax1.set_xlabel("MDD %  (lower = better)")
    ax1.set_ylabel("Calmar (closed trades)  (higher = better)")
    ax1.set_title("Panel 1 — Risk-adjusted return\n(common window 2020-09 → 2026-05)")
    ax1.axvline(5.5, ls="--", color="red", alpha=0.5, lw=1)
    ax1.text(5.6, ax1.get_ylim()[1] * 0.97, "K1 = 5.5%", color="red", fontsize=7, va="top")
    ax1.grid(True, alpha=0.3)
    _draw_legend(ax1)

    # Panel 2 — Martin vs Ulcer. Upper-left is best.
    pts2 = [(s.ulcer, s.martin, s) for s in STATEGIES_excluding_LA()]
    for x, y, s in pts2:
        _scatter(ax2, s, x, y)
        _annotate(ax2, s, x, y)
    fx2 = _frontier_upper_left(pts2)
    if len(fx2) >= 2:
        xs, ys = zip(*[(p[0], p[1]) for p in fx2])
        ax2.plot(xs, ys, ":", color="grey", alpha=0.5, zorder=2)
    ax2.set_xlabel("Ulcer Index  (lower = better)")
    ax2.set_ylabel("Martin ratio (CAGR / Ulcer)  (higher = better)")
    ax2.set_title("Panel 2 — Tail / Path shape\n(common window 2020-09 → 2026-05)")
    ax2.grid(True, alpha=0.3)

    # Panel 3 — MDB-rp vs corr_to_T3. Lower-left of corr + higher MDB = best portfolio addition.
    pts3 = [(s.corr_to_t3, s.mdb_rp, s) for s in STRATEGIES if s.code != "T3"]
    for x, y, s in pts3:
        _scatter(ax3, s, x, y)
        _annotate(ax3, s, x, y)
    ax3.axhline(0.0, color="black", alpha=0.3, lw=1)
    ax3.axvline(0.5, ls="--", color="grey", alpha=0.3, lw=1)
    # Shade the "portfolio-additive quadrant" (corr < 0.5 AND MDB-rp > 0).
    ax3.axhspan(0, ax3.get_ylim()[1] if ax3.get_ylim()[1] > 0 else 1.0,
                xmin=0, xmax=0.5, alpha=0.06, color="green")
    ax3.set_xlabel("Correlation to T3  (lower = more orthogonal)")
    ax3.set_ylabel("MDB-rp  (Sharpe gain when added to T3 book)")
    ax3.set_title("Panel 3 — Marginal Diversification Benefit\n(book = {T3}, risk-parity weights)")
    ax3.grid(True, alpha=0.3)

    fig.suptitle(
        "Strategy Pareto frontier — A1.5 + A2 (2026-05-16)",
        fontsize=14, y=1.02,
    )
    fig.tight_layout()
    fig.savefig(OUT_PATH, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUT_PATH}")


def STATEGIES_excluding_LA():
    """Helper — Panel 1+2 exclude R1~ (look-ahead) because it's not tradeable.
    Panel 3 keeps R1~ for the corr/MDB curiosity."""
    return [s for s in STRATEGIES if s.status != "~"]


if __name__ == "__main__":
    main()
