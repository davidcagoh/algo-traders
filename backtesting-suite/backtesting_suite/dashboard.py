"""Self-contained interactive HTML dashboard for every backtest run."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from backtesting_suite.config import RunConfig
from backtesting_suite.data import DataBundle
from backtesting_suite.result import BacktestResult


_PLOT_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}
_COLORS = [
    "#38bdf8", "#f59e0b", "#34d399", "#f472b6", "#a78bfa", "#fb7185",
    "#22d3ee", "#facc15", "#4ade80", "#c084fc", "#f97316", "#94a3b8",
]


def _daily_equity(equity: pd.Series) -> pd.Series:
    if not isinstance(equity.index, pd.DatetimeIndex):
        return equity
    return equity.resample("1D").last().dropna()


def _rolling_sharpe(returns: pd.Series, window: int) -> pd.Series:
    mean = returns.rolling(window, min_periods=window).mean()
    std = returns.rolling(window, min_periods=window).std()
    return mean.div(std.replace(0.0, np.nan)) * np.sqrt(365.0)


def _drawdown_episodes(equity: pd.Series) -> pd.DataFrame:
    """Return the deepest distinct peak-to-recovery drawdown episodes."""

    drawdown = equity.div(equity.cummax()).sub(1.0)
    underwater = drawdown < -1e-12
    rows: list[dict[str, Any]] = []
    start: pd.Timestamp | None = None
    peak: pd.Timestamp | None = None
    previous_timestamp: pd.Timestamp | None = None

    for timestamp, is_underwater in underwater.items():
        if is_underwater and start is None:
            start = timestamp
            peak = previous_timestamp or timestamp
        elif not is_underwater and start is not None:
            segment = drawdown.loc[start:previous_timestamp]
            trough = segment.idxmin()
            rows.append(
                {
                    "peak": peak,
                    "trough": trough,
                    "recovery": timestamp,
                    "depth_pct": float(segment.min() * 100.0),
                    "days": int((timestamp - peak).total_seconds() / 86_400),
                }
            )
            start = None
            peak = None
        previous_timestamp = timestamp

    if start is not None:
        segment = drawdown.loc[start:]
        trough = segment.idxmin()
        end = drawdown.index[-1]
        rows.append(
            {
                "peak": peak,
                "trough": trough,
                "recovery": None,
                "depth_pct": float(segment.min() * 100.0),
                "days": int((end - peak).total_seconds() / 86_400),
            }
        )
    return pd.DataFrame(rows).sort_values("depth_pct").head(10) if rows else pd.DataFrame()


def _stress_rows(equity: pd.Series) -> list[dict[str, str]]:
    rows = []
    for days in (1, 7, 30, 63, 252):
        period_returns = equity.pct_change(days).dropna() * 100.0
        if period_returns.empty:
            continue
        worst_at = period_returns.idxmin()
        rows.append(
            {
                "horizon": f"{days}d",
                "worst": f"{period_returns.loc[worst_at]:.2f}%",
                "ended": worst_at.strftime("%Y-%m-%d"),
                "median": f"{period_returns.median():.2f}%",
                "best": f"{period_returns.max():.2f}%",
            }
        )
    return rows


def _theme(figure: go.Figure, title: str, height: int = 420) -> go.Figure:
    figure.update_layout(
        title={"text": title, "x": 0.01, "xanchor": "left"},
        template="plotly_dark",
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font={"color": "#dbeafe", "family": "Inter, system-ui, sans-serif"},
        hovermode="x unified",
        height=height,
        margin={"l": 60, "r": 35, "t": 62, "b": 48},
        legend={"orientation": "h", "y": 1.08, "x": 1, "xanchor": "right"},
    )
    figure.update_xaxes(gridcolor="#243244", zerolinecolor="#334155")
    figure.update_yaxes(gridcolor="#243244", zerolinecolor="#334155")
    return figure


def _fragment(figure: go.Figure, *, include_plotlyjs: bool = False) -> str:
    return pio.to_html(
        figure,
        full_html=False,
        include_plotlyjs=True if include_plotlyjs else False,
        config=_PLOT_CONFIG,
    )


def _benchmark(data: DataBundle, config: RunConfig, index: pd.Index) -> pd.Series | None:
    symbol = config.evaluation.benchmark
    if not symbol or symbol not in data.symbols:
        return None
    prices = data.field(config.execution.price_field)[symbol].reindex(index).ffill()
    first = prices.first_valid_index()
    if first is None:
        return None
    return prices / prices.loc[first] * 100.0


def _metric_cards(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    execution = summary["execution"]

    def number(value: Any, suffix: str = "", signed: bool = False) -> str:
        if value is None or not np.isfinite(float(value)):
            return "n/a"
        sign = "+" if signed else ""
        return f"{float(value):{sign}.2f}{suffix}"

    values = [
        ("Total return", number(execution["total_return_pct"], "%", signed=True)),
        ("CAGR", number(metrics["cagr_pct"], "%", signed=True)),
        ("Sharpe", number(metrics["sharpe"])),
        ("Max drawdown", number(-metrics["mdd_pct"], "%") if metrics["mdd_pct"] is not None else "n/a"),
        ("Calmar", number(metrics["calmar"])),
        ("Final equity", f"{execution['final_equity']:,.0f}"),
        ("Turnover", f"{execution['total_turnover']:.2f}x"),
        ("Trading costs", f"{execution['transaction_cost']:,.2f}"),
    ]
    return "".join(
        f'<div class="metric"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'
        for label, value in values
    )


def _table(headers: list[str], rows: list[list[str]], empty: str) -> str:
    if not rows:
        return f'<p class="muted">{escape(empty)}</p>'
    head = "".join(f"<th>{escape(value)}</th>" for value in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f"<div class=table-wrap><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def _display_number(value: Any, digits: int = 2, suffix: str = "") -> str:
    if value is None or not np.isfinite(float(value)):
        return "n/a"
    return f"{float(value):.{digits}f}{suffix}"


def build_dashboard_html(
    config: RunConfig,
    data: DataBundle,
    result: BacktestResult,
    summary: dict[str, Any],
) -> str:
    equity = result.equity.astype(float)
    daily = _daily_equity(equity)
    daily_returns = daily.pct_change().dropna()
    drawdown = equity.div(equity.cummax()).sub(1.0).mul(100.0)
    rolling_63_drawdown = daily.div(daily.rolling(63, min_periods=1).max()).sub(1.0).mul(100.0)

    performance = go.Figure()
    performance.add_trace(
        go.Scatter(x=equity.index, y=equity / equity.iloc[0] * 100.0, name="Strategy", line={"width": 2.5, "color": _COLORS[0]})
    )
    benchmark = _benchmark(data, config, equity.index)
    if benchmark is not None:
        performance.add_trace(
            go.Scatter(x=benchmark.index, y=benchmark, name=f"{config.evaluation.benchmark} buy & hold", line={"width": 1.6, "color": _COLORS[1]})
        )
    performance.update_yaxes(title="Growth of 100")
    _theme(performance, "Equity and PnL over time")

    risk = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12)
    risk.add_trace(go.Scatter(x=daily.index, y=_rolling_sharpe(daily_returns, 63), name="63d Sharpe", line={"color": _COLORS[0]}), row=1, col=1)
    risk.add_trace(go.Scatter(x=daily.index, y=_rolling_sharpe(daily_returns, 252), name="252d Sharpe", line={"color": _COLORS[1]}), row=1, col=1)
    risk.add_hline(y=0, line={"color": "#64748b", "dash": "dot"}, row=1, col=1)
    risk.add_trace(go.Scatter(x=daily.index, y=daily_returns.rolling(63).std() * np.sqrt(365) * 100, name="63d vol", line={"color": _COLORS[5]}), row=2, col=1)
    risk.update_yaxes(title="Sharpe", row=1, col=1)
    risk.update_yaxes(title="Volatility %", row=2, col=1)
    _theme(risk, "Rolling risk statistics", 560)

    dd_figure = go.Figure()
    dd_figure.add_trace(go.Scatter(x=drawdown.index, y=drawdown, name="Since-peak drawdown", fill="tozeroy", line={"color": _COLORS[5]}))
    dd_figure.add_trace(go.Scatter(x=rolling_63_drawdown.index, y=rolling_63_drawdown, name="63d-window drawdown", line={"color": _COLORS[1], "width": 1.5}))
    dd_figure.update_yaxes(title="Drawdown %", rangemode="tozero")
    _theme(dd_figure, "Drawdowns")

    weights = go.Figure()
    for position, symbol in enumerate(result.executed_weights.columns):
        weights.add_trace(
            go.Scatter(
                x=result.executed_weights.index,
                y=result.executed_weights[symbol] * 100.0,
                name=str(symbol),
                mode="lines",
                line={"width": 1.5, "color": _COLORS[position % len(_COLORS)]},
            )
        )
    weights.add_hline(y=0, line={"color": "#64748b", "dash": "dot"})
    weights.update_yaxes(title="Executed weight %")
    _theme(weights, "Portfolio weights")

    exposure = make_subplots(specs=[[{"secondary_y": True}]])
    gross = result.executed_weights.abs().sum(axis=1) * 100.0
    net = result.executed_weights.sum(axis=1) * 100.0
    cash = (1.0 - result.executed_weights.sum(axis=1)) * 100.0
    exposure.add_trace(go.Scatter(x=gross.index, y=gross, name="Gross", line={"color": _COLORS[1]}), secondary_y=False)
    exposure.add_trace(go.Scatter(x=net.index, y=net, name="Net", line={"color": _COLORS[2]}), secondary_y=False)
    exposure.add_trace(go.Scatter(x=cash.index, y=cash, name="Cash", line={"color": _COLORS[4]}), secondary_y=False)
    exposure.add_trace(go.Bar(x=result.turnover.index, y=result.turnover * 100.0, name="Turnover", marker_color="#475569", opacity=0.5), secondary_y=True)
    exposure.update_yaxes(title="Exposure %", secondary_y=False)
    exposure.update_yaxes(title="Turnover %", secondary_y=True)
    _theme(exposure, "Exposure and turnover")

    costs = go.Figure()
    cost_columns = [column for column in result.costs.columns if column != "transaction_cost"]
    for position, column in enumerate(cost_columns):
        values = result.costs[column]
        if column == "funding_pnl":
            values = -values
        costs.add_trace(
            go.Scatter(x=values.index, y=values.cumsum(), name=column.replace("_", " ").title(), line={"color": _COLORS[position % len(_COLORS)]})
        )
    costs.update_yaxes(title="Cumulative drag (currency)")
    _theme(costs, "Costs and financing (positive = drag)")

    distribution = go.Figure()
    distribution.add_trace(go.Histogram(x=daily_returns * 100.0, nbinsx=60, name="Daily returns", marker_color=_COLORS[0], opacity=0.8))
    var_5 = float(daily_returns.quantile(0.05) * 100.0) if len(daily_returns) else float("nan")
    if np.isfinite(var_5):
        distribution.add_vline(x=var_5, line={"color": _COLORS[5], "dash": "dash"}, annotation_text="5% VaR")
    distribution.update_xaxes(title="Daily return %")
    distribution.update_yaxes(title="Observations")
    _theme(distribution, "Return distribution")

    monthly_returns = daily.pct_change().add(1.0).groupby([daily.index.year, daily.index.month]).prod().sub(1.0).mul(100.0)
    monthly = monthly_returns.unstack().reindex(columns=range(1, 13))
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    heatmap = go.Figure(go.Heatmap(
        z=monthly.to_numpy(), x=month_labels, y=[str(year) for year in monthly.index],
        colorscale=[[0, "#7f1d1d"], [0.5, "#111827"], [1, "#065f46"]], zmid=0,
        colorbar={"title": "%"}, hovertemplate="%{y} %{x}: %{z:.2f}%<extra></extra>",
    ))
    _theme(heatmap, "Monthly returns", max(360, 110 + 30 * len(monthly)))

    episodes = _drawdown_episodes(daily)
    episode_rows = []
    if not episodes.empty:
        for _, row in episodes.iterrows():
            episode_rows.append([
                row["peak"].strftime("%Y-%m-%d"),
                row["trough"].strftime("%Y-%m-%d"),
                row["recovery"].strftime("%Y-%m-%d") if pd.notna(row["recovery"]) else "Unrecovered",
                f"{row['depth_pct']:.2f}%",
                str(row["days"]),
            ])
    stress_rows = _stress_rows(daily)
    stress_table = _table(
        ["Horizon", "Worst return", "Period ended", "Median", "Best return"],
        [[row[key] for key in ("horizon", "worst", "ended", "median", "best")] for row in stress_rows],
        "Not enough observations for historical stress windows.",
    )
    episode_table = _table(
        ["Peak", "Trough", "Recovery", "Depth", "Days underwater"],
        episode_rows,
        "No drawdown episodes.",
    )
    metrics = summary["metrics"]
    statistic_rows = [
        ["SQN", _display_number(metrics.get("sqn")), "Sample-size-adjusted consistency"],
        ["Skew", _display_number(metrics.get("skew")), "Negative implies a heavier left tail"],
        ["Excess kurtosis", _display_number(metrics.get("kurt_excess")), "High values imply fat tails"],
        ["Tail ratio", _display_number(metrics.get("tail_ratio")), "Upside-tail / downside-tail magnitude"],
        ["CVaR 5%", _display_number(metrics.get("cvar_5_pct"), suffix="%"), "Mean return in the worst 5% of days"],
        ["Ulcer index", _display_number(metrics.get("ulcer_index")), "Depth and persistence of drawdowns"],
        ["Pain index", _display_number(metrics.get("pain_index")), "Mean absolute drawdown"],
        ["Martin ratio", _display_number(metrics.get("martin_ratio")), "CAGR per unit of ulcer risk"],
        ["Observations", str(metrics.get("n_obs", "n/a")), "Return observations"],
    ]
    statistics_table = _table(
        ["Metric", "Value", "Interpretation"], statistic_rows, "No statistics available."
    )
    regime_rows = []
    for label, values in summary.get("regimes", {}).items():
        regime_rows.append(
            [
                str(label).replace("_", " ").title(),
                str(values.get("n_obs", "n/a")),
                _display_number(values.get("cagr_pct"), suffix="%"),
                _display_number(values.get("sharpe")),
                _display_number(values.get("mdd_pct"), suffix="%"),
                _display_number(values.get("calmar")),
            ]
        )
    regime_table = _table(
        ["Regime", "Bars", "CAGR", "Sharpe", "MDD", "Calmar"],
        regime_rows,
        "Regime stress is disabled for this run.",
    )

    figure_fragments = [
        _fragment(performance, include_plotlyjs=True),
        _fragment(risk),
        _fragment(dd_figure),
        _fragment(weights),
        _fragment(exposure),
        _fragment(costs),
        _fragment(distribution),
        _fragment(heatmap),
    ]
    subtitle = (
        f"{config.strategy.import_path} · {config.data.market} {config.data.timeframe} · "
        f"{summary['window']['start'][:10]} to {summary['window']['end'][:10]}"
    )
    generated = escape(str(result.metadata.get("created_at", "")))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Backtest dashboard — {escape(config.experiment)}</title>
<style>
:root {{ color-scheme: dark; font-family: Inter, system-ui, sans-serif; background: #070b14; color: #dbeafe; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #070b14; }}
main {{ width: min(1500px, calc(100% - 32px)); margin: 0 auto; padding: 38px 0 72px; }}
h1 {{ margin: 0 0 8px; font-size: clamp(1.8rem, 4vw, 3rem); letter-spacing: -0.04em; }}
h2 {{ margin: 0 0 18px; font-size: 1.15rem; }}
.subtitle, .muted {{ color: #94a3b8; }}
.metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr)); gap: 12px; margin: 28px 0; }}
.metric, .panel {{ background: #111827; border: 1px solid #243244; border-radius: 12px; box-shadow: 0 12px 35px rgba(0,0,0,.18); }}
.metric {{ padding: 16px; }}
.metric span {{ display: block; color: #94a3b8; font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; }}
.metric strong {{ display: block; margin-top: 7px; font-size: 1.35rem; }}
.grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
.panel {{ overflow: hidden; min-width: 0; }}
.wide {{ grid-column: 1 / -1; }}
.tables {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-top: 16px; }}
.table-panel {{ padding: 22px; }}
.table-wrap {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: .87rem; }}
th, td {{ padding: 10px 8px; border-bottom: 1px solid #243244; text-align: right; white-space: nowrap; }}
th:first-child, td:first-child {{ text-align: left; }}
th {{ color: #94a3b8; font-size: .72rem; text-transform: uppercase; letter-spacing: .06em; }}
footer {{ margin-top: 24px; color: #64748b; font-size: .8rem; }}
@media (max-width: 900px) {{ .grid, .tables {{ grid-template-columns: 1fr; }} .wide {{ grid-column: auto; }} }}
</style>
</head>
<body><main>
<header><h1>{escape(config.experiment)}</h1><div class="subtitle">{escape(subtitle)}</div></header>
<section class="metrics">{_metric_cards(summary)}</section>
<section class="grid">
  <div class="panel wide">{figure_fragments[0]}</div>
  <div class="panel">{figure_fragments[1]}</div>
  <div class="panel">{figure_fragments[2]}</div>
  <div class="panel wide">{figure_fragments[3]}</div>
  <div class="panel">{figure_fragments[4]}</div>
  <div class="panel">{figure_fragments[5]}</div>
  <div class="panel">{figure_fragments[6]}</div>
  <div class="panel">{figure_fragments[7]}</div>
</section>
<section class="tables">
  <div class="panel table-panel"><h2>Historical stress windows</h2>{stress_table}</div>
  <div class="panel table-panel"><h2>Deepest drawdown episodes</h2>{episode_table}</div>
  <div class="panel table-panel"><h2>Risk and path statistics</h2>{statistics_table}</div>
  <div class="panel table-panel"><h2>Benchmark-regime stress</h2>{regime_table}</div>
</section>
<footer>Generated {generated} UTC · Self-contained HTML; no server or internet connection required.</footer>
</main></body></html>
"""


def write_dashboard(
    directory: Path,
    config: RunConfig,
    data: DataBundle,
    result: BacktestResult,
    summary: dict[str, Any],
) -> Path:
    path = directory / "report.html"
    path.write_text(build_dashboard_html(config, data, result, summary))
    return path
