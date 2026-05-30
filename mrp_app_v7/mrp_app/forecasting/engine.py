"""
forecasting/engine.py
Orchestrator: runs all available models per product, stores results per method,
picks best by accuracy for the 'best' mode.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Callable

import numpy as np
import pandas as pd
from loguru import logger

from config.settings import settings
from forecasting.preprocessor import preprocess, train_test_split, classify
from forecasting.metrics import accuracy

ALL_REAL_METHODS = ["prophet", "sarima", "naive"]
METHOD_DISPLAY   = {"prophet": "Prophet", "sarima": "SARIMA", "naive": "Rolling mean"}


# ── per-model runner ─────────────────────────────────────────────────

def _run_one(model_fn: Callable, df_train: pd.DataFrame,
             df_test: pd.DataFrame, horizon: int) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    fc_df, train_pred_df = model_fn(df_train, horizon=horizon)

    acc = float("nan")
    if not df_test.empty:
        test_ds  = set(df_test["ds"].astype(str))
        tp       = train_pred_df[train_pred_df["ds"].astype(str).isin(test_ds)]
        actual   = df_test[df_test["ds"].astype(str).isin(set(tp["ds"].astype(str)))]["y"].values
        predicted = tp["yhat"].values[: len(actual)]
        if len(actual):
            acc = accuracy(actual, predicted)

    return fc_df, train_pred_df, acc


# ── forecast one product for ALL methods ────────────────────────────

def forecast_product_all_methods(
    df_raw: pd.DataFrame,
    product_name: str,
    horizon: int | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Run every available model for a single product.

    Returns dict keyed by method name ('prophet'|'sarima'|'naive'),
    each value is a DataFrame with columns:
        forecast_date, product_name, forecast_qty,
        forecast_lower, forecast_upper, accuracy_pct, model_used
    """
    if horizon is None:
        horizon = settings.FORECAST_HORIZON_DAYS

    logger.info("Forecasting '{}' — all methods ...", product_name)
    df_clean   = preprocess(df_raw, product_name)
    data_class = classify(df_clean)
    df_train, df_test = train_test_split(df_clean)

    from forecasting.models import forecast_naive, forecast_sarima

    model_fns: dict[str, Callable] = {"sarima": forecast_sarima, "naive": forecast_naive}
    try:
        from forecasting.models import forecast_prophet
        model_fns["prophet"] = forecast_prophet
    except ImportError:
        logger.debug("Prophet not available for '{}'.", product_name)

    results: dict[str, pd.DataFrame] = {}
    for method, fn in model_fns.items():
        try:
            fc_df, train_pred_df, acc = _run_one(fn, df_train, df_test, horizon)
            fc = fc_df.copy()
            fc["product_name"]  = product_name
            fc["accuracy_pct"]  = round(acc, 1) if not np.isnan(acc) else None
            fc["model_used"]    = method
            fc = fc.rename(columns={
                "ds": "forecast_date", "yhat": "forecast_qty",
                "yhat_lower": "forecast_lower", "yhat_upper": "forecast_upper",
            })
            cols = ["forecast_date", "product_name", "forecast_qty",
                    "forecast_lower", "forecast_upper", "accuracy_pct", "model_used"]
            results[method] = fc[cols].reset_index(drop=True)
            logger.info("  {} / {} → accuracy={}", product_name, method,
                        f"{acc:.1f}%" if not np.isnan(acc) else "n/a")
        except Exception as exc:
            logger.warning("  {} / {} failed: {}", product_name, method, exc)

    # Fallback: if nothing worked, return zero naive
    if not results:
        logger.error("All models failed for '{}'.", product_name)
        today = pd.Timestamp(date.today())
        zero_fc = pd.DataFrame({
            "forecast_date":  [today + pd.Timedelta(days=d+1) for d in range(horizon)],
            "product_name":   product_name,
            "forecast_qty":   0.0,
            "forecast_lower": 0.0,
            "forecast_upper": 0.0,
            "accuracy_pct":   None,
            "model_used":     "zero_fallback",
        })
        results["naive"] = zero_fc

    return results


def best_method(method_results: dict[str, pd.DataFrame]) -> str:
    """Return the method name with the highest accuracy_pct."""
    best, best_acc = None, -1.0
    for m, df in method_results.items():
        acc = df["accuracy_pct"].dropna().mean()
        if not np.isnan(acc) and acc > best_acc:
            best_acc, best = acc, m
    return best or list(method_results.keys())[0]


# ── multi-product orchestration ──────────────────────────────────────

def run_all_forecasts(
    df_sales: pd.DataFrame,
    horizon: int | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> dict[str, dict[str, pd.DataFrame]]:
    """
    Run all forecast methods for every product.

    Returns:
        {product_name: {method_name: forecast_df, ...}, ...}
    """
    if horizon is None:
        horizon = settings.FORECAST_HORIZON_DAYS

    products = df_sales["product_name"].unique().tolist()
    all_results: dict[str, dict[str, pd.DataFrame]] = {}

    for i, product in enumerate(products):
        if progress_callback:
            progress_callback(product, i + 1, len(products))
        df_p = df_sales[df_sales["product_name"] == product].copy()
        try:
            all_results[product] = forecast_product_all_methods(df_p, product, horizon)
        except Exception as exc:
            logger.error("Skipping '{}': {}", product, exc)

    return all_results


def flatten_forecasts(
    all_results: dict[str, dict[str, pd.DataFrame]],
    selected_method: str = "best",
) -> pd.DataFrame:
    """
    Flatten per-product, per-method results into a single DataFrame
    using the chosen method ('best' | 'prophet' | 'sarima' | 'naive').
    """
    frames = []
    for product, method_results in all_results.items():
        if selected_method == "best":
            m = best_method(method_results)
        elif selected_method in method_results:
            m = selected_method
        else:
            m = best_method(method_results)   # graceful fallback
        frames.append(method_results[m])

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
