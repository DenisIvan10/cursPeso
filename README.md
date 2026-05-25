# MXN BNR Exchange App

Local-first React + FastAPI app for the MXN exchange rate published by BNR.

## What is included

- MXN-only CSV loading and normalization.
- Latest local row validation against the official BNR XML feed.
- Forecasting pipeline with Prophet, XGBoost, and ARIMA/SARIMA adapters.
- Graceful fallback models when optional ML packages are not installed.
- FastAPI backend on `http://localhost:7772`.
- React dashboard with rates, latest forecast, model comparison, and Plotly chart.
- Bottom-right chatbot widget.
- Backend-mediated tool registry for chatbot actions.
- OpenAI primary, Gemini secondary, and Ollama third provider adapters.

## Project structure

```text
cursPeso/
|-- backend/
|   |-- app/
|   |   |-- chat/
|   |   |-- bnr_client.py
|   |   |-- config.py
|   |   |-- data_loader.py
|   |   |-- main.py
|   |   |-- model_pipeline.py
|   |   |-- schemas.py
|   |   `-- storage.py
|   `-- requirements.txt
|-- frontend/
|   |-- src/
|   |-- index.html
|   `-- package.json
|-- data/
|   |-- raw/
|   `-- processed/
|-- outputs/
|   |-- models/
|   `-- reports/
|-- .env.example
|-- .gitignore
`-- README.md
```

## Backend setup

From the project root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 7772 --reload
```

For the full Prophet, XGBoost, and ARIMA/SARIMA model competition, install the optional ML extras:

```powershell
pip install -r requirements-ml-extra.txt
```

If Prophet installs but falls back with a Stan backend error, install CmdStan:

```powershell
python -c "import cmdstanpy; cmdstanpy.install_cmdstan()"
```

That step can take a while on Windows and may require a working C++ toolchain.

API docs:

```text
http://localhost:7772/docs
```

## Frontend setup

From the project root:

```powershell
cd frontend
npm install
npm run dev
```

## Data

The attached CSV is expected at:

```text
data/raw/date_converted.csv
```

The app normalizes these CSV columns:

```text
Date,Value,Change,Percent
```

into:

```text
date,value,change,percent
```

The latest attached CSV row was verified against the official BNR XML feed:

```text
2026-05-15 MXN = 0.2576
```

## LLM configuration

Create a local `.env` file from `.env.example`.

Recommended provider order:

```text
openai,gemini,ollama
```

The frontend never calls LLM providers directly. Chat requests go to:

```text
POST /api/chat
```

The backend chooses the provider, validates tool calls, executes tools, and returns the final answer.

If no LLM provider is configured, the app still works with deterministic tool routing for core MXN actions.

## Key endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/rates` | Return MXN rates |
| GET | `/api/forecast/latest` | Return the latest forecast |
| GET | `/api/runs?limit=1` | Return latest training run |
| GET | `/api/models/compare` | Return model comparison metrics |
| GET | `/api/plot-data` | Return actual vs forecast chart data |
| POST | `/api/scrape` | Fetch latest BNR XML rate and update local processed data |
| POST | `/api/train` | Train/evaluate models |
| POST | `/api/chat` | Chatbot endpoint |

## Notes

- GitHub publishing is intentionally not configured yet.
- `Prophet`, `xgboost`, and `statsmodels` are optional ML extras. The app has fallbacks so the backend can remain usable if a heavy optional package fails to install.
- For MVP, scraping is manual and local-only.
