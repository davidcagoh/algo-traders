#!/usr/bin/env python3
"""
Generate wiki/assets/leaderboard.png from wiki/_index.md and backtest result ZIPs.

Usage:
    ./freqtrade/.venv/bin/python scripts/generate_leaderboard_chart.py
"""
import glob
import io
import json
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
WIKI_INDEX = REPO_ROOT / "wiki" / "_index.md"
ZIP_DIR = REPO_ROOT / "user_data" / "backtest_results"
OUT_PATH = REPO_ROOT / "wiki" / "assets" / "leaderboard.png"

# Short display names for chart x-axis labels
SHORT_NAMES = {
    "SmaRegime720": "SMA720",
    "SmaRegime180": "SMA180",
    "LongOnlyStrategy": "LongOnly",
    "TrendFilter200": "TrendF200",
    "HmmRegime4": "HMM4",
}

EQUITY_COLORS = ["#2ecc71", "#3498db", "#e74c3c", "#f39c12", "#9b59b6"]


def _clean(s):
    """Strip markdown bold/italic markers and Unicode footnote superscripts."""
    s = re.sub(r"\*{1,2}", "", s)
    s = re.sub(r"[²³⁴⁵¹]", "", s)
    return s.strip()


def parse_leaderboard(content):
    """Return list of strategy dicts from the wiki/_index.md leaderboard table."""
    m = re.search(r"\| Strategy \| Calmar", content)
    if not m:
        raise ValueError("Leaderboard table not found in wiki/_index.md")

    strategies = []
    for line in content[m.start():].split("\n")[2:]:  # skip header + separator
        if not line.startswith("|"):
            break
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) < 8:
            continue

        name_m = re.search(r"`([^`]+)`", cols[0])
        if not name_m:
            continue
        name = name_m.group(1)

        calmar_raw = _clean(cols[1])
        if "pending" in calmar_raw or calmar_raw in ("—", "-"):
            continue

        try:
            calmar = float(calmar_raw)
            sharpe = float(_clean(cols[4]).replace("+", ""))
            mdd = float(_clean(cols[6]).replace("%", "")) / 100.0
            cagr = float(_clean(cols[5]).replace("%", "").replace("+", "")) / 100.0
            trades = int(_clean(cols[7]).replace(",", ""))
        except ValueError:
            continue

        strategies.append({
            "name": name,
            "calmar": calmar,
            "sharpe": sharpe,
            "mdd": mdd,
            "cagr": cagr,
            "trades": trades,
            "winrate": None,
            "post_cost_calmar": None,
            "wallet_df": None,
            "market_df": None,
        })

    # Parse post-cost Calmar from footnote body
    pc_m = re.search(r"est\.\s*Calmar\s*[~≈]\s*(\d+(?:\.\d+)?)", content)
    if pc_m:
        pc_val = float(pc_m.group(1))
        # Attribute to the strategy whose raw Calmar matches the ³-footnoted value (SmaRegime180)
        for s in strategies:
            if s["name"] == "SmaRegime180":
                s["post_cost_calmar"] = pc_val
                break

    return strategies


def find_latest_zip(strategy_name):
    """Return path to the newest ZIP containing data for strategy_name, or None."""
    zips = sorted(glob.glob(str(ZIP_DIR / "*.zip")))
    for z in reversed(zips):
        try:
            with zipfile.ZipFile(z) as zf:
                if any(f"{strategy_name}_wallet" in n for n in zf.namelist()):
                    return z
        except zipfile.BadZipFile:
            continue
    return None


def load_zip_data(strategy_name, zip_path):
    """Return (winrate, wallet_df, market_df) from a backtest result ZIP."""
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()

        json_name = next(
            n for n in names if n.endswith(".json") and "_config" not in n
        )
        strat_data = json.loads(zf.read(json_name))["strategy"][strategy_name]
        winrate = strat_data.get("winrate")

        wallet_name = next(n for n in names if f"{strategy_name}_wallet" in n)
        wdf = pd.read_feather(io.BytesIO(zf.read(wallet_name)))[["date", "balance"]].copy()
        wdf["return_pct"] = (wdf["balance"] / wdf["balance"].iloc[0] - 1.0) * 100.0
        wdf["days"] = (wdf["date"] - wdf["date"].iloc[0]).dt.total_seconds() / 86400.0

        market_name = next(n for n in names if "market_change" in n)
        mdf = pd.read_feather(io.BytesIO(zf.read(market_name)))[["date", "rel_mean"]].copy()
        mdf["return_pct"] = mdf["rel_mean"] * 100.0
        mdf["days"] = (mdf["date"] - mdf["date"].iloc[0]).dt.total_seconds() / 86400.0

    return winrate, wdf, mdf


def _bar_label(ax, bar, value, fmt, offset, va):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        value + offset,
        fmt.format(value),
        ha="center", va=va, fontsize=7.5, fontweight="bold",
    )


def generate_chart(strategies):
    short = [SHORT_NAMES.get(s["name"], s["name"][:9]) for s in strategies]
    n = len(strategies)
    xs = list(range(n))

    fig = plt.figure(figsize=(14, 10), facecolor="white")
    gs = gridspec.GridSpec(
        2, 4, figure=fig, height_ratios=[1, 1.2], hspace=0.55, wspace=0.42
    )
    ax_c = fig.add_subplot(gs[0, 0])   # Calmar
    ax_s = fig.add_subplot(gs[0, 1])   # Sharpe
    ax_w = fig.add_subplot(gs[0, 2])   # Win Rate
    ax_m = fig.add_subplot(gs[0, 3])   # Max Drawdown
    ax_e = fig.add_subplot(gs[1, :])   # Equity curves

    BW = 0.55

    # ── Calmar ──────────────────────────────────────────────────────────────
    for i, s in enumerate(strategies):
        v = s["calmar"]
        color = "#2ecc71" if v > 0 else "#e74c3c"
        bar = ax_c.bar(i, v, width=BW, color=color, zorder=2)[0]
        offset = 0.4 if v >= 0 else -0.4
        va = "bottom" if v >= 0 else "top"
        _bar_label(ax_c, bar, v, "{:.1f}", offset, va)

        # Post-cost annotation inside the bar (SmaRegime180 only)
        if s.get("post_cost_calmar") is not None:
            ax_c.text(
                i, v * 0.45,
                f"~{s['post_cost_calmar']:.1f}\npost-cost",
                ha="center", va="center", fontsize=6, color="white",
                fontweight="bold", alpha=0.92,
            )

    ax_c.axhline(0, color="#444", linewidth=0.8)
    ax_c.set_title("Calmar", fontsize=10, fontweight="bold")
    ax_c.set_xticks(xs)
    ax_c.set_xticklabels(short, fontsize=7.5, rotation=15, ha="right")
    ax_c.grid(axis="y", alpha=0.3, zorder=1)
    ax_c.set_ylabel("Calmar (CAGR / MDD)", fontsize=7.5)

    # ── Sharpe ──────────────────────────────────────────────────────────────
    for i, s in enumerate(strategies):
        v = s["sharpe"]
        color = "#2ecc71" if v > 0 else "#e74c3c"
        bar = ax_s.bar(i, v, width=BW, color=color, zorder=2)[0]
        offset = 0.02 if v >= 0 else -0.02
        va = "bottom" if v >= 0 else "top"
        _bar_label(ax_s, bar, v, "{:.2f}", offset, va)

    ax_s.axhline(0, color="#444", linewidth=0.8)
    ax_s.set_title("Sharpe", fontsize=10, fontweight="bold")
    ax_s.set_xticks(xs)
    ax_s.set_xticklabels(short, fontsize=7.5, rotation=15, ha="right")
    ax_s.grid(axis="y", alpha=0.3, zorder=1)

    # ── Win Rate ─────────────────────────────────────────────────────────────
    for i, s in enumerate(strategies):
        v = (s["winrate"] or 0) * 100
        bar = ax_w.bar(i, v, width=BW, color="#3498db", zorder=2)[0]
        _bar_label(ax_w, bar, v, "{:.1f}%", 0.8, "bottom")

    ax_w.axhline(50, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
    ax_w.set_title("Win Rate", fontsize=10, fontweight="bold")
    ax_w.set_xticks(xs)
    ax_w.set_xticklabels(short, fontsize=7.5, rotation=15, ha="right")
    ax_w.set_ylim(0, 65)
    ax_w.set_ylabel("%", fontsize=8)
    ax_w.grid(axis="y", alpha=0.3, zorder=1)

    # ── Max Drawdown ─────────────────────────────────────────────────────────
    for i, s in enumerate(strategies):
        v = s["mdd"] * 100
        bar = ax_m.bar(i, v, width=BW, color="#e74c3c", zorder=2)[0]
        _bar_label(ax_m, bar, v, "{:.1f}%", 0.05, "bottom")

    ax_m.set_title("Max Drawdown", fontsize=10, fontweight="bold")
    ax_m.set_xticks(xs)
    ax_m.set_xticklabels(short, fontsize=7.5, rotation=15, ha="right")
    ax_m.set_ylabel("%", fontsize=8)
    ax_m.grid(axis="y", alpha=0.3, zorder=1)

    # ── Equity Curves ────────────────────────────────────────────────────────
    for i, s in enumerate(strategies):
        if s["wallet_df"] is None:
            continue
        c = EQUITY_COLORS[i % len(EQUITY_COLORS)]
        label = short[i]
        wdf = s["wallet_df"]
        mdf = s["market_df"]
        ax_e.plot(wdf["days"], wdf["return_pct"], color=c, linewidth=1.8,
                  label=label, zorder=3)
        ax_e.plot(mdf["days"], mdf["return_pct"], color=c, linewidth=0.9,
                  linestyle="--", alpha=0.45, label=f"{label} (market)", zorder=2)

    ax_e.axhline(0, color="#444", linewidth=0.8)
    ax_e.set_xlabel("Days from backtest start", fontsize=9)
    ax_e.set_ylabel("Return (%)", fontsize=9)
    ax_e.set_title("Equity Curves — normalized to 0%  (dashed = market benchmark)",
                   fontsize=10, fontweight="bold")
    ax_e.legend(fontsize=7.5, ncol=min(n * 2, 6), loc="upper left",
                framealpha=0.8)
    ax_e.grid(alpha=0.25, zorder=1)

    today = datetime.now().strftime("%Y-%m-%d")
    fig.suptitle(f"Strategy Leaderboard — {today}", fontsize=13,
                 fontweight="bold", y=1.01)

    return fig


def main():
    content = WIKI_INDEX.read_text()
    strategies = parse_leaderboard(content)

    print(f"{'Strategy':<20} {'Calmar':>8} {'Sharpe':>8} {'WinRate':>9} "
          f"{'MDD':>7} {'Trades':>7}")
    print("-" * 65)

    for s in strategies:
        zip_path = find_latest_zip(s["name"])
        if zip_path:
            try:
                winrate, wdf, mdf = load_zip_data(s["name"], zip_path)
                s["winrate"] = winrate
                s["wallet_df"] = wdf
                s["market_df"] = mdf
            except Exception as exc:
                print(f"  Warning: could not load {s['name']} from ZIP: {exc}")
        else:
            print(f"  Warning: no ZIP found for {s['name']}")

        wr = f"{s['winrate'] * 100:.1f}%" if s["winrate"] is not None else "n/a"
        print(f"{s['name']:<20} {s['calmar']:>8.2f} {s['sharpe']:>8.2f} "
              f"{wr:>9} {s['mdd'] * 100:>6.2f}% {s['trades']:>7}")

    print()
    fig = generate_chart(strategies)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
