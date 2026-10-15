"""Normalizes raw source data to plain text for
`aurora_forecaster.multimodal.tokenize_text_context`.

GDELT, Alpha Vantage, and Currents return differently-shaped news JSON
(`data/text_gdelt.py`/`text_alphavantage.py`/`text_currents.py` return the
raw response, not normalized text); funding/dxy/spy are numeric covariates
rendered into human-readable snippets instead of extracted from an article
list (Aurora has no multivariate numeric input -- confirmed 2026-08-08 via
`ts_generation_mixin.py`'s hard 2-D `[batch, seq_len]` shape check -- so
these enter through this same text-context path). This module is the one
place that knows all six raw shapes and reduces each to a flat `list[str]`,
then joins snippets into the single string a multimodal forecast call needs.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Literal

TextSource = Literal["gdelt", "alphavantage", "currents", "funding", "dxy", "spy"]

# Subset of TextSource usable as a real-image covariate instead of text:
# GDELT/Alpha Vantage/Currents are inherently textual, no natural single-
# series chart representation the way a numeric covariate has.
VisionSource = Literal["funding", "dxy", "spy"]

DEFAULT_FALLBACK_TEXT = "No text context available for this origin."


def _titles(articles: list[dict], key: str = "title") -> list[str]:
    return [a[key] for a in articles if a.get(key)]


def extract_gdelt_snippets(raw: dict) -> list[str]:
    return _titles(raw.get("articles", []))


def extract_alphavantage_snippets(raw: dict) -> list[str]:
    return _titles(raw.get("feed", []))


def extract_currents_snippets(raw: dict) -> list[str]:
    return _titles(raw.get("news", []))


def extract_funding_snippet(raw: dict) -> list[str]:
    pct = raw["funding_rate"] * 100
    sign = "+" if pct >= 0 else ""
    return [f"BTC perp funding rate (Hyperliquid): {sign}{pct:.4f}%"]


def _render_index_snippet(label: str, raw: dict) -> str:
    pct = raw["pct_change"] * 100
    sign = "+" if pct >= 0 else ""
    return f"{label}: {raw['close']:.2f} (Δ over lookback: {sign}{pct:.1f}%)"


def extract_dxy_snippet(raw: dict) -> list[str]:
    return [_render_index_snippet("DXY", raw)]


def extract_spy_snippet(raw: dict) -> list[str]:
    return [_render_index_snippet("S&P 500 (SPY)", raw)]


SOURCE_EXTRACTORS: dict[TextSource, Callable[[dict], list[str]]] = {
    "gdelt": extract_gdelt_snippets,
    "alphavantage": extract_alphavantage_snippets,
    "currents": extract_currents_snippets,
    "funding": extract_funding_snippet,
    "dxy": extract_dxy_snippet,
    "spy": extract_spy_snippet,
}


def normalize_source_text(source: TextSource, raw: dict) -> list[str]:
    """Dispatches to the extractor for `source`. Raises `KeyError` on an
    unknown source rather than silently dropping text."""
    return SOURCE_EXTRACTORS[source](raw)


def join_snippets(
    snippets: Sequence[str],
    fallback: str = DEFAULT_FALLBACK_TEXT,
    max_snippets: int | None = None,
) -> str:
    """Space-joins non-empty stripped snippets, optionally capped to the
    first `max_snippets`. Returns `fallback` if nothing remains -- mirrors
    `scripts/multimodal_smoke_test.py`'s existing FALLBACK_TEXT pattern so a
    quiet news day never sends an empty string into `tokenize_text_context`.
    """
    cleaned = [s.strip() for s in snippets if s.strip()]
    if max_snippets is not None:
        cleaned = cleaned[:max_snippets]
    if not cleaned:
        return fallback
    return " ".join(cleaned)
