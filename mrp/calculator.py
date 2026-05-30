"""
mrp/calculator.py  — Material Requirement Planning calculations.

All functions accept a flat forecast_df (one row per date × product)
plus bom_df, plus optional filter args.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
from loguru import logger


# ── helpers ──────────────────────────────────────────────────────────

def _filter_fc(
    forecast_df: pd.DataFrame,
    products: list[str] | None,
    date_from: date | None,
    date_to:   date | None,
) -> pd.DataFrame:
    fc = forecast_df.copy()
    fc["forecast_date"] = pd.to_datetime(fc["forecast_date"])
    if products:
        fc = fc[fc["product_name"].isin(products)]
    if date_from:
        fc = fc[fc["forecast_date"] >= pd.Timestamp(date_from)]
    if date_to:
        fc = fc[fc["forecast_date"] <= pd.Timestamp(date_to)]
    return fc


# ── daily MRP: one row per date × material ───────────────────────────

def calculate_daily_mrp(
    forecast_df: pd.DataFrame,
    bom_df:      pd.DataFrame,
    products:    list[str] | None = None,
    date_from:   date | None = None,
    date_to:     date | None = None,
) -> pd.DataFrame:
    """
    Returns DataFrame [order_date, material, qty_needed].
    qty_needed = SUM(forecast_qty × component_qty) per date × material.
    """
    if forecast_df.empty or bom_df.empty:
        logger.warning("MRP skipped: empty inputs.")
        return pd.DataFrame(columns=["order_date", "material", "qty_needed"])

    fc = _filter_fc(forecast_df, products, date_from, date_to)
    if fc.empty:
        return pd.DataFrame(columns=["order_date", "material", "qty_needed"])

    missing = set(fc["product_name"].unique()) - set(bom_df["product_name"].unique())
    if missing:
        logger.warning("Products with no BOM (skipped): {}", missing)

    merged = fc[["forecast_date", "product_name", "forecast_qty"]].merge(
        bom_df[["product_name", "material", "component_qty"]],
        on="product_name", how="left",
    ).dropna(subset=["component_qty"])

    merged["qty_needed"] = (merged["forecast_qty"] * merged["component_qty"]).round(4)

    daily = (
        merged
        .groupby(["forecast_date", "material"], as_index=False)["qty_needed"]
        .sum()
        .rename(columns={"forecast_date": "order_date"})
        .sort_values(["order_date", "material"])
        .reset_index(drop=True)
    )
    daily["qty_needed"] = daily["qty_needed"].round(3)
    return daily


# ── pivot: material (rows) × date (columns) ──────────────────────────

def pivot_mrp(daily_mrp: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot daily MRP so materials are rows and dates are columns.
    Adds a TOTAL column (row sum). Sorted by TOTAL descending.
    """
    if daily_mrp.empty:
        return pd.DataFrame()

    pivot = daily_mrp.pivot_table(
        index="material", columns="order_date",
        values="qty_needed", fill_value=0.0, aggfunc="sum",
    )
    pivot.columns = [str(c)[:10] for c in pivot.columns]
    pivot.insert(0, "TOTAL", pivot.sum(axis=1).round(3))
    pivot = pivot.sort_values("TOTAL", ascending=False).reset_index()
    return pivot


# ── total MRP: one row per material, sorted descending ───────────────

def total_mrp(
    forecast_df: pd.DataFrame,
    bom_df:      pd.DataFrame,
    products:    list[str] | None = None,
    date_from:   date | None = None,
    date_to:     date | None = None,
) -> pd.DataFrame:
    """
    Returns DataFrame [rank, material, total_qty, avg_per_day],
    sorted by total_qty descending.
    """
    daily = calculate_daily_mrp(forecast_df, bom_df, products, date_from, date_to)
    if daily.empty:
        return pd.DataFrame(columns=["rank", "material", "total_qty", "avg_per_day"])

    n_days = max(daily["order_date"].nunique(), 1)
    agg = (
        daily.groupby("material", as_index=False)["qty_needed"]
        .sum()
        .rename(columns={"qty_needed": "total_qty"})
        .sort_values("total_qty", ascending=False)
        .reset_index(drop=True)
    )
    agg["total_qty"]  = agg["total_qty"].round(3)
    agg["avg_per_day"] = (agg["total_qty"] / n_days).round(4)
    agg.insert(0, "rank", range(1, len(agg) + 1))
    return agg
