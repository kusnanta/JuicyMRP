"""ui/filters.py — render sidebar filters, return active filter state."""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st


def render_filters(
    all_products: list[str],
    all_materials: list[str],
    default_horizon: int = 30,
    show_material_filter: bool = False,
) -> dict:
    """
    Render date range + product multi-select in the sidebar.
    Returns a dict with keys:
        date_from, date_to, selected_products, selected_materials
    """
    today = date.today()

    # ── Date range ────────────────────────────────────────────────
    st.sidebar.markdown("##### Rentang tanggal")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        date_from = st.date_input(
            "Dari", value=today, key="date_from",
            min_value=today, max_value=today + timedelta(days=default_horizon - 1),
            label_visibility="collapsed",
        )
    with col2:
        date_to = st.date_input(
            "Sampai", value=today + timedelta(days=6), key="date_to",
            min_value=today, max_value=today + timedelta(days=default_horizon - 1),
            label_visibility="collapsed",
        )

    if date_to < date_from:
        st.sidebar.warning("Tanggal akhir harus ≥ tanggal awal.")
        date_to = date_from

    st.sidebar.caption(f"{date_from.strftime('%d %b')} – {date_to.strftime('%d %b %Y')} ({(date_to - date_from).days + 1} hari)")

    # ── Product multi-select ──────────────────────────────────────
    st.sidebar.markdown("##### Produk")
    selected_products = st.sidebar.multiselect(
        "Pilih produk",
        options=all_products,
        default=all_products,
        key="sel_products",
        label_visibility="collapsed",
    )
    if not selected_products:
        st.sidebar.warning("Pilih minimal 1 produk.")
        selected_products = all_products[:1]

    # ── Material filter (MRP tab only) ────────────────────────────
    selected_materials = all_materials
    if show_material_filter and all_materials:
        st.sidebar.markdown("##### Raw material (MRP)")
        selected_materials = st.sidebar.multiselect(
            "Pilih material",
            options=all_materials,
            default=all_materials,
            key="sel_materials",
            label_visibility="collapsed",
        )
        if not selected_materials:
            selected_materials = all_materials

    return {
        "date_from": date_from,
        "date_to": date_to,
        "selected_products": selected_products,
        "selected_materials": selected_materials,
    }
