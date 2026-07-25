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


_COMPOSITION_COLORS = {
    "cash": "#a1a1aa",     # neutral grey — matches the dashboard's Kas segment
    "stocks": "#22c55e",   # chart-2 green — matches Saham
    "business": "#15803d", # deeper green — matches Bisnis
}


_BAND_LABELS = {
    "strong_buy": "Strong Buy",
    "buy": "Buy",
    "watchlist": "Watchlist",
    "avoid": "Hindari",
    "reject": "Tolak",
    "no_verdict": "Data Kurang",
}


def _fmt_rp(value: float) -> str:
    return f"Rp {value:,.0f}".replace(",", ".")


def render_report_table_chart(
    verdicts: dict[str, dict], weights: list[dict], plan_cash: float | None = None,
) -> bytes:
    """Renders the Layer 1 verdict table and optimizer weight table as one
    PNG — mirrors report.py's markdown tables (_layer1_section/_plan_section)
    since WhatsApp has no markdown table renderer. Either argument may be
    empty; the corresponding table is simply omitted, but at least one must
    be non-empty for a meaningful image.

    plan_cash (allocation_plan.cash) is the actual rupiah amount the weights
    were computed against — which is Layer 0's stock-sleeve slice, not the
    user's total funds. Without surfacing it, "BBCA 95%" reads as 95% of
    everything the user owns instead of 95% of just the stock slice."""
    tickers = list(verdicts.keys())
    if not tickers and not weights:
        raise ValueError("render_report_table_chart: verdicts and weights both empty")
    n_verdict_rows = len(tickers) + 1
    n_weight_rows = len(weights) + 1
    n_tables = int(bool(tickers)) + int(bool(weights))
    height = 0.9 * (n_verdict_rows if tickers else 0) + 0.9 * (n_weight_rows if weights else 0) + 1.2

    fig, axes = plt.subplots(
        n_tables, 1, figsize=(6.5, max(height, 2.5)), dpi=150,
        squeeze=False,
    )
    fig.patch.set_facecolor(_BG)
    ax_iter = iter(axes[:, 0])

    if tickers:
        ax = next(ax_iter)
        ax.set_facecolor(_BG)
        ax.axis("off")
        ax.set_title("Verdik per Saham (Layer 1)", color=_FG, fontsize=12, fontweight="bold", loc="left")
        rows = [
            [t, _BAND_LABELS.get(str(v.get("band", "")), str(v.get("band", "-"))),
             f"{float(v.get('score', 0)):.0f}", str(v.get("gate_status", "-")).upper()]
            for t, v in verdicts.items()
        ]
        table = ax.table(
            cellText=rows, colLabels=["Ticker", "Band", "Skor", "Gate"],
            loc="center", cellLoc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 1.6)
        for (row, _col), cell in table.get_celld().items():
            cell.set_edgecolor("#333333")
            cell.set_facecolor("#1a1a1a" if row else "#262626")
            cell.set_text_props(color=_FG)

    if weights:
        ax = next(ax_iter)
        ax.set_facecolor(_BG)
        ax.axis("off")
        title = "Bobot Saham (Optimizer)"
        if plan_cash is not None:
            title += f" — Dana dianalisis: {_fmt_rp(plan_cash)}"
        ax.set_title(title, color=_FG, fontsize=11, fontweight="bold", loc="left")
        rows = [[w.get("ticker", "?"), f"{float(w.get('weight', 0)):.0%}"] for w in weights]
        table = ax.table(
            cellText=rows, colLabels=["Ticker", "Bobot"],
            loc="center", cellLoc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 1.6)
        for (row, _col), cell in table.get_celld().items():
            cell.set_edgecolor("#333333")
            cell.set_facecolor("#1a1a1a" if row else "#262626")
            cell.set_text_props(color=_FG)

    buf = BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def render_composition_chart(cash: float, stocks: float, business: float) -> bytes:
    """Layer 0's cash/stocks/business split as a donut, sent alongside the
    composition-gate pause message on WhatsApp (ALLOCATE_CAPITAL only) so
    the user can see the split before replying ya/tidak. fractions 0..1."""
    labels = ["Kas", "Saham", "Bisnis"]
    sizes = [max(0.0, cash), max(0.0, stocks), max(0.0, business)]
    colors = [_COMPOSITION_COLORS["cash"], _COMPOSITION_COLORS["stocks"], _COMPOSITION_COLORS["business"]]

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
    ax.set_title("Kas vs Saham vs Bisnis", color=_FG, fontsize=14, fontweight="bold", pad=18)

    buf = BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()
