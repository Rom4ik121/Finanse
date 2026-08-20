"""Charts for dashboard — matplotlib on desktop, native Flet widgets on mobile."""

from __future__ import annotations

import base64
import io
import os
import sys
import tempfile
from decimal import Decimal
from typing import Sequence, Tuple, Type

import flet as ft

_plt = None
_FuncFormatter = None
_MaxNLocator = None
_MPL_AVAILABLE: bool | None = None

_CHART_COLORS = [
    "#2DD4BF",
    "#38BDF8",
    "#4ADE80",
    "#FBBF24",
    "#F87171",
    "#A78BFA",
    "#FB7185",
    "#34D399",
]


def _prefer_native_charts() -> bool:
    """Android/iOS builds bundle Python but matplotlib often fails at runtime."""
    if sys.platform.startswith(("android", "ios")):
        return True
    # Flet mobile host sets one of these in packaged apps.
    return bool(os.environ.get("FLET_PLATFORM")) and os.environ.get(
        "FLET_PLATFORM", ""
    ).lower() in {"android", "ios"}


def _configure_matplotlib_env() -> None:
    """Use a writable config dir (Android has no ~/.matplotlib)."""
    config_dir = os.path.join(tempfile.gettempdir(), "finanse_matplotlib")
    os.makedirs(config_dir, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", config_dir)
    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ.setdefault("MATPLOTLIBRC", os.path.join(config_dir, "matplotlibrc"))
    rc_path = os.environ["MATPLOTLIBRC"]
    if not os.path.exists(rc_path):
        with open(rc_path, "w", encoding="utf-8") as fh:
            fh.write("backend: Agg\n")


def _load_matplotlib() -> Tuple[object, Type, Type] | None:
    """Import matplotlib lazily; return (pyplot, FuncFormatter, MaxNLocator) or None."""
    global _plt, _FuncFormatter, _MaxNLocator, _MPL_AVAILABLE
    if _prefer_native_charts():
        _MPL_AVAILABLE = False
        return None
    if _MPL_AVAILABLE is False:
        return None
    if _plt is not None and _FuncFormatter is not None and _MaxNLocator is not None:
        return _plt, _FuncFormatter, _MaxNLocator
    try:
        _configure_matplotlib_env()
        import matplotlib

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt
        from matplotlib.ticker import FuncFormatter, MaxNLocator

        _plt = plt
        _FuncFormatter = FuncFormatter
        _MaxNLocator = MaxNLocator
        _MPL_AVAILABLE = True
        return plt, FuncFormatter, MaxNLocator
    except Exception:  # noqa: BLE001
        _MPL_AVAILABLE = False
        return None


def _money_formatter(value: float, _pos: int = 0) -> str:
    """Human-readable axis labels (1.2K / 1.5M)."""
    abs_v = abs(value)
    if abs_v >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs_v >= 1_000:
        return f"{value / 1_000:.1f}K"
    if abs_v >= 10:
        return f"{value:.0f}"
    return f"{value:.1f}"


def _empty_chart(message: str, hint: str, *, width: int, height: int) -> ft.Container:
    return ft.Container(
        width=width,
        height=height,
        border_radius=12,
        alignment=ft.Alignment.CENTER,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
        content=ft.Column(
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
            controls=[
                ft.Icon(ft.Icons.INSERT_CHART_OUTLINED, size=28, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(message, size=12, color=ft.Colors.ON_SURFACE, text_align=ft.TextAlign.CENTER),
                ft.Text(hint, size=10, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
            ],
        ),
    )


def _native_pie_chart(
    labels: Sequence[str],
    values: Sequence[Decimal | float | int],
    *,
    width: int,
    height: int,
    language: str,
    show_legend: bool = True,
) -> ft.Control:
    """Stacked bar + share labels — works without matplotlib on mobile."""
    from lib.infrastructure.services.localization import t

    nums = [float(v) for v in values]
    if not nums or sum(nums) <= 0:
        return _empty_chart(
            t("chart.no_expenses", language),
            t("chart.add_month_ops", language),
            width=width,
            height=height,
        )

    total = sum(nums)
    inner_w = max(width - 24, 120)
    segments: list[ft.Control] = []
    legend: list[ft.Control] = []
    for idx, (label, amount) in enumerate(zip(labels, nums)):
        color = _CHART_COLORS[idx % len(_CHART_COLORS)]
        share = amount / total * 100 if total else 0
        seg_w = max(6, int(inner_w * amount / total))
        segments.append(
            ft.Container(
                width=seg_w,
                height=26,
                bgcolor=color,
                border_radius=ft.BorderRadius.only(
                    top_left=12 if idx == 0 else 0,
                    bottom_left=12 if idx == 0 else 0,
                    top_right=12 if idx == len(nums) - 1 else 0,
                    bottom_right=12 if idx == len(nums) - 1 else 0,
                ),
                tooltip=f"{label}: {share:.0f}%",
            )
        )
        legend.append(
            ft.Row(
                spacing=6,
                controls=[
                    ft.Container(width=8, height=8, border_radius=4, bgcolor=color),
                    ft.Text(
                        f"{label} · {share:.0f}%",
                        size=10,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        expand=True,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=1,
                    ),
                ],
            )
        )

    return ft.Container(
        width=width,
        height=height,
        content=ft.Column(
            tight=True,
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    t("chart.total", language),
                    size=11,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.Text(
                    _money_formatter(total),
                    size=16,
                    weight=ft.FontWeight.W_700,
                    color=ft.Colors.ON_SURFACE,
                ),
                ft.Row(spacing=0, alignment=ft.MainAxisAlignment.CENTER, controls=segments),
                *(
                    [ft.Column(spacing=4, tight=True, controls=legend[:4])]
                    if show_legend
                    else []
                ),
            ],
        ),
    )


def _native_line_chart(
    periods: Sequence[str],
    income: Sequence[Decimal | float | int],
    expense: Sequence[Decimal | float | int],
    *,
    width: int,
    height: int,
    language: str,
) -> ft.Control:
    """Grouped bars per day — mobile-friendly fallback."""
    from lib.infrastructure.services.localization import t

    if not periods:
        return _empty_chart(
            t("chart.no_data", language),
            t("chart.dynamics_empty", language),
            width=width,
            height=height,
        )

    inc = [float(v) for v in income]
    exp = [float(v) for v in expense]
    max_val = max([1.0, *inc, *exp])
    plot_h = max(height - 72, 80)
    income_color = ft.Colors.SECONDARY
    expense_color = ft.Colors.ERROR

    bars: list[ft.Control] = []
    for idx, period in enumerate(periods):
        inc_h = max(2, int(inc[idx] / max_val * plot_h))
        exp_h = max(2, int(exp[idx] / max_val * plot_h))
        bars.append(
            ft.Column(
                tight=True,
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=3,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                        controls=[
                            ft.Container(
                                width=7,
                                height=inc_h,
                                bgcolor=income_color,
                                border_radius=4,
                                tooltip=t("transaction.income", language),
                            ),
                            ft.Container(
                                width=7,
                                height=exp_h,
                                bgcolor=expense_color,
                                border_radius=4,
                                tooltip=t("transaction.expense", language),
                            ),
                        ],
                    ),
                    ft.Text(
                        period,
                        size=8,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        text_align=ft.TextAlign.CENTER,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
            )
        )

    return ft.Container(
        width=width,
        height=height,
        content=ft.Column(
            tight=True,
            spacing=8,
            controls=[
                ft.Row(
                    spacing=12,
                    controls=[
                        ft.Row(
                            spacing=4,
                            controls=[
                                ft.Container(width=8, height=8, border_radius=4, bgcolor=income_color),
                                ft.Text(t("transaction.income", language), size=10, color=ft.Colors.ON_SURFACE_VARIANT),
                            ],
                        ),
                        ft.Row(
                            spacing=4,
                            controls=[
                                ft.Container(width=8, height=8, border_radius=4, bgcolor=expense_color),
                                ft.Text(t("transaction.expense", language), size=10, color=ft.Colors.ON_SURFACE_VARIANT),
                            ],
                        ),
                    ],
                ),
                ft.Container(
                    height=plot_h + 18,
                    alignment=ft.Alignment(0, 1),
                    content=ft.Row(
                        spacing=6,
                        scroll=ft.ScrollMode.AUTO,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                        controls=bars,
                    ),
                ),
            ],
        ),
    )


def _fig_to_image(fig, *, width: int = 360, height: int = 260) -> ft.Image:
    """Serialize a matplotlib figure to an in-memory PNG ``ft.Image``."""
    plt = _plt
    assert plt is not None
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


def build_pie_chart_image(
    labels: Sequence[str],
    values: Sequence[Decimal | float | int],
    *,
    title: str = "",
    width: int = 360,
    height: int = 280,
    dark: bool = True,
    language: str = "ru",
    show_legend: bool = True,
) -> ft.Control:
    """Donut chart (desktop) or stacked bar (mobile)."""
    mpl = _load_matplotlib()
    if mpl is not None:
        try:
            return _build_pie_chart_mpl(
                mpl,
                labels,
                values,
                title=title,
                width=width,
                height=height,
                dark=dark,
                language=language,
                show_legend=show_legend,
            )
        except Exception:  # noqa: BLE001
            pass
    return _native_pie_chart(
        labels,
        values,
        width=width,
        height=height,
        language=language,
        show_legend=show_legend,
    )


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
) -> ft.Control:
    """Line chart (desktop) or grouped bars (mobile)."""
    mpl = _load_matplotlib()
    if mpl is not None:
        try:
            return _build_line_chart_mpl(
                mpl,
                periods,
                income,
                expense,
                title=title,
                width=width,
                height=height,
                dark=dark,
                language=language,
            )
        except Exception:  # noqa: BLE001
            pass
    return _native_line_chart(
        periods,
        income,
        expense,
        width=width,
        height=height,
        language=language,
    )


def _build_pie_chart_mpl(
    mpl: Tuple[object, Type, Type],
    labels: Sequence[str],
    values: Sequence[Decimal | float | int],
    *,
    title: str,
    width: int,
    height: int,
    dark: bool,
    language: str,
    show_legend: bool = True,
) -> ft.Control:
    from lib.infrastructure.services.localization import t

    plt, _, _ = mpl
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

    total = sum(nums)
    wedges, _, autotexts = ax.pie(
        nums,
        labels=None,
        autopct=lambda pct: f"{pct:.0f}%" if pct >= 8 else "",
        startangle=90,
        colors=_CHART_COLORS[: len(nums)],
        pctdistance=0.72,
        wedgeprops={"linewidth": 2, "edgecolor": edge, "width": 0.42},
    )
    for item in autotexts:
        item.set_color(text)
        item.set_fontsize(9)
        item.set_fontweight("700")

    ax.text(0, 0.06, t("chart.total", language), ha="center", va="center", color=muted, fontsize=8)
    ax.text(
        0,
        -0.12,
        _money_formatter(total),
        ha="center",
        va="center",
        color=text,
        fontsize=11,
        fontweight="700",
    )

    legend_labels = [
        f"{label}  ·  {amount / total * 100:.0f}%"
        for label, amount in zip(labels, nums)
    ]
    if show_legend:
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
        fig.tight_layout()
    else:
        fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
    if title:
        ax.set_title(title, fontsize=11, pad=6, color=text, fontweight="600")
    ax.axis("equal")
    fig.patch.set_alpha(0)
    return _fig_to_image(fig, width=width, height=height)


def _build_line_chart_mpl(
    mpl: Tuple[object, Type, Type],
    periods: Sequence[str],
    income: Sequence[Decimal | float | int],
    expense: Sequence[Decimal | float | int],
    *,
    title: str,
    width: int,
    height: int,
    dark: bool,
    language: str,
) -> ft.Control:
    from lib.infrastructure.services.localization import t

    plt, FuncFormatter, MaxNLocator = mpl
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
