"""Real-image covariate encoding for Aurora's `vision_inputs` path -- an
alternative to rendering a covariate as text (`text_adapter.py`), to test
whether image-encoding vs. text-encoding of the same information changes
forecast quality.

Distinct from Aurora's own always-on "pseudo" vision (auto-derived from the
primary time series when no real image is given, `AuroraModel.forward`) --
that path is architecturally separate and already active on every call this
project makes, real or not.

No plotting library (matplotlib/plotly) is installed in this project's
venv -- `render_line_chart` hand-draws a simple line chart with Pillow's
`ImageDraw` rather than adding one for a single chart type.

Real images are passed to `generate(vision_inputs=[image])` as raw PIL
Images, NOT preprocessed -- confirmed 2026-08-08 (the hard way, via a real
traceback): Aurora's own `VisionEncoder`/`UnifiedImageProcessor.
process_real_image` runs its own internal `ViTImageProcessor` pass
(`modality_connector.py`), so pre-normalizing here double-processes the
image and crashes (`ValueError: ... values outside the range [0, 1], got
[-1.0, 1.0]`). This mirrors the model's own `type='pseudo'` path, which
also expects a raw (un-normalized) tensor for the same reason.
"""

from __future__ import annotations

from collections.abc import Sequence

from PIL import Image, ImageDraw


def render_line_chart(values: Sequence[float], width: int = 400, height: int = 200) -> Image.Image:
    """White-background line chart of `values` (index on x, min-max scaled
    on y). Fed to a ViT, not for human aesthetics -- axis lines + a polyline
    is enough. Raises `ValueError` if fewer than 2 values (can't draw a
    line from one point)."""
    if len(values) < 2:
        raise ValueError(f"need at least 2 values to draw a line, got {len(values)}")

    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)

    margin = 10
    plot_w = width - 2 * margin
    plot_h = height - 2 * margin
    draw.line([(margin, height - margin), (width - margin, height - margin)], fill="black")
    draw.line([(margin, margin), (margin, height - margin)], fill="black")

    lo, hi = min(values), max(values)
    span = hi - lo or 1.0
    n = len(values)
    points = [
        (
            margin + plot_w * i / (n - 1),
            margin + plot_h * (1 - (v - lo) / span),
        )
        for i, v in enumerate(values)
    ]
    draw.line(points, fill="blue", width=2)

    return image
