from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error

from .config import settings
from .data_loader import load_rates_df
from .storage import (
    ensure_project_dirs,
    forecast_history_path,
    latest_forecast_path,
    latest_run_path,
    read_json,
    winner_model_path,
    write_json,
)


TRAINING_START = pd.Timestamp("2020-02-22")
TEST_SIZE = 14


def _next_business_day(value: pd.Timestamp) -> pd.Timestamp:
    next_day = value + pd.Timedelta(days=1)
    while next_day.weekday() >= 5:
        next_day += pd.Timedelta(days=1)
    return next_day.normalize()


def _split_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    scoped = df[df["date"] >= TRAINING_START].copy()
    if len(scoped) <= TEST_SIZE + 20:
        scoped = df.copy()
    scoped = scoped.sort_values("date").reset_index(drop=True)
    if len(scoped) <= TEST_SIZE:
        raise ValueError("Not enough MXN observations to create a 14-day test set.")
    return scoped.iloc[:-TEST_SIZE].copy(), scoped.iloc[-TEST_SIZE:].copy()


def _features(df: pd.DataFrame) -> pd.DataFrame:
    featured = df.sort_values("date").copy()
    featured["lag_1"] = featured["value"].shift(1)
    featured["lag_2"] = featured["value"].shift(2)
    featured["lag_3"] = featured["value"].shift(3)
    featured["day_of_week"] = featured["date"].dt.dayofweek
    featured["month"] = featured["date"].dt.month
    featured["ma_7"] = featured["value"].rolling(7).mean()
    featured["ma_14"] = featured["value"].rolling(14).mean()
    return featured.dropna().reset_index(drop=True)


def _metric_payload(actual: np.ndarray, predicted: np.ndarray) -> Dict[str, float]:
    rmse = math.sqrt(mean_squared_error(actual, predicted))
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(rmse),
        "mape": float(mean_absolute_percentage_error(actual, predicted) * 100),
    }


def _forecast_records(
    test_df: pd.DataFrame,
    predicted: np.ndarray,
    lower: np.ndarray | None = None,
    upper: np.ndarray | None = None,
) -> List[Dict[str, Any]]:
    if lower is None or upper is None:
        residual_std = float(np.std(test_df["value"].to_numpy() - predicted))
        lower = predicted - 1.96 * residual_std
        upper = predicted + 1.96 * residual_std

    records: List[Dict[str, Any]] = []
    for index, row in enumerate(test_df.to_dict(orient="records")):
        records.append(
            {
                "date": pd.Timestamp(row["date"]).date().isoformat(),
                "actual": float(row["value"]),
                "forecast": float(predicted[index]),
                "lower": float(lower[index]),
                "upper": float(upper[index]),
            }
        )
    return records


def _fallback_trend(train_df: pd.DataFrame, test_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
    y = train_df["value"].to_numpy(dtype=float)
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, deg=1)
    future_x = np.arange(len(y), len(y) + len(test_df), dtype=float)
    predicted = intercept + slope * future_x
    residual_std = float(np.std(y - (intercept + slope * x))) if len(y) > 2 else 0.0
    lower = predicted - 1.96 * residual_std
    upper = predicted + 1.96 * residual_std
    model = {"kind": "linear_trend_fallback", "slope": float(slope), "intercept": float(intercept), "residual_std": residual_std}
    return predicted, lower, upper, model


def _train_prophet(train_df: pd.DataFrame, test_df: pd.DataFrame) -> Dict[str, Any]:
    try:
        from prophet import Prophet

        prophet_train = train_df.rename(columns={"date": "ds", "value": "y"})[["ds", "y"]]
        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True,
            interval_width=0.95,
        )
        model.fit(prophet_train)
        future = test_df.rename(columns={"date": "ds"})[["ds"]]
        forecast = model.predict(future)
        predicted = forecast["yhat"].to_numpy(dtype=float)
        lower = forecast["yhat_lower"].to_numpy(dtype=float)
        upper = forecast["yhat_upper"].to_numpy(dtype=float)
        status = "ok"
        error = None
    except Exception as exc:
        predicted, lower, upper, model = _fallback_trend(train_df, test_df)
        status = "fallback"
        error = f"Prophet unavailable or failed: {exc}"
        if "stan_backend" in str(exc) or "CmdStan" in str(exc):
            error += " CmdStan may need to be installed with: python -c \"import cmdstanpy; cmdstanpy.install_cmdstan()\""

    actual = test_df["value"].to_numpy(dtype=float)
    return {
        "name": "prophet",
        "status": status,
        "error": error,
        "metrics": _metric_payload(actual, predicted),
        "forecast": _forecast_records(test_df, predicted, lower, upper),
        "model": model,
    }


def _train_xgboost(full_df: pd.DataFrame, train_df: pd.DataFrame, test_df: pd.DataFrame) -> Dict[str, Any]:
    feature_columns = ["lag_1", "lag_2", "lag_3", "day_of_week", "month", "ma_7", "ma_14"]
    featured = _features(full_df)
    train_features = featured[featured["date"].isin(train_df["date"])]
    test_features = featured[featured["date"].isin(test_df["date"])]
    if len(test_features) != len(test_df):
        raise ValueError("Could not create complete XGBoost features for the test set.")

    x_train = train_features[feature_columns]
    y_train = train_features["value"]
    x_test = test_features[feature_columns]
    actual = test_features["value"].to_numpy(dtype=float)

    status = "ok"
    error = None
    try:
        from xgboost import XGBRegressor

        model = XGBRegressor(
            objective="reg:squarederror",
            n_estimators=250,
            max_depth=3,
            learning_rate=0.03,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
        )
    except Exception as exc:
        model = GradientBoostingRegressor(random_state=42)
        status = "fallback"
        error = f"XGBoost unavailable, used GradientBoostingRegressor fallback: {exc}"

    model.fit(x_train, y_train)
    predicted = np.asarray(model.predict(x_test), dtype=float)
    return {
        "name": "xgboost",
        "status": status,
        "error": error,
        "metrics": _metric_payload(actual, predicted),
        "forecast": _forecast_records(test_df, predicted),
        "model": {
            "estimator": model,
            "feature_columns": feature_columns,
        },
    }


def _train_arima(train_df: pd.DataFrame, test_df: pd.DataFrame) -> Dict[str, Any]:
    actual = test_df["value"].to_numpy(dtype=float)
    status = "ok"
    error = None
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        model = SARIMAX(
            train_df["value"].astype(float),
            order=(1, 1, 1),
            seasonal_order=(1, 0, 1, 5),
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        result = model.fit(disp=False)
        forecast_result = result.get_forecast(steps=len(test_df))
        predicted = forecast_result.predicted_mean.to_numpy(dtype=float)
        interval = forecast_result.conf_int(alpha=0.05).to_numpy(dtype=float)
        lower = interval[:, 0]
        upper = interval[:, 1]
        model_payload: Any = result
    except Exception as exc:
        rolling_value = float(train_df["value"].tail(7).mean())
        predicted = np.full(len(test_df), rolling_value, dtype=float)
        residual_std = float(train_df["value"].tail(30).std() or 0.0)
        lower = predicted - 1.96 * residual_std
        upper = predicted + 1.96 * residual_std
        model_payload = {"kind": "rolling_mean_fallback", "window": 7, "residual_std": residual_std}
        status = "fallback"
        error = f"ARIMA/SARIMA unavailable or failed: {exc}"

    return {
        "name": "arima_sarima",
        "status": status,
        "error": error,
        "metrics": _metric_payload(actual, predicted),
        "forecast": _forecast_records(test_df, predicted, lower, upper),
        "model": model_payload,
    }


def _next_forecast_from_result(winner: Dict[str, Any], full_df: pd.DataFrame) -> Dict[str, Any]:
    last_date = pd.Timestamp(full_df["date"].max())
    forecast_for = _next_business_day(last_date)
    forecast_records = winner["forecast"]
    last_forecast = forecast_records[-1]
    recent_values = full_df["value"].tail(7).to_numpy(dtype=float)
    drift = float(np.mean(np.diff(recent_values))) if len(recent_values) > 1 else 0.0
    value = float(full_df["value"].iloc[-1] + drift)
    band = abs(float(last_forecast["upper"]) - float(last_forecast["lower"])) / 2
    if not math.isfinite(band) or band == 0:
        band = float(full_df["value"].tail(30).std() or 0.002)
    return {
        "currency": settings.app_currency,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "forecast_for": forecast_for.date().isoformat(),
        "model": winner["name"],
        "value": value,
        "confidence_interval": {
            "lower": value - band,
            "upper": value + band,
        },
    }


def train_models() -> Dict[str, Any]:
    ensure_project_dirs()
    full_df = load_rates_df().sort_values("date").reset_index(drop=True)
    train_df, test_df = _split_data(full_df)

    results = [
        _train_prophet(train_df, test_df),
        _train_xgboost(pd.concat([train_df, test_df], ignore_index=True), train_df, test_df),
        _train_arima(train_df, test_df),
    ]
    winner = min(results, key=lambda item: (item["metrics"]["mae"], item["metrics"]["rmse"]))

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_payload = {
        "id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "currency": settings.app_currency,
        "training_start": TRAINING_START.date().isoformat(),
        "test_size": TEST_SIZE,
        "test_range": {
            "start": pd.Timestamp(test_df["date"].min()).date().isoformat(),
            "end": pd.Timestamp(test_df["date"].max()).date().isoformat(),
        },
        "winner": winner["name"],
        "models": {
            result["name"]: {
                "status": result["status"],
                "error": result["error"],
                "metrics": result["metrics"],
            }
            for result in results
        },
    }

    forecast_history = {
        "currency": settings.app_currency,
        "model": winner["name"],
        "records": winner["forecast"],
    }
    latest_forecast = _next_forecast_from_result(winner, full_df)

    write_json(latest_run_path(), run_payload)
    write_json(forecast_history_path(), forecast_history)
    write_json(latest_forecast_path(), latest_forecast)
    joblib.dump(
        {
            "winner": winner["name"],
            "model": winner["model"],
            "created_at": run_payload["created_at"],
        },
        winner_model_path(),
    )
    return {
        "run": run_payload,
        "latest_forecast": latest_forecast,
        "forecast_history": forecast_history,
    }


def get_latest_run(limit: int = 1) -> Dict[str, Any]:
    run = read_json(latest_run_path(), default=None)
    return {"runs": [] if run is None else [run][:limit]}


def get_latest_forecast() -> Dict[str, Any]:
    forecast = read_json(latest_forecast_path(), default=None)
    if forecast is None:
        return {
            "currency": settings.app_currency,
            "status": "not_trained",
            "message": "No forecast exists yet. Run POST /api/train first.",
        }
    return forecast


def get_model_comparison() -> Dict[str, Any]:
    run = read_json(latest_run_path(), default=None)
    if run is None:
        return {"currency": settings.app_currency, "models": {}, "winner": None}
    return {
        "currency": settings.app_currency,
        "winner": run["winner"],
        "models": run["models"],
    }


def get_plot_data() -> Dict[str, Any]:
    return read_json(
        forecast_history_path(),
        default={"currency": settings.app_currency, "model": None, "records": []},
    )
