from __future__ import annotations

from typing import Any, Callable, Dict

from ..bnr_client import scrape_latest_bnr_rate
from ..data_loader import get_rates
from ..model_pipeline import get_latest_forecast, get_latest_run, get_model_comparison, train_models


ToolHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


def _get_rates(params: Dict[str, Any]) -> Dict[str, Any]:
    limit = params.get("limit")
    target_date = params.get("date")
    return {"rates": get_rates(limit=limit, target_date=target_date)}


def _get_latest_forecast(params: Dict[str, Any]) -> Dict[str, Any]:
    return get_latest_forecast()


def _get_latest_training_run(params: Dict[str, Any]) -> Dict[str, Any]:
    limit = int(params.get("limit") or 1)
    return get_latest_run(limit=limit)


def _compare_models(params: Dict[str, Any]) -> Dict[str, Any]:
    return get_model_comparison()


def _scrape_bnr_data(params: Dict[str, Any]) -> Dict[str, Any]:
    return scrape_latest_bnr_rate()


def _train_models(params: Dict[str, Any]) -> Dict[str, Any]:
    return train_models()


TOOL_REGISTRY: Dict[str, ToolHandler] = {
    "get_rates": _get_rates,
    "get_latest_forecast": _get_latest_forecast,
    "get_latest_training_run": _get_latest_training_run,
    "compare_models": _compare_models,
    "scrape_bnr_data": _scrape_bnr_data,
    "train_models": _train_models,
}


def execute_tool(name: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if name not in TOOL_REGISTRY:
        raise ValueError(f"Unknown chatbot tool: {name}")
    return TOOL_REGISTRY[name](params or {})
