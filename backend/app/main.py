from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .bnr_client import scrape_latest_bnr_rate, validate_latest_local_rate
from .chat.service import chat
from .config import settings
from .data_loader import get_rates
from .model_pipeline import get_latest_forecast, get_latest_run, get_model_comparison, get_plot_data, train_models
from .schemas import ChatRequest, ChatResponse, RatesResponse
from .storage import ensure_project_dirs


app = FastAPI(title="MXN BNR Exchange API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    ensure_project_dirs()


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "currency": settings.app_currency,
        "data_csv_path": str(settings.resolved_data_csv_path),
    }


@app.get("/api/rates", response_model=RatesResponse)
def rates(
    limit: Optional[int] = Query(default=30, ge=1, le=5000),
    date: Optional[str] = Query(default=None),
) -> dict:
    return {
        "currency": settings.app_currency,
        "rates": get_rates(limit=limit, target_date=date),
    }


@app.get("/api/rates/validate")
def validate_rates() -> dict:
    return validate_latest_local_rate()


@app.get("/api/forecast/latest")
def latest_forecast() -> dict:
    return get_latest_forecast()


@app.get("/api/runs")
def runs(limit: int = Query(default=1, ge=1, le=50)) -> dict:
    return get_latest_run(limit=limit)


@app.get("/api/models/compare")
def models_compare() -> dict:
    return get_model_comparison()


@app.get("/api/plot-data")
def plot_data() -> dict:
    return get_plot_data()


@app.post("/api/scrape")
def scrape() -> dict:
    return scrape_latest_bnr_rate()


@app.post("/api/train")
def train() -> dict:
    return train_models()


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> dict:
    return await chat(request.message)
