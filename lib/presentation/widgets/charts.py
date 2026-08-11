"""Matplotlib charts rendered as Flet Image controls — clear & readable."""

from __future__ import annotations

import base64
import io
from decimal import Decimal
from typing import Sequence

import flet as ft
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, MaxNLocator


def _fig_to_image(fig: plt.Figure, *, width: int = 360, height: int = 260) -> ft.Image:
    """Serialize a matplotlib figure to an in-memory PNG ``ft.Image``."""
    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=150,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
        transparent=True,
        pad_inches=0.15,
    )
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("ascii")
    return ft.Image(
        src=f"data:image/png;base64,{b64}",
        width=width,
        height=height,
        fit=ft.BoxFit.CONTAIN,
        border_radius=12,
        expand=True,
    )


def _money_formatter(value: float, _pos: int) -> str:
    """Human-readable axis labels (1.2K / 1.5M)."""
    abs_v = abs(value)
    if abs_v >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs_v >= 1_000:
        return f"{value / 1_000:.1f}K"
    if abs_v >= 10:
        return f"{value:.0f}"
    return f"{value:.1f}"


def build_pie_chart_image(
    labels: Sequence[str],
    values: Sequence[Decimal | float | int],
    *,
    title: str = "",
    width: int = 360,
    height: int = 280,
    dark: bool = True,
    language: str = "ru",
) -> ft.Image:
    """Donut chart with legend under the plot (fits narrow screens)."""
    from lib.infrastructure.services.localization import t

    nums = [float(v) for v in values]
    text = "#E2E8F0" if dark else "#0F172A"
    muted = "#94A3B8" if dark else "#475569"
    edge = "#0B1220" if dark else "#FFFFFF"

    fig_w = max(width / 100, 3.2)
    fig_h = max(height / 100, 2.8)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    if not nums or sum(nums) <= 0:
        ax.text(
            0.5,
            0.55,
            t("chart.no_expenses", language),
            ha="center",
            va="center",
            color=text,
            fontsize=12,
        )
        ax.text(
            0.5,
            0.38,
            t("chart.add_month_ops", language),
            ha="center",
            va="center",
            color=muted,
            fontsize=9,
        )
        ax.axis("off")
        fig.patch.set_alpha(0)
        return _fig_to_image(fig, width=width, height=height)

    colors = [
        "#2DD4BF",
        "#38BDF8",
        "#4ADE80",
        "#FBBF24",
        "#F87171",
        "#A78BFA",
        "#FB7185",
        "#34D399",
    ]
    total = sum(nums)
    wedges, _, autotexts = ax.pie(
        nums,
        labels=None,
        autopct=lambda pct: f"{pct:.0f}%" if pct >= 8 else "",
        startangle=90,
        colors=colors[: len(nums)],
        pctdistance=0.72,
        wedgeprops={
            "linewidth": 2,
            "edgecolor": edge,
            "width": 0.42,  # donut
        },
    )
    for item in autotexts:
        item.set_color(text)
        item.set_fontsize(9)
        item.set_fontweight("700")

    # Center label
    ax.text(
        0,
        0.06,
        t("chart.total", language),
        ha="center",
        va="center",
        color=muted,
        fontsize=8,
    )
    ax.text(
        0,
        -0.12,
        _money_formatter(total, 0),
        ha="center",
        va="center",
        color=text,
        fontsize=11,
        fontweight="700",
    )

    legend_labels = []
    for label, amount in zip(labels, nums):
        share = amount / total * 100 if total else 0
        legend_labels.append(f"{label}  ·  {share:.0f}%")

    ax.legend(
        wedges,
        legend_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=1 if len(labels) <= 4 else 2,
        fontsize=8,
        frameon=False,
        labelcolor=text,
        handlelength=1.0,
        columnspacing=1.0,
    )
    if title:
        ax.set_title(title, fontsize=11, pad=6, color=text, fontweight="600")
    ax.axis("equal")
    fig.patch.set_alpha(0)
    fig.tight_layout()
    return _fig_to_image(fig, width=width, height=height)


def build_line_chart_image(
    periods: Sequence[str],
    income: Sequence[Decimal | float | int],
    expense: Sequence[Decimal | float | int],
    *,
    title: str = "",
    width: int = 360,
    height: int = 260,
    dark: bool = True,
    language: str = "ru",
) -> ft.Image:
    """Clear income vs expense trend for mobile width."""
    from lib.infrastructure.services.localization import t

    text = "#E2E8F0" if dark else "#0F172A"
    muted = "#94A3B8" if dark else "#475569"
    grid = "#33415566" if dark else "#CBD5E1"

    fig_w = max(width / 100, 3.2)
    fig_h = max(height / 100, 2.6)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    if not periods:
        ax.text(
            0.5,
            0.55,
            t("chart.no_data", language),
            ha="center",
            va="center",
            color=text,
            fontsize=12,
        )
        ax.text(
            0.5,
            0.38,
            t("chart.dynamics_empty", language),
            ha="center",
            va="center",
            color=muted,
            fontsize=9,
        )
        ax.axis("off")
        fig.patch.set_alpha(0)
        return _fig_to_image(fig, width=width, height=height)

    x = list(range(len(periods)))
    inc = [float(v) for v in income]
    exp = [float(v) for v in expense]
    income_color = "#4ADE80" if dark else "#15803D"
    expense_color = "#F87171" if dark else "#B91C1C"

    ax.plot(
        x,
        inc,
        color=income_color,
        marker="o",
        markersize=4,
        label=t("transaction.income", language),
        linewidth=2.2,
    )
    ax.plot(
        x,
        exp,
        color=expense_color,
        marker="o",
        markersize=4,
        label=t("transaction.expense", language),
        linewidth=2.2,
    )
    ax.fill_between(x, inc, alpha=0.10, color=income_color)
    ax.fill_between(x, exp, alpha=0.10, color=expense_color)

    # Show at most ~6 x labels to stay readable.
    step = max(1, len(periods) // 5)
    ticks = list(range(0, len(periods), step))
    if ticks[-1] != len(periods) - 1:
        ticks.append(len(periods) - 1)
    ax.set_xticks(ticks)
    ax.set_xticklabels([periods[i] for i in ticks], rotation=0, fontsize=8, color=muted)

    ax.yaxis.set_major_formatter(FuncFormatter(_money_formatter))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
    ax.tick_params(axis="y", labelsize=8, colors=muted)
    ax.legend(
        fontsize=9,
        frameon=False,
        labelcolor=text,
        loc="upper left",
        ncols=2,
    )
    ax.grid(True, axis="y", linestyle="--", alpha=0.35, color=grid)
    ax.set_facecolor("none")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(muted)
    ax.spines["bottom"].set_color(muted)
    if title:
        ax.set_title(title, fontsize=11, pad=8, color=text, fontweight="600")
    fig.patch.set_alpha(0)
    fig.tight_layout()
    return _fig_to_image(fig, width=width, height=height)
