from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import settings


def ensure_project_dirs() -> None:
    for path in [
        settings.project_root / "data" / "raw",
        settings.project_root / "data" / "processed",
        settings.reports_dir,
        settings.models_dir,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)


def latest_run_path() -> Path:
    return settings.reports_dir / "latest_run.json"


def forecast_history_path() -> Path:
    return settings.reports_dir / "forecast_history.json"


def latest_forecast_path() -> Path:
    return settings.reports_dir / "latest_forecast.json"


def winner_model_path() -> Path:
    return settings.models_dir / "winner.joblib"
