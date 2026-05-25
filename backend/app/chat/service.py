from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .providers import get_provider_chain
from .tools import execute_tool


SYSTEM_PROMPT = (
    "You are an intelligent chatbot for an MXN exchange-rate app. "
    "Answer in English. Be concise and use the provided tool data as the source of truth. "
    "If tool data is unavailable, say what the user should do next."
)


def _select_tool(message: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    text = message.lower()
    if any(word in text for word in ["scrape", "refresh", "update data", "update bnr", "actualizeaza", "actualizare"]):
        return "scrape_bnr_data", {}
    if any(word in text for word in ["train", "retrain", "training", "antreneaza"]):
        return "train_models", {}
    if any(word in text for word in ["compare", "comparison", "models", "model comparison", "best model"]):
        return "compare_models", {}
    if any(word in text for word in ["forecast", "prediction", "predict", "prognoza"]):
        return "get_latest_forecast", {}
    if any(word in text for word in ["latest run", "last run", "run"]):
        return "get_latest_training_run", {"limit": 1}
    if any(word in text for word in ["rate", "mxn", "peso", "exchange", "curs"]):
        return "get_rates", {"limit": 5}
    return None


def _fallback_answer(message: str, tool_name: Optional[str], data: Optional[Dict[str, Any]]) -> str:
    if tool_name == "get_rates" and data:
        rates = data.get("rates", [])
        if not rates:
            return "I could not find MXN rates in the local dataset."
        latest = rates[0]
        return f"The latest local MXN rate is {latest['value']:.4f} RON for {latest['date']}."

    if tool_name == "get_latest_forecast" and data:
        if data.get("status") == "not_trained":
            return data["message"]
        interval = data.get("confidence_interval", {})
        return (
            f"The latest MXN forecast for {data.get('forecast_for')} is {data.get('value'):.4f} RON "
            f"using {data.get('model')}. Confidence interval: "
            f"{interval.get('lower'):.4f} to {interval.get('upper'):.4f}."
        )

    if tool_name == "compare_models" and data:
        winner = data.get("winner")
        if not winner:
            return "No model comparison is available yet. Run training first."
        return f"The current winning model is {winner}. You can see the full metrics in the model comparison panel."

    if tool_name == "get_latest_training_run" and data:
        runs = data.get("runs", [])
        if not runs:
            return "No training run exists yet. Run training first."
        run = runs[0]
        return f"The latest training run is {run['id']}. Winning model: {run['winner']}."

    if tool_name == "scrape_bnr_data" and data:
        return data.get("message", "BNR data update completed.")

    if tool_name == "train_models" and data:
        run = data.get("run", {})
        return f"Training completed. Winning model: {run.get('winner')}."

    return (
        "I can help with MXN BNR rates, forecasts, model comparisons, data refreshes, and training. "
        "Ask for one of those actions."
    )


async def chat(message: str) -> Dict[str, Any]:
    selected = _select_tool(message)
    tool_calls: List[Dict[str, Any]] = []
    tool_data: Optional[Dict[str, Any]] = None
    tool_name: Optional[str] = None

    if selected:
        tool_name, params = selected
        tool_calls.append({"tool": tool_name, "params": params})
        tool_data = execute_tool(tool_name, params)

    for provider in get_provider_chain():
        if not provider.is_configured():
            continue
        try:
            answer = await provider.complete(SYSTEM_PROMPT, message, tool_data)
            return {
                "answer": answer,
                "provider": provider.name,
                "tool_calls": tool_calls,
                "data": tool_data,
            }
        except Exception:
            continue

    return {
        "answer": _fallback_answer(message, tool_name, tool_data),
        "provider": "deterministic-fallback",
        "tool_calls": tool_calls,
        "data": tool_data,
    }
