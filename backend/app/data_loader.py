from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .config import settings
from .storage import ensure_project_dirs, read_json, write_json


ROMANIAN_MONTHS = {
    "ian": 1,
    "ianuarie": 1,
    "feb": 2,
    "februarie": 2,
    "mar": 3,
    "mart": 3,
    "martie": 3,
    "apr": 4,
    "aprilie": 4,
    "mai": 5,
    "iun": 6,
    "iunie": 6,
    "iul": 7,
    "iulie": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "septembrie": 9,
    "oct": 10,
    "octombrie": 10,
    "nov": 11,
    "noiembrie": 11,
    "dec": 12,
    "decembrie": 12,
}


def _ascii_lower(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return ascii_value.strip().lower()


def parse_romanian_date(value: Any) -> pd.Timestamp:
    if isinstance(value, pd.Timestamp):
        return value.normalize()
    if isinstance(value, datetime):
        return pd.Timestamp(value.date())
    if isinstance(value, date):
        return pd.Timestamp(value)

    text = str(value).strip()
    iso_candidate = pd.to_datetime(text, errors="coerce")
    if not pd.isna(iso_candidate):
        return pd.Timestamp(iso_candidate).normalize()

    parts = text.replace(",", " ").split()
    if len(parts) < 3:
        raise ValueError(f"Cannot parse date value: {value!r}")

    day = int(re.sub(r"\D", "", parts[0]))
    month_key = _ascii_lower(parts[1]).replace(".", "")
    year = int(re.sub(r"\D", "", parts[2]))
    month = ROMANIAN_MONTHS.get(month_key)
    if not month:
        raise ValueError(f"Unsupported Romanian month in date value: {value!r}")
    return pd.Timestamp(year=year, month=month, day=day)


def _to_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if pd.isna(value):
        return default
    text = str(value).strip().replace("%", "").replace(",", ".")
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {column: column.strip().lower() for column in df.columns}
    df = df.rename(columns=renamed)
    required = {"date", "value"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

    df["date"] = df["date"].apply(parse_romanian_date)
    df["value"] = df["value"].apply(_to_float)

    if "change" in df.columns:
        df["change"] = df["change"].apply(_to_float)
    else:
        df["change"] = None

    if "percent" in df.columns:
        df["percent"] = df["percent"].apply(_to_float)
    else:
        df["percent"] = None

    df = df.dropna(subset=["date", "value"])
    df = df[["date", "value", "change", "percent"]]
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    return df.reset_index(drop=True)


def load_raw_csv(path: Optional[Path] = None) -> pd.DataFrame:
    csv_path = path or settings.resolved_data_csv_path
    if not csv_path.exists():
        raise FileNotFoundError(f"Data CSV not found: {csv_path}")
    df = pd.read_csv(csv_path)
    return _normalize_columns(df)


def _load_processed_updates() -> pd.DataFrame:
    payload = read_json(settings.processed_rates_path, default=[])
    if not payload:
        return pd.DataFrame(columns=["date", "value", "change", "percent"])
    df = pd.DataFrame(payload)
    return _normalize_columns(df)


def load_rates_df() -> pd.DataFrame:
    raw = load_raw_csv()
    updates = _load_processed_updates()
    if updates.empty:
        return raw
    combined = pd.concat([raw, updates], ignore_index=True)
    combined = combined.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    return combined.reset_index(drop=True)


def records_from_df(df: pd.DataFrame, descending: bool = True) -> List[Dict[str, Any]]:
    ordered = df.sort_values("date", ascending=not descending)
    records: List[Dict[str, Any]] = []
    for row in ordered.to_dict(orient="records"):
        records.append(
            {
                "date": pd.Timestamp(row["date"]).date().isoformat(),
                "value": float(row["value"]),
                "change": None if pd.isna(row.get("change")) else float(row.get("change")),
                "percent": None if pd.isna(row.get("percent")) else float(row.get("percent")),
            }
        )
    return records


def get_rates(limit: Optional[int] = None, target_date: Optional[str] = None) -> List[Dict[str, Any]]:
    df = load_rates_df()
    if target_date:
        wanted = pd.Timestamp(target_date).normalize()
        df = df[df["date"] == wanted]
    records = records_from_df(df, descending=True)
    if limit:
        return records[:limit]
    return records


def get_latest_rate() -> Dict[str, Any]:
    records = get_rates(limit=1)
    if not records:
        raise ValueError("No MXN rates are available.")
    return records[0]


def upsert_processed_rate(rate_date: str, value: float) -> Dict[str, Any]:
    ensure_project_dirs()
    df = load_rates_df()
    timestamp = pd.Timestamp(rate_date).normalize()
    existing = df[df["date"] == timestamp]
    if not existing.empty:
        return {
            "updated": False,
            "rate": records_from_df(existing, descending=True)[0],
            "message": "The latest BNR rate already exists locally.",
        }

    previous = df[df["date"] < timestamp].tail(1)
    change = None
    percent = None
    if not previous.empty:
        previous_value = float(previous.iloc[0]["value"])
        change = value - previous_value
        percent = (change / previous_value) * 100 if previous_value else None

    updates = read_json(settings.processed_rates_path, default=[])
    record = {
        "date": timestamp.date().isoformat(),
        "value": float(value),
        "change": change,
        "percent": percent,
    }
    updates = [item for item in updates if item.get("date") != record["date"]]
    updates.append(record)
    write_json(settings.processed_rates_path, updates)
    return {
        "updated": True,
        "rate": record,
        "message": "The latest BNR rate was added to the local processed store.",
    }
