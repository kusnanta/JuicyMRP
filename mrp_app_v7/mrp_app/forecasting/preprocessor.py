"""forecasting/preprocessor.py — clean and prepare per-product time series."""
from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger

from config.settings import settings


def preprocess(df_product: pd.DataFrame, product_name: str) -> pd.DataFrame:
    """
    Full preprocessing for a single product's sales history.

    Steps:
    1. Aggregate duplicate dates.
    2. Resample to daily frequency, fill missing dates with 0.
    3. Clip outliers via IQR.

    Returns DataFrame with columns: ds (datetime), y (float).
    """
    df = df_product[["date", "sales_qty"]].copy()
    df = df.set_index("date").sort_index()
    df = df.resample("D").sum()

    full_range = pd.date_range(df.index.min(), df.index.max(), freq="D")
    df = df.reindex(full_range, fill_value=0)
    df.index.name = "date"

    q1, q3 = df["sales_qty"].quantile(0.25), df["sales_qty"].quantile(0.75)
    iqr = q3 - q1
    upper = q3 + 3 * iqr
    n_clip = (df["sales_qty"] > upper).sum()
    if n_clip:
        logger.debug("Clipped {} outlier(s) for '{}'.", n_clip, product_name)
    df["sales_qty"] = df["sales_qty"].clip(lower=0, upper=max(upper, df["sales_qty"].max()))

    return df.reset_index().rename(columns={"date": "ds", "sales_qty": "y"})


def train_test_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chronological split. Train ratio from settings."""
    n = len(df)
    idx = max(int(n * settings.TRAIN_TEST_SPLIT_RATIO), settings.MIN_DATA_POINTS)
    return df.iloc[:idx].copy(), df.iloc[idx:].copy()


def classify(df: pd.DataFrame) -> str:
    """Return 'rich' | 'medium' | 'limited' | 'sparse'."""
    n = len(df)
    nonzero = (df["y"] > 0).sum()
    if n >= 60 and nonzero >= 30:
        return "rich"
    if n >= 30 and nonzero >= 14:
        return "medium"
    if n >= settings.MIN_DATA_POINTS:
        return "limited"
    return "sparse"
