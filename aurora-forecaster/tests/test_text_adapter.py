import pytest

from aurora_forecaster.text_adapter import (
    DEFAULT_FALLBACK_TEXT,
    extract_alphavantage_snippets,
    extract_currents_snippets,
    extract_dxy_snippet,
    extract_funding_snippet,
    extract_gdelt_snippets,
    extract_spy_snippet,
    join_snippets,
    normalize_source_text,
)


def test_extract_gdelt_snippets_well_formed():
    raw = {"articles": [{"title": "BTC rallies"}, {"title": "ETH dips"}]}

    assert extract_gdelt_snippets(raw) == ["BTC rallies", "ETH dips"]


def test_extract_gdelt_snippets_skips_missing_or_empty_titles():
    raw = {"articles": [{"title": "BTC rallies"}, {"title": ""}, {}, {"title": "ETH dips"}]}

    assert extract_gdelt_snippets(raw) == ["BTC rallies", "ETH dips"]


def test_extract_alphavantage_snippets_well_formed():
    raw = {"feed": [{"title": "BTC ETF inflows slow"}, {"title": "Bitcoin miners sell"}]}

    assert extract_alphavantage_snippets(raw) == ["BTC ETF inflows slow", "Bitcoin miners sell"]


def test_extract_alphavantage_snippets_skips_missing_or_empty_titles():
    raw = {"feed": [{"title": "BTC ETF inflows slow"}, {"title": ""}, {}]}

    assert extract_alphavantage_snippets(raw) == ["BTC ETF inflows slow"]


def test_extract_currents_snippets_well_formed():
    raw = {"news": [{"title": "Bitcoin surges past resistance"}, {"title": "SPY flat"}]}

    assert extract_currents_snippets(raw) == ["Bitcoin surges past resistance", "SPY flat"]


def test_extract_currents_snippets_skips_missing_or_empty_titles():
    raw = {"news": [{"title": "Bitcoin surges past resistance"}, {"title": ""}, {}]}

    assert extract_currents_snippets(raw) == ["Bitcoin surges past resistance"]


def test_extract_funding_snippet_renders_positive_rate():
    raw = {"coin": "BTC", "funding_rate": 0.00012, "time": 100}

    assert extract_funding_snippet(raw) == ["BTC perp funding rate (Hyperliquid): +0.0120%"]


def test_extract_funding_snippet_renders_negative_rate():
    raw = {"coin": "BTC", "funding_rate": -0.00034, "time": 100}

    assert extract_funding_snippet(raw) == ["BTC perp funding rate (Hyperliquid): -0.0340%"]


def test_extract_dxy_snippet_renders_close_and_pct_change():
    raw = {"close": 103.42, "pct_change": -0.003}

    assert extract_dxy_snippet(raw) == ["DXY: 103.42 (Δ over lookback: -0.3%)"]


def test_extract_spy_snippet_renders_close_and_pct_change():
    raw = {"close": 542.1, "pct_change": 0.011}

    assert extract_spy_snippet(raw) == ["S&P 500 (SPY): 542.10 (Δ over lookback: +1.1%)"]


def test_normalize_source_text_dispatches_by_source():
    gdelt_raw = {"articles": [{"title": "BTC rallies"}]}
    av_raw = {"feed": [{"title": "BTC ETF inflows slow"}]}
    currents_raw = {"news": [{"title": "Bitcoin surges"}]}
    funding_raw = {"coin": "BTC", "funding_rate": 0.0001, "time": 100}
    dxy_raw = {"close": 100.0, "pct_change": 0.0}
    spy_raw = {"close": 500.0, "pct_change": 0.0}

    assert normalize_source_text("gdelt", gdelt_raw) == ["BTC rallies"]
    assert normalize_source_text("alphavantage", av_raw) == ["BTC ETF inflows slow"]
    assert normalize_source_text("currents", currents_raw) == ["Bitcoin surges"]
    assert normalize_source_text("funding", funding_raw) == extract_funding_snippet(funding_raw)
    assert normalize_source_text("dxy", dxy_raw) == extract_dxy_snippet(dxy_raw)
    assert normalize_source_text("spy", spy_raw) == extract_spy_snippet(spy_raw)


def test_normalize_source_text_rejects_unknown_source():
    with pytest.raises(KeyError):
        normalize_source_text("guardian", {})


def test_join_snippets_joins_with_spaces():
    assert join_snippets(["BTC rallies", "ETH dips"]) == "BTC rallies ETH dips"


def test_join_snippets_strips_and_drops_whitespace_only_entries():
    assert join_snippets(["  BTC rallies  ", "   ", "ETH dips"]) == "BTC rallies ETH dips"


def test_join_snippets_falls_back_on_empty_input():
    assert join_snippets([]) == DEFAULT_FALLBACK_TEXT
    assert join_snippets(["   ", ""]) == DEFAULT_FALLBACK_TEXT


def test_join_snippets_respects_custom_fallback():
    assert join_snippets([], fallback="nothing today") == "nothing today"


def test_join_snippets_max_snippets_caps_count():
    assert join_snippets(["a", "b", "c"], max_snippets=2) == "a b"
