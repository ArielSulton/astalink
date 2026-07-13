"""Renders the allocation donut chart as a PNG, for WhatsApp image messages.

Mirrors frontend/components/allocation-chart.tsx's donut (weights as
segments, remaining cash_buffer as the unfilled portion) with the same
green brand palette, since WhatsApp has no equivalent of that interactive
web component — this is the static-image stand-in."""
from __future__ import annotations

from io import BytesIO

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — no display, just PNG bytes
import matplotlib.pyplot as plt

_BG = "#0a0a0a"
_FG = "#fafafa"
_CASH_COLOR = "#404040"
_PALETTE = ["#22c55e", "#86efac", "#16a34a", "#4ade80", "#15803d", "#bbf7d0", "#166534"]


def render_allocation_chart(weights: list[dict], cash_buffer: float = 0.0) -> bytes:
    """weights: [{"ticker": "BBCA", "weight": 0.5}, ...] (fractions, not %).
    cash_buffer: remaining unallocated fraction (0..1). Returns PNG bytes."""
    labels = [w["ticker"].replace(".JK", "") for w in weights]
    sizes = [max(0.0, float(w["weight"])) for w in weights]
    colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(weights))]

    if cash_buffer > 0:
        labels.append("Cash")
        sizes.append(cash_buffer)
        colors.append(_CASH_COLOR)

    fig, ax = plt.subplots(figsize=(5, 5), dpi=150)
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)

    _, _, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, autopct="%1.0f%%",
        pctdistance=0.8, startangle=90,
        wedgeprops={"width": 0.4, "edgecolor": _BG, "linewidth": 2},
        textprops={"color": _FG, "fontsize": 12},
    )
    for at in autotexts:
        at.set_color(_BG)
        at.set_fontsize(10)
        at.set_fontweight("bold")
    ax.set_title("Alokasi Portofolio", color=_FG, fontsize=14, fontweight="bold", pad=18)

    buf = BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()
