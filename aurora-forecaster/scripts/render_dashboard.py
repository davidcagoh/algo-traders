"""
Manual script: computes the current ablation results, records this run into
the leaderboard history, and renders `artifacts/dashboard.html` -- a
horizontal bar chart of current mean loss per config (sorted best-first), a
pairwise Diebold-Mariano significance table (highlighted where p<0.05), and
(once 2+ historical runs exist for a config) a small trend section.

Pure local file I/O -- no network/model needed. Inline SVG/CSS, no plotting
library or Artifact tool -- same reasoning as aurora_forecaster/vision.py's
chart renderer, and per standing decision (2026-08-08) to keep this local
rather than publish it anywhere.

Usage: python scripts/render_dashboard.py
"""

from __future__ import annotations

import html
from datetime import UTC, datetime
from pathlib import Path

from aurora_forecaster.ablation import STANDARD_CONFIGS, compute_ablation_results
from aurora_forecaster.ablation_core import ConfigSummary, PairwiseComparison
from aurora_forecaster.leaderboard import (
    LeaderboardEntry,
    load_leaderboard_history,
    record_leaderboard_entry,
)

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"
DASHBOARD_PATH = ARTIFACTS_DIR / "dashboard.html"


def render_bar_chart(summaries: list[ConfigSummary], width: int = 700) -> str:
    if not summaries:
        return "<p>No scored configs yet.</p>"

    ordered = sorted(summaries, key=lambda s: s.mean_loss)
    row_h = 32
    label_w = 160
    bar_area = width - label_w - 80
    max_loss = max(s.mean_loss for s in ordered) or 1.0
    height = row_h * len(ordered) + 20

    bars = []
    for i, s in enumerate(ordered):
        y = 10 + i * row_h
        bar_w = bar_area * (s.mean_loss / max_loss)
        bars.append(
            f'<text x="{label_w - 10}" y="{y + row_h * 0.65:.0f}" text-anchor="end" '
            f'font-size="13" fill="#0b0b0b">{html.escape(s.config_name)}</text>'
            f'<rect x="{label_w}" y="{y + 4}" width="{bar_w:.1f}" height="{row_h - 12}" '
            f'fill="#2a78d6" rx="2"/>'
            f'<text x="{label_w + bar_w + 6:.1f}" y="{y + row_h * 0.65:.0f}" font-size="12" '
            f'fill="#52514e">{s.mean_loss:.1f} (n={s.n_origins})</text>'
        )
    return f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">{"".join(bars)}</svg>'


def render_comparison_table(comparisons: list[PairwiseComparison]) -> str:
    if not comparisons:
        return "<p>No pairwise comparisons yet (need 2+ scored configs).</p>"

    rows = []
    for c in sorted(comparisons, key=lambda c: c.dm.p_value):
        significant = c.dm.p_value < 0.05
        style = ' style="background:#fde8e8;font-weight:600"' if significant else ""
        rows.append(
            f"<tr{style}><td>{html.escape(c.config_a)}</td><td>{html.escape(c.config_b)}</td>"
            f"<td>{c.dm.statistic:.3f}</td><td>{c.dm.p_value:.3f}</td>"
            f"<td>{c.n_common_origins}</td><td>{c.dm.max_lag}</td></tr>"
        )
    return (
        "<table><thead><tr><th>config_a</th><th>config_b</th><th>statistic</th>"
        "<th>p_value</th><th>n_common</th><th>max_lag</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        "<p><em>Negative statistic + small p-value: config_a significantly better than "
        "config_b. Highlighted rows: p&lt;0.05. No multiple-comparison correction applied "
        "-- with many configs, some highlighted rows are expected by chance alone.</em></p>"
    )


def render_trend_section(history: list[LeaderboardEntry]) -> str:
    by_config: dict[str, list[LeaderboardEntry]] = {}
    for entry in history:
        by_config.setdefault(entry.config_name, []).append(entry)

    trending = {name: entries for name, entries in by_config.items() if len(entries) >= 2}
    if not trending:
        return "<p>Not enough historical runs yet for a trend view (need 2+ runs per config).</p>"

    rows = []
    for name, entries in sorted(trending.items()):
        entries_sorted = sorted(entries, key=lambda e: e.run_at)
        losses = " → ".join(f"{e.mean_loss:.1f}" for e in entries_sorted)
        rows.append(f"<tr><td>{html.escape(name)}</td><td>{losses}</td></tr>")
    return (
        "<table><thead><tr><th>config</th><th>mean_loss over time (oldest → newest)"
        f"</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


def main() -> None:
    summaries, comparisons, _skipped, missing = compute_ablation_results(
        ARTIFACTS_DIR, STANDARD_CONFIGS
    )
    run_at = datetime.now(UTC).isoformat()
    record_leaderboard_entry(ARTIFACTS_DIR, summaries, run_at=run_at)
    history = load_leaderboard_history(ARTIFACTS_DIR)

    html_doc = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Aurora Forecaster -- Ablation Dashboard</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto;
          padding: 0 20px; color: #0b0b0b; background: #fcfcfb; }}
  h1, h2 {{ font-weight: 600; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid #e1e0d9; font-size: 13px; }}
  th {{ color: #52514e; font-weight: 600; }}
  .meta {{ color: #898781; font-size: 13px; }}
</style>
</head>
<body>
<h1>Aurora Forecaster -- Ablation Dashboard</h1>
<p class="meta">Rendered {html.escape(run_at)} &middot; {len(summaries)} scored configs
&middot; missing: {html.escape(", ".join(missing)) if missing else "none"}</p>

<h2>Mean loss by config (lower is better)</h2>
{render_bar_chart(summaries)}

<h2>Pairwise Diebold-Mariano</h2>
{render_comparison_table(comparisons)}

<h2>Trend across runs</h2>
{render_trend_section(history)}
</body>
</html>
"""
    DASHBOARD_PATH.write_text(html_doc)
    print(f"written to {DASHBOARD_PATH}")
    print(f"leaderboard history: {len(history)} total entries")


if __name__ == "__main__":
    main()
