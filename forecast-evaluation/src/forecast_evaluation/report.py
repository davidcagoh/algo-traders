"""Render a self-contained Plotly HTML report from saved evaluation artifacts."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


_COLORS = {"timesfm3": "#1769aa", "zero_return": "#697586", "last_return": "#cf6b32"}


def _metric_figure(go: Any, rows: pd.DataFrame, *, metric: str, title: str, ylabel: str) -> Any:
    figure = go.Figure()
    for symbol, color in (("BTC", "#1769aa"), ("ETH", "#16856b")):
        selected = rows.loc[rows["symbol"] == symbol]
        for model in ("timesfm3", "zero_return", "last_return"):
            model_rows = selected.loc[selected["model"] == model].sort_values("lead_hours")
            if model_rows.empty:
                continue
            figure.add_trace(go.Scatter(
                x=model_rows["lead_hours"], y=model_rows[metric] * 10_000,
                mode="lines", name=f"{symbol} · {model}",
                line={"color": color, "dash": "solid" if model == "timesfm3" else "dot" if model == "zero_return" else "dash"},
                legendgroup=symbol,
            ))
    figure.update_layout(
        title=title, xaxis_title="Forecast lead (hours)", yaxis_title=ylabel,
        template="plotly_white", margin={"l": 70, "r": 25, "t": 60, "b": 55},
        legend={"orientation": "h", "y": -0.25}, hovermode="x unified",
    )
    return figure


def _directional_accuracy_figure(go: Any, rows: pd.DataFrame) -> Any:
    figure = go.Figure()
    for symbol, color in (("BTC", "#1769aa"), ("ETH", "#16856b")):
        selected = rows.loc[rows["symbol"] == symbol]
        # A zero forecast does not make a directional prediction, so its
        # sign-based accuracy would be misleading in this chart.
        for model in ("timesfm3", "last_return"):
            model_rows = selected.loc[selected["model"] == model].sort_values("lead_hours")
            if model_rows.empty:
                continue
            figure.add_trace(go.Scatter(
                x=model_rows["lead_hours"], y=model_rows["directional_accuracy"] * 100,
                mode="lines", name=f"{symbol} · {model}",
                line={
                    "color": color,
                    "dash": "solid" if model == "timesfm3" else "dot" if model == "zero_return" else "dash",
                },
                legendgroup=symbol,
            ))
    figure.update_layout(
        title="Directional accuracy by forecast lead (zero-return omitted)",
        xaxis_title="Forecast lead (hours)", yaxis_title="Directional accuracy (%)",
        template="plotly_white", margin={"l": 70, "r": 25, "t": 60, "b": 55},
        legend={"orientation": "h", "y": -0.25}, hovermode="x unified",
    )
    figure.update_yaxes(range=[0, 100], ticksuffix="%")
    return figure


def _skill_figure(
    go: Any,
    rows: pd.DataFrame,
    *,
    metric: str,
    title: str,
    xaxis_title: str,
) -> Any:
    figure = go.Figure()
    timesfm_rows = rows.loc[rows["model"] == "timesfm3"]
    for symbol, color in (("BTC", "#1769aa"), ("ETH", "#16856b")):
        selected = timesfm_rows.loc[timesfm_rows["symbol"] == symbol].sort_values("lead_hours")
        for baseline, label, dash in (
            ("zero", "zero-return", "solid"),
            ("last_return", "last-return", "dash"),
        ):
            column = f"skill_vs_{baseline}_{metric}"
            if column not in selected:
                continue
            figure.add_trace(go.Scatter(
                x=selected["lead_hours"], y=selected[column],
                mode="lines+markers", name=f"{symbol} vs {label}",
                line={"color": color, "dash": dash},
            ))
    figure.add_hline(y=0, line_dash="dot", line_color="#697586")
    figure.update_layout(
        title=title, xaxis_title=xaxis_title,
        yaxis_title="Skill score (positive is lower error)",
        template="plotly_white", margin={"l": 70, "r": 25, "t": 60, "b": 55},
        legend={"orientation": "h", "y": -0.25}, hovermode="x unified",
    )
    return figure


def _forecast_figure(go: Any, forecasts: pd.DataFrame, *, segment: str, mode: str) -> Any:
    figure = go.Figure()
    sample_labels: list[str] = []
    trace_groups: list[list[int]] = []
    for symbol in ("BTC", "ETH"):
        selected = forecasts.loc[
            (forecasts["segment"] == segment)
            & (forecasts["mode"] == mode)
            & (forecasts["symbol"] == symbol)
            & (forecasts["model"] == "timesfm3")
        ]
        origins = sorted(selected["origin"].unique())
        if not origins:
            continue
        chosen_indices = sorted(set((0, len(origins) // 2, len(origins) - 1)))
        for index in chosen_indices:
            origin = origins[index]
            sample = selected.loc[selected["origin"] == origin].sort_values("lead")
            start = len(figure.data)
            figure.add_trace(go.Scatter(
                x=sample["lead"], y=sample["q10"] * 10_000,
                mode="lines", line={"width": 0}, showlegend=False,
                legendgroup=symbol,
            ))
            figure.add_trace(go.Scatter(
                x=sample["lead"], y=sample["q90"] * 10_000,
                mode="lines", line={"width": 0}, fill="tonexty",
                fillcolor="rgba(23, 105, 170, 0.15)",
                name=f"{symbol} nominal q10–q90", legendgroup=symbol,
            ))
            figure.add_trace(go.Scatter(
                x=sample["lead"], y=sample["q50"] * 10_000,
                mode="lines", name=f"{symbol} q50", line={"color": _COLORS["timesfm3"]},
                legendgroup=symbol,
            ))
            figure.add_trace(go.Scatter(
                x=sample["lead"], y=sample["actual"] * 10_000,
                mode="lines+markers", name=f"{symbol} realized", line={"color": "#bd3f35"},
                marker={"size": 5}, legendgroup=symbol,
            ))
            trace_groups.append(list(range(start, start + 4)))
            sample_labels.append(f"{symbol} · {pd.Timestamp(origin).strftime('%Y-%m-%d %H:%M UTC')}")
    if trace_groups:
        visibility = [False] * len(figure.data)
        for trace_index in trace_groups[0]:
            visibility[trace_index] = True
        for trace_index, trace in enumerate(figure.data):
            trace.visible = visibility[trace_index]
        buttons = []
        for label, group in zip(sample_labels, trace_groups, strict=True):
            visible = [False] * len(figure.data)
            for trace_index in group:
                visible[trace_index] = True
            buttons.append({"label": label, "method": "update", "args": [{"visible": visible}]})
        figure.update_layout(updatemenus=[{
            "buttons": buttons, "direction": "down", "x": 0, "y": 1.18,
            "xanchor": "left", "yanchor": "top",
        }])
    figure.add_hline(y=0, line_dash="dot", line_color="#9aa4b2", line_width=1)
    figure.add_vline(x=0, line_dash="dash", line_color="#697586", line_width=1)
    figure.add_annotation(
        x=0, y=1, yref="paper", text="Forecast origin · lead 0",
        showarrow=False, xanchor="left", yanchor="bottom",
        font={"size": 11, "color": "#54647d"},
    )
    if not forecasts.empty:
        figure.update_xaxes(range=[0, float(forecasts["lead"].max())])
    figure.update_layout(
        title="Hourly return forecasts at selected rolling origins",
        xaxis_title="Lead hour", yaxis_title="Log return (basis points)",
        template="plotly_white", margin={"l": 75, "r": 25, "t": 105, "b": 60},
        legend={"orientation": "h", "y": -0.25}, hovermode="x unified",
    )
    return figure


def _calibration_figure(go: Any, rows: pd.DataFrame, *, metric: str, title: str, ylabel: str) -> Any:
    figure = go.Figure()
    for symbol, color in (("BTC", "#1769aa"), ("ETH", "#16856b")):
        selected = rows.loc[rows["symbol"] == symbol].sort_values("lead_hours")
        if selected.empty:
            continue
        figure.add_trace(go.Scatter(
            x=selected["lead_hours"], y=selected[metric] if metric.endswith("coverage") else selected[metric] * 10_000,
            mode="lines+markers", name=symbol, line={"color": color},
        ))
    if metric.endswith("coverage"):
        figure.add_hline(y=0.8, line_dash="dash", line_color="#bd3f35", annotation_text="Nominal 80%")
        figure.update_yaxes(range=[0, 1], tickformat=".0%")
    figure.update_layout(
        title=title, xaxis_title="Forecast lead (hours)", yaxis_title=ylabel,
        template="plotly_white", margin={"l": 75, "r": 25, "t": 60, "b": 55},
        legend={"orientation": "h", "y": -0.25}, hovermode="x unified",
    )
    return figure


def _summary_row(rows: pd.DataFrame, *, segment: str, mode: str) -> dict[str, Any] | None:
    selected = rows.loc[
        (rows["segment"] == segment)
        & (rows["mode"] == mode)
        & (rows["model"] == "timesfm3")
    ]
    if selected.empty:
        return None
    return {
        "zero_skill": float(selected["skill_vs_zero_mae"].mean()),
        "persistence_skill": float(selected["skill_vs_last_return_mae"].mean()),
        "directional_accuracy": float(selected["directional_accuracy"].mean()),
        "origins": int(selected["n"].min()),
    }


def _percent(value: float, *, signed: bool = False) -> str:
    return f"{value * 100:+.1f}%" if signed else f"{value * 100:.1f}%"


def _inference_summary(analysis: dict[str, Any] | None) -> tuple[str, str]:
    if not analysis:
        return "", ""
    rows = [
        row for row in analysis["comparisons"]
        if (row["kind"] == "cumulative" and row["horizon"] == 24)
        or (row["kind"] == "lead" and row["horizon"] in {1, 6, 24})
    ]
    body = "".join(
        "<tr>"
        f"<th scope=\"row\">{html.escape(row['segment'].replace('_', ' ').title())}<br>"
        f"<span>{html.escape(row['symbol'])} · {html.escape(row['mode'])}</span></th>"
        f"<td>{'Cumulative return' if row['kind'] == 'cumulative' else 'One-hour return · lead'} {row['horizon']}h</td>"
        f"<td>{html.escape(row['baseline'].replace('_', ' '))}</td>"
        f"<td>{row['mae_difference'] * 10_000:+.2f} bp"
        f"<small>95% CI [{row['ci95_low'] * 10_000:+.2f}, {row['ci95_high'] * 10_000:+.2f}]</small></td>"
        f"<td>{row['p_value_holm']:.3f}</td><td>{row['n_origins']}</td></tr>"
        for row in rows
    )
    table = (
        '<div class="table-wrap"><table class="decision-table"><thead><tr>'
        '<th scope="col">Slice · asset · mode</th><th scope="col">Scored endpoint</th>'
        '<th scope="col">Baseline</th><th scope="col">Paired MAE difference</th>'
        '<th scope="col">Holm adjusted p</th><th scope="col">Origins</th>'
        f"</tr></thead><tbody>{body}</tbody></table></div>"
    )
    details = (
        "Paired per-origin absolute-loss differences (TimesFM minus baseline); negative favors TimesFM. "
        "Intervals use a stationary block bootstrap with the same origin resamples across assets and modes. "
        f"Holm correction covers all {analysis['multiplicity']['family_size']} saved lead and cumulative-horizon comparisons. "
        "This analysis was specified after the forecast results were inspected, so it is exploratory rather than confirmatory. "
        "The post-release sample is small; do not read a non-significant result as evidence of equivalence. "
        "Post-release cumulative horizons beyond one hour are unavailable because the frozen forecasts saved only leads 1, 6, and 24, not every intervening hour."
    )
    return table, details


def _inference_figure(go: Any, analysis: dict[str, Any]) -> Any:
    rows = [
        row for row in analysis["comparisons"]
        if (row["kind"] == "cumulative" and row["horizon"] == 24)
        or (row["kind"] == "lead" and row["horizon"] in {1, 6, 24})
    ]
    figure = go.Figure()
    for baseline, label, color, symbol in (
        ("zero_return", "Predict no change", "#697586", "circle"),
        ("last_return", "Repeat last return", "#cf6b32", "diamond"),
    ):
        selected = [row for row in rows if row["baseline"] == baseline]
        labels = [
            f"{row['segment'].replace('_', ' ')} · {row['kind']} {row['horizon']}h · "
            f"{row['symbol']} · {row['mode']}"
            for row in selected
        ]
        point = [row["mae_difference"] * 10_000 for row in selected]
        low = [row["ci95_low"] * 10_000 for row in selected]
        high = [row["ci95_high"] * 10_000 for row in selected]
        figure.add_trace(go.Scatter(
            x=point, y=labels, mode="markers", name=label,
            marker={"color": color, "symbol": symbol, "size": 8},
            error_x={
                "type": "data", "symmetric": False,
                "array": [upper - center for upper, center in zip(high, point, strict=True)],
                "arrayminus": [center - lower for center, lower in zip(point, low, strict=True)],
                "color": color, "thickness": 1.5, "width": 3,
            },
            customdata=[[row["p_value_holm"], row["n_origins"]] for row in selected],
            hovertemplate=(
                "%{y}<br>Difference: %{x:.2f} bp<br>"
                "Holm adjusted p: %{customdata[0]:.3f}<br>"
                "Origins: %{customdata[1]}<extra>%{fullData.name}</extra>"
            ),
        ))
    figure.add_vline(x=0, line_dash="dash", line_color="#14233b")
    figure.update_layout(
        title="Paired forecast-loss differences with 95% block-bootstrap intervals",
        xaxis_title="MAE difference in basis points (negative favors TimesFM)",
        yaxis_title="Segment · scored endpoint · asset · mode",
        height=max(720, len(rows) * 23), template="plotly_white",
        margin={"l": 310, "r": 35, "t": 65, "b": 70},
        legend={"orientation": "h", "y": -0.14},
    )
    return figure


def render_report(run_dir: str | Path, *, analysis_path: str | Path | None = None) -> str:
    """Return a complete offline HTML document for a saved evaluation run."""
    try:
        import plotly.graph_objects as go
    except ImportError as exc:
        raise ImportError("install forecast-evaluation[report] to render the HTML viewer") from exc

    root = Path(run_dir).resolve()
    forecasts = pd.read_parquet(root / "forecasts.parquet")
    metrics = json.loads((root / "metrics.json").read_text())
    metadata = json.loads((root / "metadata.json").read_text())
    analysis = json.loads(Path(analysis_path).read_text()) if analysis_path else None
    inference_table, inference_details = _inference_summary(analysis)
    lead_metrics = pd.DataFrame(metrics["lead_return_metrics"])
    cumulative_metrics = pd.DataFrame(metrics["cumulative_return_metrics"])
    report_sections: list[str] = []
    section_links: list[str] = []
    include_plotly = True
    figure_count = 0

    def add_figure(figure: Any, label: str) -> None:
        nonlocal include_plotly, figure_count
        figure_html = figure.to_html(
            full_html=False, include_plotlyjs=include_plotly, include_mathjax=False,
            config={"displaylogo": False, "responsive": True},
            div_id=f"forecast-figure-{figure_count:03d}",
        )
        figure_count += 1
        include_plotly = False
        report_sections.append(f'<section class="chart" aria-label="{html.escape(label)}">{figure_html}</section>')

    for segment in sorted(forecasts["segment"].unique()):
        for mode in sorted(forecasts["mode"].unique(), key=lambda value: value != "univariate"):
            subset = forecasts.loc[
                (forecasts["segment"] == segment) & (forecasts["mode"] == mode)
            ]
            if subset.empty:
                continue
            section_id = re.sub(r"[^a-z0-9-]+", "-", f"{segment}-{mode}".lower()).strip("-")
            section_links.append(
                f'<a href="#{section_id}">{html.escape(segment.replace("_", " ").title())} · '
                f'{html.escape(mode.title())}</a>'
            )
            lead_rows = lead_metrics.loc[
                (lead_metrics["segment"] == segment) & (lead_metrics["mode"] == mode)
            ]
            cumulative = cumulative_metrics.loc[
                (cumulative_metrics["segment"] == segment)
                & (cumulative_metrics["mode"] == mode)
            ]
            section_intro = (
                "Historical replay may overlap TimesFM pretraining."
                if segment == "historical_replay"
                else f"Post-release freshness check · {int(subset.groupby('symbol')['origin'].nunique().min())} origins per asset; exploratory only."
            )
            report_sections.append(
                f'<section id="{section_id}" class="analysis-block"><h3>{html.escape(segment.replace("_", " ").title())} · '
                f'{html.escape(mode.title())}</h3><p class="section-intro">'
                f'{html.escape(section_intro)} Compare TimesFM with both simple baselines across forecast lead.</p>'
            )
            add_figure(_forecast_figure(go, subset, segment=segment, mode=mode), "Selected forecast paths")
            add_figure(
                _metric_figure(go, lead_rows, metric="mae", title="One-hour return MAE by forecast lead", ylabel="MAE (bp)"),
                "One-hour return MAE by lead",
            )
            add_figure(
                _metric_figure(go, lead_rows, metric="rmse", title="One-hour return RMSE by forecast lead", ylabel="RMSE (bp)"),
                "One-hour return RMSE by lead",
            )
            add_figure(
                _directional_accuracy_figure(go, lead_rows),
                "Directional accuracy by lead",
            )
            timesfm_lead = lead_rows.loc[lead_rows["model"] == "timesfm3"]
            add_figure(
                _metric_figure(go, timesfm_lead, metric="pinball_loss", title="Pinball loss by forecast lead", ylabel="Mean pinball loss (bp)"),
                "Quantile pinball loss by lead",
            )
            add_figure(
                _metric_figure(go, cumulative, metric="mae", title="Cumulative-return MAE by horizon", ylabel="MAE (bp)"),
                "Cumulative return MAE",
            )
            add_figure(
                _metric_figure(go, cumulative, metric="rmse", title="Cumulative-return RMSE by horizon", ylabel="RMSE (bp)"),
                "Cumulative return RMSE",
            )
            add_figure(
                _skill_figure(
                    go, lead_rows, metric="mae",
                    title="One-hour return MAE skill versus baselines",
                    xaxis_title="Forecast lead (hours)",
                ),
                "One-hour return MAE skill by lead",
            )
            add_figure(
                _skill_figure(
                    go, lead_rows, metric="rmse",
                    title="One-hour return RMSE skill versus baselines",
                    xaxis_title="Forecast lead (hours)",
                ),
                "One-hour return RMSE skill by lead",
            )
            add_figure(
                _skill_figure(
                    go, cumulative, metric="mae",
                    title="Cumulative-return MAE skill versus baselines",
                    xaxis_title="Cumulative horizon (hours)",
                ),
                "Cumulative return MAE skill by horizon",
            )
            add_figure(
                _skill_figure(
                    go, cumulative, metric="rmse",
                    title="Cumulative-return RMSE skill versus baselines",
                    xaxis_title="Cumulative horizon (hours)",
                ),
                "Cumulative return RMSE skill by horizon",
            )
            if not timesfm_lead.empty:
                add_figure(
                    _calibration_figure(
                        go, timesfm_lead, metric="nominal_80_coverage",
                        title="Marginal q10–q90 coverage (nominal target 80%)",
                        ylabel="Observed coverage",
                    ),
                    "Nominal interval coverage by lead",
                )
                add_figure(
                    _calibration_figure(
                        go, timesfm_lead, metric="nominal_80_width",
                        title="Marginal q10–q90 interval width", ylabel="Width (bp)",
                    ),
                    "Nominal interval width by lead",
                )
            report_sections.append("</section>")

    if analysis:
        add_figure(
            _inference_figure(go, analysis),
            "Paired MAE differences and pointwise block-bootstrap intervals",
        )

    origin_count = sum(item["origins"] for item in metadata["origin_counts"])
    snapshot = metadata["snapshot"]
    model = metadata["model"]
    protocol = metadata["protocol"]
    limitations = "".join(f"<li>{html.escape(item)}</li>" for item in metadata["limitations"])
    summary_rows = []
    for segment, label in (
        ("historical_replay", "Historical replay"),
        ("post_release_freshness", "Recent-data check"),
    ):
        for mode in ("univariate", "multivariate"):
            row = _summary_row(lead_metrics, segment=segment, mode=mode)
            if row is None:
                continue
            sample = f'{row["origins"]} origins / asset'
            summary_rows.append(
                "<tr>"
                f"<th scope=\"row\">{label}<br><span>{mode.title()}</span></th>"
                f"<td>{_percent(row['zero_skill'], signed=True)}<small>{'worse' if row['zero_skill'] < 0 else 'better'} vs no-change</small></td>"
                f"<td>{_percent(row['persistence_skill'], signed=True)}<small>{'better' if row['persistence_skill'] > 0 else 'worse'} vs repeat-last-hour</small></td>"
                f"<td>{_percent(row['directional_accuracy'])}<small>{sample}</small></td>"
                "</tr>"
            )
    summary_table = "".join(summary_rows)
    historical_rows = [
        row for mode in ("univariate", "multivariate")
        if (row := _summary_row(lead_metrics, segment="historical_replay", mode=mode)) is not None
    ]
    freshness_rows = [
        row for mode in ("univariate", "multivariate")
        if (row := _summary_row(lead_metrics, segment="post_release_freshness", mode=mode)) is not None
    ]
    historical_zero_skill = (
        sum(row["zero_skill"] for row in historical_rows) / len(historical_rows)
        if historical_rows else 0.0
    )
    historical_persistence_skill = (
        sum(row["persistence_skill"] for row in historical_rows) / len(historical_rows)
        if historical_rows else 0.0
    )
    historical_direction = (
        sum(row["directional_accuracy"] for row in historical_rows) / len(historical_rows)
        if historical_rows else 0.0
    )
    comparison_count = analysis["multiplicity"]["family_size"] if analysis else 0
    significant_timesfm_count = sum(
        row["p_value_holm"] < 0.05 and row["mae_difference"] < 0
        for row in analysis["comparisons"]
    ) if analysis else None
    significant_baseline_count = sum(
        row["p_value_holm"] < 0.05 and row["mae_difference"] > 0
        for row in analysis["comparisons"]
    ) if analysis else None
    significant_count = (
        significant_timesfm_count + significant_baseline_count
        if analysis else None
    )
    min_adjusted_p = min(
        (row["p_value_holm"] for row in analysis["comparisons"]), default=1.0
    ) if analysis else 1.0
    zero_comparison = (
        f"{_percent(abs(historical_zero_skill))} "
        f"{'lower' if historical_zero_skill > 0 else 'higher'} than the no-change baseline"
    )
    persistence_comparison = (
        f"{_percent(abs(historical_persistence_skill))} "
        f"{'lower' if historical_persistence_skill > 0 else 'higher'} than repeating the last return"
    )
    baseline_result = (
        f"In historical replay, average MAE was {zero_comparison} and "
        f"{persistence_comparison}. Direction accuracy was {_percent(historical_direction)}."
        if historical_rows else "The historical replay baseline summary is unavailable for this run."
    )
    uncertainty_result = (
        f"Among {comparison_count:,} Holm-adjusted paired comparisons, "
        f"{significant_timesfm_count} favor TimesFM and {significant_baseline_count} favor a baseline "
        f"at the 5% threshold; the smallest adjusted p-value is {min_adjusted_p:.3f}. "
        "This post-hoc analysis is exploratory."
        if analysis and significant_count
        else f"None of {comparison_count:,} paired comparisons passes the Holm-adjusted 5% threshold; "
        f"the smallest adjusted p-value is {min_adjusted_p:.3f}. This post-hoc analysis is exploratory."
        if analysis else "Paired uncertainty analysis is not available in this report."
    )
    if not historical_rows:
        conclusion_sentence = "This run cannot support a conclusion about historical forecast skill."
    elif analysis and significant_timesfm_count and significant_baseline_count:
        conclusion_sentence = "Adjusted comparisons point in both directions; this post-hoc analysis remains exploratory."
    elif analysis and significant_timesfm_count:
        conclusion_sentence = "Some adjusted comparisons favor TimesFM, but this post-hoc analysis remains exploratory."
    elif analysis and significant_baseline_count:
        conclusion_sentence = "Some adjusted comparisons favor the baselines; this post-hoc analysis remains exploratory."
    elif analysis:
        conclusion_sentence = "No adjusted comparison establishes an improvement over the no-change baseline."
    elif historical_zero_skill > 0:
        conclusion_sentence = "Mean MAE is lower than no-change, but paired uncertainty was not assessed."
    else:
        conclusion_sentence = "Mean MAE was not lower than no-change, and paired uncertainty was not assessed."
    historical_direction_result = (
        f"Historical direction accuracy was {_percent(historical_direction)}."
        if historical_rows else "Historical direction accuracy is unavailable for this run."
    )
    freshness_origins = min((row["origins"] for row in freshness_rows), default=None)
    freshness_limit = (
        f"The recent-data slice contains {freshness_origins} origins per asset."
        if freshness_origins is not None else "No separate recent-data slice is available in this run."
    )
    freshness_size_note = (
        " This is a small exploratory sample."
        if freshness_origins is not None and freshness_origins <= 30 else ""
    )
    persistence_result = (
        f"On average, TimesFM's MAE was {persistence_comparison}."
        if historical_rows else "No historical repeat-last comparison is available for this run."
    )
    if not historical_rows:
        headline = "An exploratory test of TimesFM forecasts against simple baselines."
    elif historical_persistence_skill > 0 and historical_zero_skill <= 0:
        headline = f"A {_percent(historical_persistence_skill)} win—and no evidence it beats doing nothing."
    else:
        headline = f"Historical mean MAE was {zero_comparison}."
    lede = (
        f"We tested TimesFM 3.0 on rolling BTC and ETH hourly-return forecasts. On historical replay, "
        f"average MAE was {zero_comparison} and {persistence_comparison}."
        if historical_rows else
        "We tested TimesFM 3.0 on rolling BTC and ETH hourly-return forecasts; historical baseline scores are unavailable for this run."
    )
    if not historical_rows:
        verdict_title = "Historical baseline evidence is unavailable for this run."
    elif analysis and significant_timesfm_count and significant_baseline_count:
        verdict_title = "Adjusted comparisons point both ways; the finding remains exploratory."
    elif analysis and significant_timesfm_count:
        verdict_title = "Some adjusted comparisons favor TimesFM; the finding remains exploratory."
    elif analysis and significant_baseline_count:
        verdict_title = "Some adjusted comparisons favor the baselines; the finding remains exploratory."
    elif historical_zero_skill > 0 and not analysis:
        verdict_title = "Mean MAE is lower than no-change, but paired uncertainty was not assessed."
    elif analysis:
        verdict_title = "This run does not establish an improvement over “predict no change.”"
    elif historical_zero_skill <= 0:
        verdict_title = "This run did not lower average MAE versus “predict no change.”"
    else:
        verdict_title = "Historical baseline evidence is unavailable for this run."
    baseline_argument_title = (
        "The apparent win depends on the comparator."
        if historical_rows and historical_persistence_skill > 0 and historical_zero_skill <= 0
        else "Baseline comparisons define what this result can support."
    )
    uncertainty_title = (
        "The paired comparisons do not establish an improvement."
        if analysis and significant_count == 0
        else "Adjusted comparisons point in both directions."
        if analysis and significant_timesfm_count and significant_baseline_count
        else "Some adjusted comparisons favor TimesFM."
        if analysis and significant_timesfm_count
        else "Some adjusted comparisons favor the baselines."
        if analysis
        else "Paired uncertainty was not tested in this report."
    )
    cumulative_168 = cumulative_metrics.loc[
        (cumulative_metrics["segment"] == "historical_replay")
        & (cumulative_metrics["lead_hours"] == 168)
        & (cumulative_metrics["model"] == "timesfm3")
    ]
    zero_168 = cumulative_168["skill_vs_zero_mae"].tolist()
    persistence_168 = cumulative_168["skill_vs_last_return_mae"].tolist()
    long_horizon_summary = ""
    if zero_168:
        n_cases = len(zero_168)
        if all(value < 0 for value in zero_168):
            long_horizon_summary = (
                "At 168 hours, TimesFM's cumulative-return MAE was "
                f"{_percent(min(abs(value) for value in zero_168))}–{_percent(max(abs(value) for value in zero_168))} "
                f"higher than no-change in all {n_cases} available asset/mode comparisons."
            )
        elif all(value > 0 for value in zero_168):
            long_horizon_summary = (
                "At 168 hours, TimesFM's cumulative-return MAE was "
                f"{_percent(min(zero_168))}–{_percent(max(zero_168))} lower than no-change "
                f"in all {n_cases} available asset/mode comparisons."
            )
        else:
            long_horizon_summary = (
                f"At 168 hours, MAE skill versus no-change ranged from {_percent(min(zero_168), signed=True)} "
                f"to {_percent(max(zero_168), signed=True)} across {n_cases} available asset/mode comparisons "
                "(positive values favor TimesFM)."
            )
        if persistence_168 and all(value > 0 for value in persistence_168):
            long_horizon_summary += " TimesFM also had lower MAE than the repeat-last baseline at this horizon."
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TimesFM BTC/ETH forecast evaluation</title>
<style>
:root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #14233b; background: #f3f6fa; }}
body {{ margin: 0; }} main {{ max-width: 1180px; margin: 0 auto; padding: 34px 26px 64px; }}
h1 {{ margin: 0; font-size: clamp(2rem, 3.2vw, 3.15rem); letter-spacing: -.04em; line-height: 1.05; }}
h2 {{ margin: 38px 0 12px; font-size: 1.5rem; letter-spacing: -.025em; }}
h3 {{ margin: 0 0 4px; font-size: 1.2rem; }}
.eyebrow {{ margin: 0 0 12px; color: #53647d; font-size: .78rem; font-weight: 750; letter-spacing: .12em; text-transform: uppercase; }}
.lede {{ color: #4b5a70; font-size: 1.08rem; max-width: 820px; line-height: 1.58; }}
.verdict {{ margin: 24px 0 18px; padding: 22px 24px; border: 1px solid #bfd2ed; border-left: 6px solid #245e9d; border-radius: 14px; background: linear-gradient(110deg, #eaf2fc, #fff 78%); }}
.verdict-label {{ margin: 0 0 6px; color: #245e9d; font-size: .76rem; font-weight: 750; letter-spacing: .1em; text-transform: uppercase; }}
.verdict h2 {{ margin: 0 0 8px; font-size: clamp(1.25rem, 2vw, 1.8rem); }}
.verdict p {{ max-width: 880px; margin: 0; color: #34445b; line-height: 1.6; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin: 18px 0 28px; }}
.card {{ background: white; border: 1px solid #dce3ed; border-radius: 12px; padding: 15px 16px; box-shadow: 0 2px 8px #1522380a; }}
.card strong {{ display: block; color: #54647d; font-size: .72rem; letter-spacing: .07em; text-transform: uppercase; margin-bottom: 7px; }}
.card span {{ font-size: .96rem; overflow-wrap: anywhere; line-height: 1.45; }}
.argument-grid, .length-grid, .qa-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; margin: 14px 0 22px; }}
.argument, .length-grid article, .qa-grid article {{ padding: 17px 18px; background: #fff; border: 1px solid #dce3ed; border-radius: 12px; line-height: 1.55; }}
.argument-number {{ color: #245e9d; font-size: .72rem; font-weight: 750; letter-spacing: .08em; text-transform: uppercase; }}
.argument h3, .length-grid h3, .qa-grid h3 {{ margin: 7px 0; font-size: 1rem; }}
.argument p, .length-grid p, .qa-grid p {{ margin: 7px 0; color: #4b5a70; }}
.argument a {{ color: #245e9d; font-size: .88rem; font-weight: 650; }}
.story-lengths {{ margin: 18px 0; padding: 14px 17px; background: #fff; border: 1px solid #dce3ed; border-radius: 12px; }}
.story-lengths summary {{ cursor: pointer; color: #245e9d; font-weight: 700; }}
.story-lengths .length-grid, .story-lengths .qa-grid {{ margin-bottom: 4px; }}
.decision-table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #dce3ed; border-radius: 12px; overflow: hidden; }}
.decision-table th, .decision-table td {{ padding: 13px 15px; border-bottom: 1px solid #e7ecf2; text-align: left; vertical-align: top; }}
.decision-table thead th {{ background: #edf2f8; color: #4c5d74; font-size: .75rem; letter-spacing: .045em; text-transform: uppercase; }}
.decision-table tbody th {{ min-width: 150px; font-size: .92rem; }}
.decision-table tbody th span, .decision-table small {{ display: block; margin-top: 4px; color: #65748a; font-size: .78rem; font-weight: 450; }}
.definition-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin: 14px 0 22px; }}
.definition {{ padding: 16px 17px; background: #fff; border: 1px solid #dce3ed; border-radius: 12px; line-height: 1.55; }}
.definition strong {{ display: block; margin-bottom: 5px; }}
.notice {{ margin: 18px 0; border-left: 4px solid #b56b16; background: #fff8e9; padding: 15px 18px; border-radius: 0 9px 9px 0; line-height: 1.55; }}
.notice strong {{ display: block; margin-bottom: 4px; }}
.analysis-block {{ margin-top: 32px; padding-top: 22px; border-top: 1px solid #d7dfeb; }}
.section-intro {{ margin: 0 0 14px; color: #5b6a7e; line-height: 1.5; }}
.chart {{ background: white; border: 1px solid #dce3ed; border-radius: 12px; margin: 14px 0; overflow: hidden; }}
.limitations {{ background: white; border: 1px solid #dce3ed; border-radius: 12px; padding: 13px 22px 13px 42px; line-height: 1.65; }}
.method {{ background: white; border: 1px solid #dce3ed; border-radius: 12px; padding: 16px 19px; line-height: 1.6; }}
.method summary {{ cursor: pointer; font-weight: 700; }}
.method p {{ color: #4b5a70; }}
.chart-guide {{ color: #5b6a7e; margin: -4px 0 14px; line-height: 1.5; }}
.section-nav {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 22px; }}
.section-nav a {{ display: inline-block; padding: 8px 12px; background: white; border: 1px solid #dce3ed; border-radius: 999px; color: #245e9d; font-size: .88rem; font-weight: 650; text-decoration: none; }}
.section-nav a:hover, .section-nav a:focus-visible {{ border-color: #245e9d; background: #eaf2fc; outline: 2px solid #245e9d; outline-offset: 2px; }}
footer {{ color: #54647d; margin-top: 24px; font-size: .88rem; }}
@media (max-width: 680px) {{ main {{ padding: 22px 12px 40px; }} .chart {{ overflow-x: auto; }} .decision-table {{ font-size: .83rem; }} .decision-table th, .decision-table td {{ padding: 10px 8px; }} .decision-table tbody th {{ min-width: auto; }} }}
</style></head><body><main>
<p class="eyebrow">Forecast evaluation · BTC and ETH · Hourly returns</p>
<h1>{html.escape(headline)}</h1>
<p class="lede">{html.escape(lede)}</p>
<section class="verdict" aria-labelledby="verdict-title">
<p class="verdict-label">The answer</p>
<h2 id="verdict-title">{html.escape(verdict_title)}</h2>
<p>{html.escape(baseline_result)} {html.escape(uncertainty_result)} This is an exploratory forecast evaluation—not evidence of a trading edge.</p>
</section>
<section aria-labelledby="question-title">
<h2 id="question-title">The question: does a foundation model add signal beyond a simple forecast?</h2>
<p class="chart-guide">Crypto returns are noisy, so a complex model can look impressive against a weak comparator. We compared it with both repeating the last hourly return and predicting zero return. The second baseline asks whether the model improves on simply expecting no price change.</p>
<div class="argument-grid">
<article class="argument"><span class="argument-number">01 · Baseline test</span><h3>{html.escape(baseline_argument_title)}</h3><p>{html.escape(f"TimesFM's average MAE was {persistence_comparison}, but {zero_comparison}.") if historical_rows else "The historical baseline comparison is unavailable for this run."}</p><a href="#baseline-exhibit">See Exhibit 1 · Baseline scores ↓</a></article>
<article class="argument"><span class="argument-number">02 · Uncertainty test</span><h3>{html.escape(uncertainty_title)}</h3><p>{html.escape(uncertainty_result)}</p><a href="#uncertainty-exhibit">See Exhibit 2 · Paired uncertainty ↓</a></article>
<article class="argument"><span class="argument-number">03 · Trading boundary</span><h3>Forecast accuracy is not a trading result.</h3><p>{html.escape(historical_direction_result)} We did not simulate positions, costs, execution, or portfolio returns, so this test cannot establish profitability.</p><a href="#trading-boundary">See Exhibit 3 · What was not tested ↓</a></article>
</div>
</section>
<details class="story-lengths"><summary>Presentation versions · 30 seconds to 60 minutes</summary>
<div class="length-grid">
<article><h3>30 seconds</h3><p>{html.escape(lede)} {html.escape(uncertainty_result)} The result is exploratory and does not establish a trading edge.</p></article>
<article><h3>2 minutes</h3><p>A large foundation model can look useful if it is compared with an easy baseline. {html.escape(baseline_result)} {html.escape(uncertainty_result)} {html.escape(freshness_limit + freshness_size_note)} We did not test a trading strategy, costs, or execution. {html.escape(conclusion_sentence)} This is not a trading result.</p></article>
<article><h3>10 minutes</h3><p>Walk through the baseline table first: the result changes with the comparator. Then show the paired loss intervals and explain that forecasts were compared at the same origins, with temporal dependence handled by a stationary block bootstrap and the complete comparison family corrected using Holm. Emphasize that this inference plan was post hoc and historical targets may overlap model pretraining. {html.escape(freshness_limit + freshness_size_note)} Finish with the longer-horizon result: {html.escape(long_horizon_summary) if long_horizon_summary else 'no 168-hour cumulative result is available for this run.'} The test scores forecasts, not a strategy; it includes no transaction costs or portfolio returns.</p></article>
<article><h3>60 minutes</h3><p>Start with the baseline and uncertainty exhibits, then use the optional diagnostics only to investigate a specific question about horizon effects, forecast shape, calibration, or historical versus post-release behavior. Keep historical replay separate from the {freshness_origins if freshness_origins is not None else 'unavailable'}-origin post-release freshness check. Close by reviewing the limits and the skeptical-reader answers below. {html.escape(conclusion_sentence)} Forecast accuracy does not establish trading performance.</p></article>
</div></details>
<h2 id="baseline-exhibit">Exhibit 1 · The baseline changes the story</h2>
<p class="chart-guide">MAE skill compares TimesFM's mean absolute error with each baseline. Positive means TimesFM made smaller errors; negative means the baseline did better.</p>
<div class="table-wrap"><table class="decision-table"><thead><tr><th scope="col">Evaluation slice</th><th scope="col">vs. predict no change</th><th scope="col">vs. repeat last return</th><th scope="col">Direction correct</th></tr></thead><tbody>{summary_table}</tbody></table></div>
{f'<details id="uncertainty-exhibit" class="story-lengths"><summary>Exhibit 2 · Inspect the paired uncertainty estimates</summary><p class="chart-guide">{html.escape(inference_details)}</p>{inference_table}</details>' if analysis else ''}
<div class="notice"><strong>Longer-horizon check</strong>{html.escape(long_horizon_summary or "No 168-hour cumulative-return result is available for this run.")}</div>
<h2 id="trading-boundary">Exhibit 3 · Forecast scores are not portfolio returns</h2>
<div class="definition-grid">
<div class="definition"><strong>What this test scores</strong>Mean absolute error averages the size of each forecast miss in hourly returns. Lower is better; it says nothing by itself about net trading returns.</div>
<div class="definition"><strong>Predict no change</strong>The zero-return baseline assumes the next hourly return is zero, or equivalently that price stays where it is.</div>
<div class="definition"><strong>Repeat the latest return</strong>The persistence baseline assumes the most recent hourly return repeats into the forecast. {html.escape(persistence_result)} At long horizons, this baseline can perform poorly.</div>
</div>
<p class="chart-guide">The table averages assets and forecast leads equally within each mode. “Direction correct” is sign accuracy, not profitability. No positions, transaction costs, execution rules, or portfolio returns were evaluated.</p>
<details class="story-lengths"><summary>Questions a skeptical reader may ask</summary>
<div class="qa-grid">
<article><h3>What does the repeat-last comparison show?</h3><p>{html.escape(f"Average MAE was {persistence_comparison}; against no-change it was {zero_comparison}. The comparator matters.") if historical_rows else "The historical baseline comparison is unavailable for this run."}</p></article>
<article><h3>Do non-significant results prove the model and baseline are equivalent?</h3><p>No. A non-significant result is not evidence of equivalence. This analysis is post hoc, historical results may overlap pretraining.{html.escape(freshness_size_note)}</p></article>
<article><h3>Why correct across many comparisons?</h3><p>{html.escape(f"The saved forecasts support {comparison_count:,} lead and cumulative-horizon comparisons across assets, modes, and segments. Holm correction accounts for this family. {uncertainty_result}") if analysis else "The saved forecasts support multiple leads and horizons; this report does not include a paired uncertainty analysis."}</p></article>
<article><h3>Could this still make money?</h3><p>This report cannot answer that. It evaluates forecast errors, not a trading strategy. A separate prospective backtest would need explicit signals, execution, fees, and risk controls.</p></article>
<article><h3>Is the historical replay an out-of-sample test?</h3><p>It is rolling-origin relative to the observed price series, but the historical target period may overlap TimesFM pretraining. It should not be presented as uncontaminated holdout evidence.</p></article>
<article><h3>What would strengthen the conclusion?</h3><p>Freeze the protocol before collecting new, genuinely post-release outcomes; retain enough origins for power; and test any proposed trading rule separately with realistic costs and execution.</p></article>
</div></details>
<h2>Limits that shape the conclusion</h2>
<ul class="limitations">{limitations}</ul>
<details class="story-lengths diagnostics"><summary>Optional diagnostics · horizon and forecast-shape charts</summary>
<p class="chart-guide">Open these only to inspect what the summary can hide: forecast paths show selected examples, horizon curves reveal where errors change with lead, and skill charts show which baseline drives the difference. Calibration plots assess marginal hourly intervals; they do not validate cumulative-return uncertainty.</p>
<nav class="section-nav" aria-label="Jump to chart section">{"".join(section_links)}</nav>
<div class="cards">
<div class="card"><strong>Run</strong><span>{html.escape(metadata['run_id'])}</span></div>
<div class="card"><strong>Snapshot</strong><span>{html.escape(snapshot['id'])} · {snapshot['rows']:,} bars<br>{html.escape(snapshot['source_table'])} · {html.escape(', '.join(snapshot['symbols']))}</span></div>
<div class="card"><strong>Origins</strong><span>{origin_count:,} segment/symbol/mode origins</span></div>
<div class="card"><strong>Protocol</strong><span>{html.escape(protocol['version'])}<br>SHA-256 {html.escape(protocol['sha256'])}</span></div>
{f'<div class="card"><strong>Inference</strong><span>Exploratory · {html.escape(analysis["analysis_id"])}<br>{analysis["multiplicity"]["family_size"]} tests, Holm corrected</span></div>' if analysis else ''}
</div>
{''.join(report_sections)}
<p class="chart-guide">The paired interval chart below gives the per-comparison view behind the Holm-adjusted summary. Negative differences favor TimesFM; positive differences favor the baseline. The accompanying table above shows selected endpoints and adjusted p-values.</p>
</details>
<h2>Run details</h2>
<details class="method"><summary>Data, model, and reproducibility metadata</summary>
<p>Snapshot SHA-256: <code>{html.escape(snapshot['sha256'])}</code></p>
<p>Checkpoint: <code>{html.escape(model['checkpoint'])}</code>, revision <code>{html.escape(model['revision'])}</code>, package {html.escape(model['package_version'])}. Device: {html.escape(str(metadata['device']))}; PyTorch {html.escape(str(metadata['torch_version']))}.</p>
<p>Protocol SHA-256: <code>{html.escape(protocol['sha256'])}</code>. Model and evaluator source hashes are stored in the run metadata. This viewer reads saved forecast artifacts and works offline.</p>
</details>
<footer>Generated from persisted forecast and score artifacts at {html.escape(metadata['created_at'])}. This file is self-contained and can be opened offline.</footer>
</main></body></html>"""


def write_report(run_dir: str | Path, output_path: str | Path | None = None) -> Path:
    root = Path(run_dir).resolve()
    destination = Path(output_path) if output_path is not None else root / "report.html"
    destination.write_text(render_report(root), encoding="utf-8")
    return destination
