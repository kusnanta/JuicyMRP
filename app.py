"""
app.py — Forecasting & MRP Dashboard  (CSV Edition, v7)

Run:
    streamlit run app.py
"""
from __future__ import annotations

import datetime
from datetime import date, timedelta

import numpy as np
import pandas as pd
import streamlit as st

from config.settings import settings
from data import (
    load_sales, load_bom,
    make_sample_sales, make_sample_bom,
    sales_to_csv_bytes, bom_to_csv_bytes,
)
from forecasting import (
    run_all_forecasts, flatten_forecasts,
    best_method, ALL_REAL_METHODS, METHOD_DISPLAY,
)
from mrp import calculate_daily_mrp, pivot_mrp, total_mrp
from ui import GLOBAL_CSS
from ui.charts import forecast_chart, PROD_COLORS

# ── Page config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Forecast & MRP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ── Session state ────────────────────────────────────────────────────
for k, v in {
    "df_sales":     None,
    "df_bom":       None,
    "all_results":  None,
    "processed_at": None,
    "sel_method":   "best",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def fmt_n(n: float, dec: int = 1) -> str:
    if pd.isna(n):
        return "N/A"
    if n >= 1_000_000:
        return f"{n/1_000_000:.{dec}f}M"
    if n >= 1_000:
        return f"{n/1_000:.{dec}f}K"
    return f"{n:,.{dec}f}"


METHOD_BADGE_CSS = {
    "prophet":       "background:#dbeafe;color:#1e40af",
    "sarima":        "background:#fef3c7;color:#92400e",
    "naive":         "background:#f3f4f6;color:#374151",
    "zero_fallback": "background:#fee2e2;color:#991b1b",
}

def method_badge_html(m: str) -> str:
    css = METHOD_BADGE_CSS.get(m, METHOD_BADGE_CSS["naive"])
    label = METHOD_DISPLAY.get(m, m)
    return f'<span style="font-size:10px;padding:2px 8px;border-radius:6px;{css}">{label}</span>'


def run_pipeline(df_sales: pd.DataFrame, df_bom: pd.DataFrame) -> dict:
    """Run all forecast methods for all products. Returns all_results dict."""
    from forecasting.engine import forecast_product_all_methods
    products = df_sales["product_name"].unique().tolist()
    all_results = {}
    prog = st.progress(0, text="Menyiapkan forecasting…")
    for i, prod in enumerate(products):
        pct = int((i + 1) / len(products) * 100)
        prog.progress(pct, text=f"Forecasting '{prod}' ({i+1}/{len(products)})…")
        df_p = df_sales[df_sales["product_name"] == prod].copy()
        try:
            all_results[prod] = forecast_product_all_methods(
                df_p, prod, horizon=settings.FORECAST_HORIZON_DAYS
            )
        except Exception as e:
            st.warning(f"⚠️ '{prod}' gagal: {e}")
    prog.empty()
    return all_results


# ═══════════════════════════════════════════════════════════════════════
# HTML table builders
# ═══════════════════════════════════════════════════════════════════════

_TH = "padding:6px 10px;font-weight:500;font-size:11px;color:var(--color-text-secondary);border-bottom:0.5px solid var(--color-border-tertiary);background:var(--color-background-secondary);white-space:nowrap"
_TD = "padding:5px 10px;border-bottom:0.5px solid var(--color-border-tertiary)"
_MONO = "font-family:'IBM Plex Mono',monospace;font-size:11px"


def _dot(color: str) -> str:
    return f'<span style="width:6px;height:6px;border-radius:50%;background:{color};display:inline-block;margin-right:5px;vertical-align:middle"></span>'


def _pivot_mrp_html(pivot_df: pd.DataFrame) -> str:
    """Render MRP pivot (material × date) as HTML table."""
    if pivot_df.empty:
        return "<p style='color:#9ca3af;font-size:13px'>Tidak ada data MRP.</p>"
    date_cols = [c for c in pivot_df.columns if c not in ("material", "TOTAL")]
    head = (
        f"<tr><th style='{_TH};text-align:left;position:sticky;left:0;z-index:2'>Material</th>"
        f"<th style='{_TH};text-align:right;color:#1a56db;border-left:0.5px solid var(--color-border-tertiary)'>TOTAL</th>"
        + "".join(f"<th style='{_TH};text-align:right'>{c[5:]}</th>" for c in date_cols)
        + "</tr>"
    )
    rows = []
    for ri, (_, row) in enumerate(pivot_df.iterrows()):
        bg = "background:var(--color-background-secondary)" if ri % 2 else ""
        cells = (
            f"<td style='{_TD};font-weight:500;font-size:12px;position:sticky;left:0;z-index:1;{bg}'>{row['material']}</td>"
            f"<td style='{_TD};{_MONO};text-align:right;color:#1a56db;font-weight:500;border-left:0.5px solid var(--color-border-tertiary);{bg}'>{row['TOTAL']:.3f}</td>"
            + "".join(
                f"<td style='{_TD};{_MONO};text-align:right;"
                f"{'color:#111827' if row[c] > 0 else 'color:#d1d5db'};{bg}'>"
                f"{row[c]:.3f}</td>"
                for c in date_cols
            )
        )
        rows.append(f"<tr>{cells}</tr>")
    return (
        "<div style='overflow-x:auto;border:0.5px solid var(--color-border-tertiary);"
        "border-radius:8px;margin-bottom:1rem'>"
        f"<table style='border-collapse:collapse;font-size:11px;min-width:100%'>"
        f"<thead>{head}</thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _acc_pivot_html(all_results: dict, products: list[str], selected_method: str) -> str:
    """Accuracy × method pivot table. Best cell highlighted green, active column bordered blue."""
    real_methods = ALL_REAL_METHODS

    # Header
    head = (
        f"<tr><th style='{_TH};text-align:left;position:sticky;left:0;z-index:2'>Produk</th>"
        + "".join(
            f"<th style='{_TH};text-align:center;"
            f"{'color:var(--color-text-info)' if selected_method==m else ''}"
            f"{'border-left:2px solid #1a56db;border-right:2px solid #1a56db;background:rgba(24,95,165,0.06)' if selected_method==m else ''}' >"
            f"{'✓ ' if selected_method==m else ''}{METHOD_DISPLAY.get(m,m)}</th>"
            for m in real_methods
        )
        + f"<th style='{_TH};text-align:center'>Metode aktif</th></tr>"
    )

    rows = []
    for ri, p in enumerate(products):
        method_results = all_results.get(p, {})
        accs = {
            m: (method_results[m]["accuracy_pct"].dropna().mean()
                if m in method_results and not method_results[m].empty else None)
            for m in real_methods
        }
        valid = [v for v in accs.values() if v is not None and not np.isnan(v)]
        max_acc = max(valid) if valid else None
        eff = (best_method(method_results) if selected_method == "best" and method_results
               else (selected_method if selected_method in method_results else best_method(method_results) if method_results else "naive"))

        bg = "background:var(--color-background-secondary)" if ri % 2 else ""
        color = PROD_COLORS[products.index(p) % len(PROD_COLORS)]
        prod_cell = (
            f"<td style='{_TD};font-weight:500;font-size:12px;position:sticky;left:0;z-index:1;{bg}'>"
            f"{_dot(color)}{p}</td>"
        )

        method_cells = ""
        for m in real_methods:
            acc = accs[m]
            is_best = acc is not None and max_acc is not None and not np.isnan(acc) and abs(acc - max_acc) < 0.01
            is_active = m == eff
            extra = "border-left:2px solid #1a56db;border-right:2px solid #1a56db;background:rgba(24,95,165,0.06)" if is_active else ""
            cell_style = f"{_TD};text-align:center;{bg};{extra}"
            if acc is None or np.isnan(acc):
                method_cells += f"<td style='{cell_style}'><span style='color:var(--color-text-tertiary);font-size:11px'>—</span></td>"
            elif is_best:
                method_cells += (f"<td style='{cell_style}'>"
                                 f"<span style='background:var(--color-background-success);color:var(--color-text-success);"
                                 f"font-weight:500;border-radius:5px;padding:2px 7px;font-size:11px'>{acc:.1f}%</span></td>")
            else:
                method_cells += f"<td style='{cell_style}'><span style='color:var(--color-text-secondary);font-size:11px'>{acc:.1f}%</span></td>"

        badge = method_badge_html(eff)
        rows.append(
            f"<tr style='border-bottom:0.5px solid var(--color-border-tertiary);{bg}'>"
            f"{prod_cell}{method_cells}"
            f"<td style='{_TD};text-align:center;{bg}'>{badge}</td></tr>"
        )

    return (
        "<div style='overflow-x:auto;border:0.5px solid var(--color-border-tertiary);"
        "border-radius:8px;margin-bottom:1rem'>"
        f"<table style='border-collapse:collapse;font-size:12px;min-width:100%'>"
        f"<thead>{head}</thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _fc_pivot_html(forecast_df: pd.DataFrame, products: list[str], dates: list) -> str:
    """Forecast qty pivot: product (rows) × date (columns)."""
    def _ds(d):
        return f"{d.month}/{d.day}"

    head = (
        f"<tr><th style='{_TH};text-align:left;position:sticky;left:0;z-index:2'>Produk</th>"
        + "".join(f"<th style='{_TH};text-align:right;min-width:46px'>{_ds(d)}</th>" for d in dates)
        + f"<th style='{_TH};text-align:right;color:#1a56db;border-left:0.5px solid var(--color-border-tertiary)'>Total</th></tr>"
    )

    rows = []
    for ri, p in enumerate(products):
        fc = forecast_df[forecast_df["product_name"] == p]
        vals = []
        for d in dates:
            ds = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
            row = fc[fc["forecast_date"].astype(str).str[:10] == ds]
            vals.append(float(row["forecast_qty"].iloc[0]) if not row.empty else 0.0)
        total = sum(vals)
        bg = "background:var(--color-background-secondary)" if ri % 2 else ""
        color = PROD_COLORS[products.index(p) % len(PROD_COLORS)]
        cells = "".join(
            f"<td style='{_TD};{_MONO};text-align:right;color:#111827;{bg}'>{v:.1f}</td>"
            for v in vals
        )
        rows.append(
            f"<tr style='border-bottom:0.5px solid var(--color-border-tertiary);{bg}'>"
            f"<td style='{_TD};font-weight:500;font-size:12px;position:sticky;left:0;z-index:1;{bg}'>"
            f"{_dot(color)}{p}</td>"
            f"{cells}"
            f"<td style='{_TD};{_MONO};text-align:right;color:#1a56db;font-weight:500;"
            f"border-left:0.5px solid var(--color-border-tertiary);{bg}'>{total:.1f}</td></tr>"
        )

    return (
        "<div style='overflow-x:auto;border:0.5px solid var(--color-border-tertiary);"
        "border-radius:8px;margin-bottom:1rem'>"
        f"<table style='border-collapse:collapse;font-size:11px;min-width:100%'>"
        f"<thead>{head}</thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _mrp_total_html(total_df: pd.DataFrame) -> str:
    """
    Total MRP table with inline bar chart in the 'Distribusi' column.
    Bar width = avg_per_day / max_avg_per_day.
    Label beside bar shows the actual avg/day value.
    """
    if total_df.empty:
        return "<p style='color:#9ca3af;font-size:13px'>Tidak ada data MRP.</p>"

    max_avg = total_df["avg_per_day"].max() or 1

    head = (
        f"<tr>"
        f"<th style='{_TH};text-align:left;width:36px'>Rank</th>"
        f"<th style='{_TH};text-align:left'>Material</th>"
        f"<th style='{_TH};text-align:right;width:80px'>Total qty</th>"
        f"<th style='{_TH};text-align:right;width:90px'>Per hari</th>"
        f"<th style='{_TH};min-width:160px'>Distribusi (qty/hari)</th>"
        f"</tr>"
    )

    rows = []
    for ri, row in total_df.iterrows():
        bg = "background:var(--color-background-secondary)" if ri % 2 else ""
        pct = int(row["avg_per_day"] / max_avg * 100)
        opacity = max(0.28, 1.0 - int(row["rank"] - 1) * 0.075)
        bar_color = f"rgba(24,95,165,{opacity:.2f})"

        bar_html = (
            f'<div style="display:flex;align-items:center;gap:6px">'
            f'<div style="flex:1;height:10px;background:var(--color-background-secondary);'
            f'border-radius:3px;overflow:hidden;min-width:60px">'
            f'<div style="width:{pct}%;height:100%;background:{bar_color};border-radius:3px"></div>'
            f'</div>'
            f'<span style="font-size:10px;color:var(--color-text-secondary);'
            f'font-family:\'IBM Plex Mono\',monospace;white-space:nowrap;flex-shrink:0">'
            f'{row["avg_per_day"]:.3f}/hr</span>'
            f'</div>'
        )

        rows.append(
            f"<tr style='border-bottom:0.5px solid var(--color-border-tertiary);{bg}'>"
            f"<td style='{_TD};color:var(--color-text-tertiary);font-size:11px;{bg}'>{int(row['rank'])}</td>"
            f"<td style='{_TD};font-weight:500;{bg}'>{row['material']}</td>"
            f"<td style='{_TD};{_MONO};text-align:right;{bg}'>{row['total_qty']:.3f}</td>"
            f"<td style='{_TD};{_MONO};text-align:right;{bg}'>{row['avg_per_day']:.3f}</td>"
            f"<td style='{_TD};{bg}'>{bar_html}</td>"
            f"</tr>"
        )

    return (
        "<div style='overflow-x:auto;border:0.5px solid var(--color-border-tertiary);border-radius:8px'>"
        f"<table style='border-collapse:collapse;font-size:12px;width:100%'>"
        f"<thead>{head}</thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


# ═══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════

def render_sidebar(all_results: dict | None) -> dict:
    with st.sidebar:
        st.markdown(
            "<div style='font-size:1.05rem;font-weight:800;letter-spacing:-.03em;margin-bottom:2px'>"
            "📊 Forecast & MRP</div>"
            "<div style='font-size:.65rem;color:#9ca3af;letter-spacing:.1em;text-transform:uppercase;"
            "font-weight:600;margin-bottom:14px'>CSV Edition v7</div>",
            unsafe_allow_html=True,
        )

        # ── Upload ────────────────────────────────────────────────────
        st.markdown("**1 — Data penjualan**")
        st.markdown("<div class='upload-hint'>date, product_name, sales_qty</div>", unsafe_allow_html=True)
        sales_file = st.file_uploader("Sales CSV", type=["csv"], key="sales_up", label_visibility="collapsed")
        st.download_button("⬇ Sample sales.csv", data=sales_to_csv_bytes(make_sample_sales()),
                           file_name="sample_sales.csv", mime="text/csv", use_container_width=True)

        st.divider()

        st.markdown("**2 — Raw material BOM**")
        st.markdown("<div class='upload-hint'>product_name, material, component_qty</div>", unsafe_allow_html=True)
        bom_file = st.file_uploader("BOM CSV", type=["csv"], key="bom_up", label_visibility="collapsed")
        st.download_button("⬇ Sample bom.csv", data=bom_to_csv_bytes(make_sample_bom()),
                           file_name="sample_bom.csv", mime="text/csv", use_container_width=True)

        st.divider()

        use_sample = sales_file is None or bom_file is None
        run_btn = st.button(
            "🚀 Run dengan sample data" if use_sample else "🔮 Run Forecast & MRP",
            use_container_width=True, type="primary",
        )
        if use_sample:
            st.caption("Upload kedua CSV atau klik untuk demo sample.")

        st.divider()

        # ── Filters ───────────────────────────────────────────────────
        today = date.today()
        date_from, date_to = today, today + timedelta(days=6)
        sel_prods: list[str] = []
        sel_mats: list[str] = []

        if all_results:
            all_products  = sorted(all_results.keys())
            all_materials = sorted(
                st.session_state.df_bom["material"].unique().tolist()
                if st.session_state.df_bom is not None else []
            )

            st.markdown("**Rentang tanggal**")
            st.caption("MRP pivot & forecast table.")
            c1, c2 = st.columns(2)
            with c1:
                date_from = st.date_input("Dari", value=today,
                    min_value=today,
                    max_value=today + timedelta(days=settings.FORECAST_HORIZON_DAYS - 1),
                    key="df")
            with c2:
                date_to = st.date_input("Sampai", value=today + timedelta(days=6),
                    min_value=today,
                    max_value=today + timedelta(days=settings.FORECAST_HORIZON_DAYS - 1),
                    key="dt")
            if date_to < date_from:
                date_to = date_from
            st.caption(f"{(date_to - date_from).days + 1} hari dipilih")

            st.divider()

            st.markdown("**Produk**")
            sel_prods = st.multiselect("Produk", options=all_products, default=all_products,
                                       key="sel_prods", label_visibility="collapsed")
            if not sel_prods:
                sel_prods = all_products[:1]

            st.divider()

            st.markdown("**Raw material (MRP)**")
            sel_mats = st.multiselect("Material", options=all_materials, default=all_materials,
                                      key="sel_mats", label_visibility="collapsed")
            if not sel_mats:
                sel_mats = all_materials

        if st.session_state.processed_at:
            st.divider()
            st.caption(f"🕐 {st.session_state.processed_at.strftime('%d %b %Y %H:%M:%S')}")

    return dict(
        run_btn=run_btn, use_sample=use_sample,
        sales_file=sales_file, bom_file=bom_file,
        date_from=date_from, date_to=date_to,
        sel_prods=sel_prods, sel_mats=sel_mats,
    )


# ═══════════════════════════════════════════════════════════════════════
# DASHBOARD TAB
# ═══════════════════════════════════════════════════════════════════════

def tab_dashboard(all_results, fc_df, df_sales, df_bom, sel_prods, date_from, date_to):
    today = date.today()

    # KPIs
    dates30 = [today + timedelta(days=d) for d in range(30)]
    total30 = sum(
        fc_df[(fc_df["product_name"] == p) &
              (pd.to_datetime(fc_df["forecast_date"]).dt.date.isin(dates30))]["forecast_qty"].sum()
        for p in sel_prods
    )
    avg_acc = fc_df[fc_df["product_name"].isin(sel_prods)]["accuracy_pct"].dropna().mean()
    mrp3 = total_mrp(fc_df, df_bom, sel_prods, today, today + timedelta(days=2))
    top3 = mrp3.iloc[0] if not mrp3.empty else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total forecast 30H", fmt_n(total30, 0), f"{len(sel_prods)} produk")
    c2.metric("Rata-rata akurasi", f"{avg_acc:.1f}%" if not pd.isna(avg_acc) else "N/A", "100% − MAPE")
    c3.metric("Material teratas (3H)", top3["material"] if top3 is not None else "—",
              f"{top3['total_qty']:.3f} unit" if top3 is not None else "—")
    c4.metric("Total material", str(len(df_bom["material"].unique()) if df_bom is not None else 0))

    st.divider()

    # Line chart — always full 30-day forecast, filter range highlighted
    st.markdown("<div class='section-label'>Historical 30H + Forecast 30 hari ke depan</div>",
                unsafe_allow_html=True)
    st.plotly_chart(
        forecast_chart(df_sales, fc_df, sel_prods, hist_days=30,
                       date_from=date_from, date_to=date_to, height=280),
        use_container_width=True,
    )

    # Two-column tables
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("<div class='section-label'>Forecast qty produk — 7 hari ke depan</div>",
                    unsafe_allow_html=True)
        dates7 = [pd.Timestamp(today + timedelta(days=d)) for d in range(7)]
        st.markdown(_fc_pivot_html(fc_df, sel_prods, dates7), unsafe_allow_html=True)

    with col_r:
        st.markdown("<div class='section-label'>Kebutuhan beli material — 3 hari ke depan</div>",
                    unsafe_allow_html=True)
        daily3 = calculate_daily_mrp(fc_df, df_bom, sel_prods, today, today + timedelta(days=2))
        if daily3.empty:
            st.info("Tidak ada data BOM yang cocok.")
        else:
            st.markdown(_pivot_mrp_html(pivot_mrp(daily3)), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# FORECAST TAB
# ═══════════════════════════════════════════════════════════════════════

def tab_forecast(all_results, df_sales, sel_prods, date_from, date_to):
    # ── Method selector ───────────────────────────────────────────────
    st.markdown("<div class='section-label'>Metode forecast</div>", unsafe_allow_html=True)

    METHOD_OPTIONS = {"best": "⭐ Terbaik (auto)", **{m: METHOD_DISPLAY[m] for m in ALL_REAL_METHODS}}
    keys   = list(METHOD_OPTIONS.keys())
    labels = list(METHOD_OPTIONS.values())

    cols = st.columns(len(keys))
    for i, (mk, ml) in enumerate(zip(keys, labels)):
        with cols[i]:
            active = st.session_state.sel_method == mk
            if st.button(ml, key=f"mbtn_{mk}",
                         type="primary" if active else "secondary",
                         use_container_width=True):
                st.session_state.sel_method = mk
                st.rerun()

    sel_method = st.session_state.sel_method

    if sel_method == "best":
        acc_prods = [p for p in sel_prods if p in all_results]
        notes = [f"**{p}**: {best_method(all_results[p])}" for p in acc_prods if all_results.get(p)]
        st.caption("Auto-pilih per produk — " + " · ".join(notes))

    fc_df = flatten_forecasts(all_results, selected_method=sel_method)
    fc_prods = fc_df[fc_df["product_name"].isin(sel_prods)]

    st.divider()

    # ── Line chart ────────────────────────────────────────────────────
    st.markdown("<div class='section-label'>Historical 30H + Forecast 30 hari ke depan</div>",
                unsafe_allow_html=True)
    st.plotly_chart(
        forecast_chart(df_sales, fc_prods, sel_prods, hist_days=30,
                       date_from=date_from, date_to=date_to, height=280),
        use_container_width=True,
    )

    # ── 1. Forecast pivot (date range filter) ─────────────────────────
    st.markdown("<div class='section-label'>Forecast qty produk — pivot (date range filter)</div>",
                unsafe_allow_html=True)
    dates_range = [pd.Timestamp(date_from + timedelta(days=d))
                   for d in range((date_to - date_from).days + 1)]
    st.markdown(_fc_pivot_html(fc_prods, sel_prods, dates_range), unsafe_allow_html=True)

    col1, _ = st.columns([1, 3])
    with col1:
        fc_export = fc_prods[
            (pd.to_datetime(fc_prods["forecast_date"]).dt.date >= date_from) &
            (pd.to_datetime(fc_prods["forecast_date"]).dt.date <= date_to)
        ]
        st.download_button("⬇ Download forecast CSV", data=to_csv(fc_export),
                           file_name=f"forecast_{date_from}_{date_to}.csv", mime="text/csv")

    st.divider()

    # ── 2. Accuracy pivot ─────────────────────────────────────────────
    st.markdown(
        "<div class='section-label'>Akurasi forecast per produk × metode</div>",
        unsafe_allow_html=True,
    )
    st.caption("Hijau = akurasi tertinggi per produk · Kolom aktif = metode yang dipilih")
    acc_prods = [p for p in sel_prods if p in all_results]
    st.markdown(_acc_pivot_html(all_results, acc_prods, sel_method), unsafe_allow_html=True)

    st.divider()

    # ── Detail table ──────────────────────────────────────────────────
    st.markdown("<div class='section-label'>Detail forecast (date range filter)</div>",
                unsafe_allow_html=True)

    fc_show = fc_prods[
        (pd.to_datetime(fc_prods["forecast_date"]).dt.date >= date_from) &
        (pd.to_datetime(fc_prods["forecast_date"]).dt.date <= date_to)
    ].copy()
    fc_show["forecast_date"] = fc_show["forecast_date"].astype(str).str[:10]

    st.dataframe(
        fc_show.rename(columns={
            "forecast_date": "Tanggal", "product_name": "Produk",
            "forecast_qty": "Forecast", "forecast_lower": "Lower",
            "forecast_upper": "Upper", "accuracy_pct": "Akurasi %",
            "model_used": "Metode",
        }),
        use_container_width=True, hide_index=True,
        column_config={
            "Forecast":  st.column_config.NumberColumn(format="%.1f"),
            "Lower":     st.column_config.NumberColumn(format="%.1f"),
            "Upper":     st.column_config.NumberColumn(format="%.1f"),
            "Akurasi %": st.column_config.NumberColumn(format="%.1f"),
        },
    )


# ═══════════════════════════════════════════════════════════════════════
# MRP TAB
# ═══════════════════════════════════════════════════════════════════════

def tab_mrp(fc_df, df_bom, sel_prods, sel_mats, date_from, date_to):
    n_days = (date_to - date_from).days + 1
    prod_note = (
        sel_prods[0] if len(sel_prods) == 1
        else "Semua produk" if len(sel_prods) == len(fc_df["product_name"].unique())
        else f"{len(sel_prods)} produk"
    )
    st.caption(
        f"Produk: **{prod_note}** · "
        f"Periode: **{date_from.strftime('%d %b')} – {date_to.strftime('%d %b %Y')}** "
        f"({n_days} hari) · Material: **{len(sel_mats)} dipilih**"
    )

    # ── Pivot table (material × date) ─────────────────────────────────
    st.markdown("<div class='section-label'>Kebutuhan pembelian per hari (material × tanggal)</div>",
                unsafe_allow_html=True)
    daily = calculate_daily_mrp(fc_df, df_bom, sel_prods, date_from, date_to)
    daily_f = daily[daily["material"].isin(sel_mats)] if not daily.empty else daily
    pivot_df = pivot_mrp(daily_f)
    st.markdown(_pivot_mrp_html(pivot_df), unsafe_allow_html=True)

    col1, _ = st.columns([1, 3])
    with col1:
        if not daily_f.empty:
            st.download_button("⬇ Pivot CSV", data=to_csv(pivot_df),
                               file_name=f"mrp_pivot_{date_from}_{date_to}.csv", mime="text/csv")

    # ── Total table with inline bar (bar = avg/day, scaled to max avg/day) ──
    st.markdown(
        "<div class='section-label'>Total kebutuhan (rentang filter) — diurutkan dari tertinggi</div>",
        unsafe_allow_html=True,
    )
    total_df = total_mrp(fc_df, df_bom, sel_prods, date_from, date_to)
    total_f  = total_df[total_df["material"].isin(sel_mats)] if not total_df.empty else total_df

    if total_f.empty:
        st.info("Tidak ada data MRP untuk filter yang dipilih.")
        return

    st.markdown(_mrp_total_html(total_f), unsafe_allow_html=True)

    col1, _ = st.columns([1, 3])
    with col1:
        st.download_button("⬇ Total MRP CSV", data=to_csv(total_f),
                           file_name=f"mrp_total_{date_from}_{date_to}.csv", mime="text/csv",
                           use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════
# RAW DATA TAB
# ═══════════════════════════════════════════════════════════════════════

def tab_raw(df_sales, df_bom):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='section-label'>Data penjualan</div>", unsafe_allow_html=True)
        st.dataframe(df_sales, use_container_width=True, hide_index=True)
        st.download_button("⬇ Download sales CSV", data=to_csv(df_sales),
                           file_name="sales_data.csv", mime="text/csv")
    with col2:
        st.markdown("<div class='section-label'>BOM / Recipe</div>", unsafe_allow_html=True)
        st.dataframe(df_bom, use_container_width=True, hide_index=True)
        st.download_button("⬇ Download BOM CSV", data=to_csv(df_bom),
                           file_name="bom_data.csv", mime="text/csv")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    st.markdown(
        "<div style='margin-bottom:20px'>"
        "<span style='font-size:1.55rem;font-weight:800;letter-spacing:-.04em'>📊 Forecasting & MRP Dashboard</span>"
        "<span style='font-size:.72rem;color:#9ca3af;margin-left:14px;letter-spacing:.1em;"
        "text-transform:uppercase;font-weight:600;vertical-align:middle'>"
        "Sales Forecast · Material Requirement Planning · CSV Edition</span></div>",
        unsafe_allow_html=True,
    )

    ui = render_sidebar(st.session_state.all_results)

    # ── Run pipeline ──────────────────────────────────────────────────
    if ui["run_btn"]:
        try:
            if ui["use_sample"]:
                df_sales = make_sample_sales()
                df_bom   = make_sample_bom()
                st.info("💡 Menggunakan data sample (5 produk kafe, 180 hari).")
            else:
                df_sales = load_sales(ui["sales_file"])
                df_bom   = load_bom(ui["bom_file"])

            with st.spinner("Menjalankan forecasting semua metode…"):
                all_results = run_pipeline(df_sales, df_bom)

            if not all_results:
                st.error("Forecast gagal untuk semua produk.")
                return

            st.session_state.df_sales     = df_sales
            st.session_state.df_bom       = df_bom
            st.session_state.all_results  = all_results
            st.session_state.processed_at = datetime.datetime.now()
            st.success(f"✅ Selesai — {len(all_results)} produk, "
                       f"{settings.FORECAST_HORIZON_DAYS} hari ke depan.")
            st.rerun()

        except ValueError as e:
            st.error(f"❌ Format CSV tidak valid: {e}")
        except Exception as e:
            st.error(f"❌ Error: {e}")
            import traceback; st.code(traceback.format_exc())

    # ── Empty state ───────────────────────────────────────────────────
    if st.session_state.all_results is None:
        st.markdown(
            "<div style='text-align:center;padding:60px 40px;border:1px dashed #e5e7eb;"
            "border-radius:16px;margin-top:20px'>"
            "<div style='font-size:2.5rem;margin-bottom:12px'>📊</div>"
            "<div style='font-size:1.1rem;font-weight:700;margin-bottom:8px'>Siap memulai</div>"
            "<div style='color:#9ca3af;font-size:.88rem;line-height:1.7;max-width:420px;margin:0 auto'>"
            "Upload CSV penjualan &amp; BOM di sidebar, atau klik "
            "<strong>Run dengan sample data</strong> untuk demo langsung.</div>"
            "<div style='margin-top:18px;display:flex;justify-content:center;gap:18px;flex-wrap:wrap'>"
            "<div style='background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;"
            "padding:12px 16px;text-align:left'>"
            "<div style='font-size:.65rem;letter-spacing:.1em;text-transform:uppercase;"
            "color:#9ca3af;font-weight:600;margin-bottom:4px'>sales.csv</div>"
            "<code style='font-size:.72rem;color:#1a56db'>date, product_name, sales_qty</code></div>"
            "<div style='background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;"
            "padding:12px 16px;text-align:left'>"
            "<div style='font-size:.65rem;letter-spacing:.1em;text-transform:uppercase;"
            "color:#9ca3af;font-weight:600;margin-bottom:4px'>bom.csv</div>"
            "<code style='font-size:.72rem;color:#1a56db'>product_name, material, component_qty</code>"
            "</div></div></div>",
            unsafe_allow_html=True,
        )
        return

    # ── Get state ─────────────────────────────────────────────────────
    all_results = st.session_state.all_results
    df_sales    = st.session_state.df_sales
    df_bom      = st.session_state.df_bom
    date_from   = ui["date_from"]
    date_to     = ui["date_to"]
    sel_prods   = ui["sel_prods"] or list(all_results.keys())
    sel_mats    = ui["sel_mats"] or (df_bom["material"].unique().tolist() if df_bom is not None else [])
    sel_method  = st.session_state.get("sel_method", "best")

    # Flat forecast df using current method selection
    fc_df = flatten_forecasts(all_results, selected_method=sel_method)

    # ── Tabs ──────────────────────────────────────────────────────────
    t_dash, t_fc, t_mrp, t_raw = st.tabs([
        "📊 Dashboard", "🔮 Forecast", "⚙️ MRP", "📁 Raw data"
    ])

    with t_dash:
        tab_dashboard(all_results, fc_df, df_sales, df_bom, sel_prods, date_from, date_to)

    with t_fc:
        tab_forecast(all_results, df_sales, sel_prods, date_from, date_to)

    with t_mrp:
        tab_mrp(fc_df, df_bom, sel_prods, sel_mats, date_from, date_to)

    with t_raw:
        tab_raw(df_sales, df_bom)

    # Footer
    st.markdown("---")
    ts = st.session_state.processed_at
    st.caption(
        f"🕐 {ts.strftime('%d %b %Y %H:%M:%S') if ts else '—'} · "
        f"Horizon: {settings.FORECAST_HORIZON_DAYS} hari · "
        f"Min data: {settings.MIN_DATA_POINTS} hari · "
        f"Metode aktif: {sel_method}"
    )


if __name__ == "__main__":
    main()
