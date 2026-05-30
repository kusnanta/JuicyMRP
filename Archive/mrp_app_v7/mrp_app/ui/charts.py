"""ui/charts.py — Plotly chart builders."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go

PROD_COLORS = [
    "#1a56db","#0e9f6e","#e3a008","#e02424","#7c3aed",
    "#0891b2","#db2777","#65a30d","#ea580c","#9333ea",
]
PROD_COLORS_LIGHT = [
    "#bfdbfe","#bbf7d0","#fde68a","#fecaca","#ddd6fe",
    "#bae6fd","#fbcfe8","#d9f99d","#fed7aa","#f3e8ff",
]

_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="IBM Plex Sans", size=11, color="#6b7280"),
    margin=dict(l=0, r=8, t=32, b=0),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0, font=dict(size=10)),
    xaxis=dict(gridcolor="rgba(0,0,0,0.05)", showline=False, zeroline=False),
    yaxis=dict(gridcolor="rgba(0,0,0,0.05)", showline=False, zeroline=False),
)


def _c(i):  return PROD_COLORS[i % len(PROD_COLORS)]
def _cl(i): return PROD_COLORS_LIGHT[i % len(PROD_COLORS_LIGHT)]


# ── Forecast line chart ───────────────────────────────────────────────

def forecast_chart(
    df_sales:        pd.DataFrame,
    forecast_df:     pd.DataFrame,
    selected_products: list[str],
    hist_days:       int = 30,
    date_from:       date | None = None,
    date_to:         date | None = None,
    height:          int = 300,
) -> go.Figure:
    """
    Solid line = historical (last hist_days).
    Dashed line + shaded CI = forecast.
    Chart always shows full 30-day forecast; date_from/date_to only controls
    which forecast range is highlighted (via a background shade).
    """
    today    = pd.Timestamp(date.today())
    hist_s   = today - pd.Timedelta(days=hist_days)
    fc_start = pd.Timestamp(date_from) if date_from else today
    fc_end   = pd.Timestamp(date_to)   if date_to   else today + pd.Timedelta(days=29)

    fig = go.Figure()

    # Filter range highlight band
    fig.add_vrect(
        x0=fc_start, x1=fc_end,
        fillcolor="rgba(26,86,219,0.04)",
        line_width=0,
        annotation_text="Filter range",
        annotation_font_size=9,
        annotation_font_color="#9ca3af",
        annotation_position="top left",
    )

    for idx, product in enumerate(selected_products):
        c = _c(idx); cl = _cl(idx)

        # Historical
        hist = df_sales[
            (df_sales["product_name"] == product) &
            (df_sales["date"] >= hist_s) &
            (df_sales["date"] <  today)
        ].sort_values("date")
        if not hist.empty:
            fig.add_trace(go.Scatter(
                x=hist["date"], y=hist["sales_qty"], mode="lines",
                name=f"{product} — aktual",
                line=dict(color=c, width=1.8), opacity=0.85,
                legendgroup=product,
            ))

        # Full 30-day forecast
        fc = forecast_df[forecast_df["product_name"] == product].sort_values("forecast_date")
        if not fc.empty:
            xd = pd.to_datetime(fc["forecast_date"])
            xband = pd.concat([xd, xd.iloc[::-1]])
            yband = pd.concat([fc["forecast_upper"], fc["forecast_lower"].iloc[::-1]])
            fig.add_trace(go.Scatter(
                x=xband, y=yband, fill="toself",
                fillcolor=cl + "55", line=dict(color="rgba(0,0,0,0)"),
                showlegend=False, hoverinfo="skip", legendgroup=product,
            ))
            fig.add_trace(go.Scatter(
                x=xd, y=fc["forecast_qty"], mode="lines",
                name=f"{product} — forecast",
                line=dict(color=c, width=2, dash="dot"),
                legendgroup=product,
            ))

    # Today line
    fig.add_vline(
        x=today.timestamp() * 1000,
        line_dash="dot", line_color="rgba(0,0,0,0.18)", line_width=1,
        annotation_text="Hari ini", annotation_font_size=9,
        annotation_font_color="#9ca3af",
    )

    layout = dict(**_BASE, height=height, hovermode="x unified")
    layout["title"] = dict(text="Historical (30H) + Forecast 30 hari ke depan — scroll kiri untuk history lebih lama", font=dict(size=12), x=0)
    layout["xaxis"] = dict(**_BASE["xaxis"], tickformat="%d %b", type="date")
    fig.update_layout(**layout)
    return fig


# ── Accuracy bar chart (kept for backwards compat but not used on dashboard) ──

def accuracy_chart(forecast_df: pd.DataFrame, selected_products: list[str], height: int = 220) -> go.Figure:
    rows = []
    for p in selected_products:
        sub = forecast_df[forecast_df["product_name"] == p]
        if not sub.empty:
            acc = sub["accuracy_pct"].dropna().mean()
            rows.append({"product": p, "accuracy": round(float(acc), 1) if not np.isnan(acc) else 0})
    if not rows:
        return go.Figure()
    df = pd.DataFrame(rows).sort_values("accuracy")
    bar_colors = ["#15803d" if v >= 90 else "#b45309" if v >= 80 else "#b91c1c" for v in df["accuracy"]]
    fig = go.Figure(go.Bar(
        x=df["accuracy"], y=df["product"], orientation="h",
        marker=dict(color=bar_colors, line=dict(width=0)),
        text=df["accuracy"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside", textfont=dict(size=10),
    ))
    layout = dict(**_BASE, height=height)
    layout["xaxis"] = dict(**_BASE["xaxis"], range=[0, 110], ticksuffix="%")
    layout["title"] = dict(text="Akurasi forecast per produk (100% − MAPE)", font=dict(size=12), x=0)
    fig.update_layout(**layout)
    return fig


# ── Material horizontal bar (used in total MRP section) ──────────────

def material_bar_chart(total_mrp_df: pd.DataFrame, top_n: int = 10, height: int | None = None) -> go.Figure:
    df = total_mrp_df.head(top_n).sort_values("total_qty")
    if df.empty:
        return go.Figure()
    n = len(df)
    if height is None:
        height = max(200, n * 38 + 60)
    blues = [f"rgba(26,86,219,{0.3 + 0.7*(i/max(n-1,1)):.2f})" for i in range(n)]
    fig = go.Figure(go.Bar(
        x=df["total_qty"], y=df["material"], orientation="h",
        marker=dict(color=blues, line=dict(width=0)),
        text=df["total_qty"].apply(lambda v: f"{v:,.3f}"),
        textposition="outside", textfont=dict(size=10),
    ))
    layout = dict(**_BASE, height=height)
    layout["xaxis"] = dict(**_BASE["xaxis"], title="Total qty")
    layout["title"] = dict(text="Total kebutuhan material", font=dict(size=12), x=0)
    fig.update_layout(**layout)
    return fig


# ── Daily MRP line chart ─────────────────────────────────────────────

def daily_mrp_chart(daily_mrp_df: pd.DataFrame, selected_materials: list[str], height: int = 240) -> go.Figure:
    fig = go.Figure()
    df = daily_mrp_df[daily_mrp_df["material"].isin(selected_materials)] if selected_materials else daily_mrp_df
    for idx, mat in enumerate(df["material"].unique()):
        sub = df[df["material"] == mat].sort_values("order_date")
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(sub["order_date"]), y=sub["qty_needed"],
            mode="lines+markers", name=mat,
            line=dict(color=_c(idx), width=1.6), marker=dict(size=4),
        ))
    layout = dict(**_BASE, height=height, hovermode="x unified")
    layout["title"] = dict(text="Kebutuhan material harian", font=dict(size=12), x=0)
    fig.update_layout(**layout)
    return fig
