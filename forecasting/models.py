"""
forecasting/models.py
Forecasting model implementations:
  - SARIMA  (statsmodels) — for medium/limited data
  - Naive   (rolling mean + DOW pattern) — universal fallback
  - Prophet (optional) — for rich data if installed
"""
from __future__ import annotations

import warnings
from datetime import timedelta

import numpy as np
import pandas as pd
from loguru import logger


# ─── Naive / Rolling Mean ───────────────────────────────────────────

def forecast_naive(
    df_train: pd.DataFrame,
    horizon: int = 30,
    window: int = 14,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Rolling mean forecast with day-of-week multipliers.

    Returns (forecast_df, train_pred_df).
    forecast_df columns: ds, yhat, yhat_lower, yhat_upper
    train_pred_df columns: ds, yhat
    """
    y = df_train["y"].values.astype(float)

    # Day-of-week multipliers from training data
    df_tmp = df_train.copy()
    df_tmp["dow"] = pd.to_datetime(df_tmp["ds"]).dt.dayofweek
    dow_avg = df_tmp.groupby("dow")["y"].mean()
    global_avg = float(np.mean(y)) if len(y) > 0 else 1.0
    if global_avg == 0:
        global_avg = 1.0
    dow_mult = {d: dow_avg.get(d, global_avg) / global_avg for d in range(7)}

    base = float(np.mean(y[-window:])) if len(y) >= window else float(np.mean(y)) if len(y) else 0.0
    sigma = float(np.std(y)) if len(y) > 1 else base * 0.15

    last_date = pd.to_datetime(df_train["ds"].iloc[-1])
    future_dates = [last_date + timedelta(days=d + 1) for d in range(horizon)]

    yhat = [max(0.0, base * dow_mult.get(d.weekday(), 1.0)) for d in future_dates]
    forecast_df = pd.DataFrame({
        "ds": future_dates,
        "yhat": [round(v, 2) for v in yhat],
        "yhat_lower": [round(max(0.0, v - sigma), 2) for v in yhat],
        "yhat_upper": [round(v + sigma, 2) for v in yhat],
    })

    rolling = pd.Series(y).rolling(window=window, min_periods=1).mean().values
    train_pred_df = pd.DataFrame({
        "ds": df_train["ds"].values,
        "yhat": np.clip(rolling, 0, None).round(2),
    })
    return forecast_df, train_pred_df


# ─── SARIMA ────────────────────────────────────────────────────────

def forecast_sarima(
    df_train: pd.DataFrame,
    horizon: int = 30,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    SARIMA forecast using statsmodels. Tries several (p,d,q) candidates
    and picks the best AIC.
    """
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    y = df_train["y"].values.astype(float)
    candidates = [
        ((1, 1, 1), (0, 0, 0, 0)),
        ((1, 1, 1), (1, 0, 0, 7)),
        ((2, 1, 1), (0, 0, 0, 0)),
        ((1, 0, 1), (0, 0, 0, 0)),
    ]

    best, best_aic = None, np.inf
    for order, sorder in candidates:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m = SARIMAX(
                    y, order=order, seasonal_order=sorder,
                    enforce_stationarity=False, enforce_invertibility=False,
                ).fit(disp=False)
            if m.aic < best_aic:
                best_aic, best = m.aic, m
        except Exception:
            continue

    if best is None:
        raise RuntimeError("All SARIMA candidates failed.")

    fitted = best.fittedvalues
    fc = best.get_forecast(steps=horizon)
    fc_mean = fc.predicted_mean.values
    ci = fc.conf_int(alpha=0.2).values

    last_date = pd.to_datetime(df_train["ds"].iloc[-1])
    future_dates = [last_date + timedelta(days=d + 1) for d in range(horizon)]

    forecast_df = pd.DataFrame({
        "ds": future_dates,
        "yhat": np.clip(fc_mean, 0, None).round(2),
        "yhat_lower": np.clip(ci[:, 0], 0, None).round(2),
        "yhat_upper": ci[:, 1].round(2),
    })
    train_pred_df = pd.DataFrame({
        "ds": df_train["ds"].values,
        "yhat": np.clip(fitted.values, 0, None).round(2),
    })
    return forecast_df, train_pred_df


# ─── Prophet (optional) ─────────────────────────────────────────────

def forecast_prophet(
    df_train: pd.DataFrame,
    horizon: int = 30,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Prophet forecast. Raises ImportError if prophet is not installed."""
    from prophet import Prophet  # noqa: F401

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        seasonality_mode="multiplicative",
        changepoint_prior_scale=0.05,
        interval_width=0.80,
    )
    try:
        model.add_country_holidays(country_name="ID")
    except Exception:
        pass

    model.fit(df_train[["ds", "y"]])
    future = model.make_future_dataframe(periods=horizon, freq="D", include_history=True)
    pred = model.predict(future)
    pred["yhat"] = pred["yhat"].clip(lower=0)
    pred["yhat_lower"] = pred["yhat_lower"].clip(lower=0)
    pred["yhat_upper"] = pred["yhat_upper"].clip(lower=0)

    last_train = df_train["ds"].max()
    forecast_df = pred[pred["ds"] > last_train][["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    train_pred_df = pred[pred["ds"] <= last_train][["ds", "yhat"]].copy()

    forecast_df["yhat"] = forecast_df["yhat"].round(2)
    forecast_df["yhat_lower"] = forecast_df["yhat_lower"].round(2)
    forecast_df["yhat_upper"] = forecast_df["yhat_upper"].round(2)
    return forecast_df.reset_index(drop=True), train_pred_df.reset_index(drop=True)
