"""data/sample.py — reproducible sample data generator for demo/testing."""
from __future__ import annotations

import io
import numpy as np
import pandas as pd
from datetime import date, timedelta


def _date_range(start: date, n: int) -> list[date]:
    return [start + timedelta(days=i) for i in range(n)]


def make_sample_sales(n_history_days: int = 180) -> pd.DataFrame:
    """
    Generate realistic synthetic daily sales data for 5 cafe products.

    Includes:
    - Weekly seasonality (weekend boost)
    - Slight upward trend
    - Gaussian noise
    """
    rng = np.random.default_rng(42)
    today = date.today()
    start = today - timedelta(days=n_history_days)
    dates = _date_range(start, n_history_days)

    products = [
        {"name": "Kopi Susu",    "base": 25, "std": 6},
        {"name": "Matcha Latte", "base": 18, "std": 5},
        {"name": "Croissant",    "base": 40, "std": 10},
        {"name": "Sandwich",     "base": 30, "std": 8},
        {"name": "Smoothie",     "base": 15, "std": 4},
    ]

    rows = []
    for d in dates:
        for p in products:
            dow_mult = 1.30 if d.weekday() >= 5 else 1.0
            trend = 1.0 + 0.0003 * (d - start).days
            qty = max(0, int(rng.normal(p["base"] * dow_mult * trend, p["std"])))
            rows.append({"date": d.isoformat(), "product_name": p["name"], "sales_qty": qty})

    return pd.DataFrame(rows)


def make_sample_bom() -> pd.DataFrame:
    """Return a Bill of Materials table with realistic cafe ingredient ratios."""
    rows = [
        ("Kopi Susu",    "Susu Segar",     0.150),
        ("Kopi Susu",    "Kopi Bubuk",     0.015),
        ("Kopi Susu",    "Gula Pasir",     0.020),
        ("Kopi Susu",    "Es Batu",        0.100),
        ("Matcha Latte", "Susu Segar",     0.180),
        ("Matcha Latte", "Matcha Powder",  0.010),
        ("Matcha Latte", "Gula Pasir",     0.015),
        ("Matcha Latte", "Es Batu",        0.080),
        ("Croissant",    "Tepung Terigu",  0.080),
        ("Croissant",    "Mentega",        0.040),
        ("Croissant",    "Telur",          0.050),
        ("Croissant",    "Gula Pasir",     0.010),
        ("Sandwich",     "Roti Tawar",     0.100),
        ("Sandwich",     "Daging Ayam",    0.080),
        ("Sandwich",     "Sayuran Mix",    0.050),
        ("Smoothie",     "Buah Mix",       0.200),
        ("Smoothie",     "Susu Segar",     0.100),
        ("Smoothie",     "Es Batu",        0.150),
        ("Smoothie",     "Madu",           0.015),
    ]
    return pd.DataFrame(rows, columns=["product_name", "material", "component_qty"])


def sales_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def bom_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def sales_csv_string() -> str:
    return make_sample_sales().to_csv(index=False)


def bom_csv_string() -> str:
    return make_sample_bom().to_csv(index=False)
