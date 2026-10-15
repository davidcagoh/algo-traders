import pytest

from aurora_forecaster.vision import render_line_chart


def test_render_line_chart_returns_correct_size():
    image = render_line_chart([1.0, 2.0, 3.0, 2.0, 1.5], width=400, height=200)

    assert image.size == (400, 200)


def test_render_line_chart_is_not_blank():
    image = render_line_chart([1.0, 5.0, 1.0, 5.0, 1.0], width=100, height=100)

    colors = image.convert("RGB").getcolors(maxcolors=100 * 100)
    assert len(colors) > 1  # more than just the background color


def test_render_line_chart_rejects_too_few_values():
    with pytest.raises(ValueError):
        render_line_chart([1.0])
