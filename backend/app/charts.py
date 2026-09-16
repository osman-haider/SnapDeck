"""Render a small, clean bar chart from SnapDeck's {label, value} chart data.

Kept deliberately simple (one chart type, one style) — this is the
"nice to have" chart placeholder from the demo spec, not a charting library.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless rendering, no display server required
import matplotlib.pyplot as plt

BAR_COLOR = "#4F46E5"  # matches the frontend's accent color
TEXT_COLOR = "#1F2937"


def render_bar_chart(chart_data: list[dict[str, Any]], title: str = "") -> bytes:
    """Return PNG bytes for a bar chart built from chart_data."""
    if not chart_data:
        raise ValueError("No chart data was provided to render.")

    labels = [str(point["label"]) for point in chart_data]
    values = [float(point["value"]) for point in chart_data]

    fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=150)
    bars = ax.bar(labels, values, color=BAR_COLOR, width=0.6)

    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", color=TEXT_COLOR, pad=12)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.tick_params(axis="x", labelsize=10, colors=TEXT_COLOR)

    for bar, value in zip(bars, values):
        ax.annotate(
            f"{value:g}",
            (bar.get_x() + bar.get_width() / 2, bar.get_height()),
            ha="center",
            va="bottom",
            fontsize=10,
            color=TEXT_COLOR,
            fontweight="bold",
        )

    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png", facecolor="white")
    plt.close(fig)
    buffer.seek(0)
    return buffer.read()
