# Implementation Prompt - MXN BNR Exchange App

## Document Status

- Status: draft for review and approval.
- Language: English.
- Implementation must not start until the user explicitly approves this document.
- Main goal: build a local-first exchange-rate app for the MXN exchange rate published by BNR.
- Methodology: Agile, with epics, backlog items, sprints, acceptance criteria, and approval checkpoints.

---

## Implementation Rules for the Coding Agent

You are a coding agent that will implement the application described in this document only after explicit user approval.

Mandatory rules:

1. Do not change the functional information provided by the user.
2. Keep the scope focused on MXN only.
3. Start from scratch in the target local project folder.
4. Ask for approval before implementation.
5. If a requirement is unknown, use the recommendation documented here or ask the user before coding if the decision has security, cost, or architecture impact.
6. Follow Agile delivery:
   - define epics and backlog items;
   - implement in small sprint-sized increments;
   - validate each sprint with acceptance criteria;
   - stop for user confirmation at approval checkpoints.
7. Keep all code, UI text, documentation, comments, and task names in English.
8. The app must work locally first. GitHub publication is a future/manual step handled by the user later.

---

## Confirmed User Decisions

| Topic | Decision |
|---|---|
| Target project folder | `C:\OwnProjects\cursPeso` |
| Frontend | React |
| Backend | FastAPI or Flask; recommendation: FastAPI |
| Data source file | `C:\Users\Desktop\date_converted.csv` |
| CSV value column | User says `value`; attached CSV has `Value`, so implementation should normalize it to `value` internally |
| Currency scope | MXN only |
| Existing app | None; start from zero |
| Chat widget placement | Bottom-right only |
| LLM providers | OpenAI as primary, Gemini as secondary, Ollama/local as third option |
| Tool-call execution architecture | Unknown; recommendation: backend-mediated tool execution |
| Scrape auth | Unknown; recommendation: local-only in MVP, optional admin token later |
| Scrape scheduling | Unknown; recommendation: manual scrape in MVP, scheduled job later if needed |
| Model-run metrics endpoint | Unknown; define the response contract during backend implementation |
| Optuna | Use later only if useful; not required for MVP baseline |
| GitHub | Public repository later, created by user |
| Git usage now | Local work only, no Git setup for now |

---

## Objective

Build an MXN BNR exchange-rate application that can:

- load and validate historical MXN exchange-rate data;
- preprocess and feature-engineer the time series;
- train and compare three forecasting models for next-day prediction, Z+1;
- choose and persist the best model;
- expose data, forecasts, runs, and scraping through an API;
- provide a React frontend with a bottom-right chatbot widget;
- use an LLM chatbot that can call application functions as tools;
- display a Plotly forecasting dashboard with actual values, forecast values, and a confidence interval.

---

## Verified CSV Context

Attached CSV:

```text
C:\Users\divan\OneDrive - ENDAVA\Desktop\date_converted.csv
```

Observed structure:

```csv
Date,Value,Change,Percent
15 Mai 2026,0.2576,-0.0010,-0.39 %
14 Mai 2026,0.2586,+0.0006,0.23 %
13 Mai 2026,0.2580,+0.0007,0.27 %
```

Observed facts:

- File size: about 151 KB.
- Total lines: 4,333 including the header.
- Data rows: 4,332.
- Date order: newest first.
- Latest local row: `15 Mai 2026`, value `0.2576`.
- Oldest local row observed: `3 Mart. 2009`, value `0.2219`.
- CSV columns: `Date`, `Value`, `Change`, `Percent`.
- Internal normalized columns should be: `date`, `value`, `change`, `percent`.

Official BNR spot-check:

- Official BNR XML feed URL: `https://www.bnr.ro/nbrfxrates.xml`
- BNR publishing date checked: `2026-05-15`.
- Official MXN rate checked: `0.2576`.
- Result: the attached CSV latest MXN value matches the official BNR daily XML feed for `2026-05-15`.

Implementation requirement:

- Add a validation task that compares the local CSV latest MXN row against the official BNR XML feed.
- If a yearly BNR XML archive is used later, compare more than one date, not only the latest row.
- Do not depend on third-party exchange-rate websites as the source of truth; use BNR XML as the authoritative source.

---

## Recommended Tech Stack

### Frontend

- React.
- Vite is recommended for a simple local development setup.
- Plotly.js or `react-plotly.js` for charts.
- Bottom-right chat widget implemented as a reusable React component.

### Backend

- FastAPI is recommended over Flask because:
  - the project is Python-heavy due to ML workflows;
  - FastAPI provides OpenAPI docs by default;
  - Pydantic is useful for API contracts and tool schemas;
  - async HTTP integrations for LLM providers are straightforward.

### ML and Data

- Python.
- pandas for loading and preprocessing.
- scikit-learn metrics for MAE, RMSE, and MAPE.
- Prophet for model 1.
- XGBoost for model 2.
- statsmodels or pmdarima for ARIMA/SARIMA.
- joblib/pickle or model-specific persistence for saving the winner.

### LLM Providers

Provider priority:

1. OpenAI - primary.
2. Gemini - fallback/secondary.
3. Ollama - local fallback/third option.

Recommendation:

- The frontend should not call LLM provider APIs directly.
- The backend should own LLM calls, API keys, tool registry, and tool execution.
- The frontend should send chat messages to the backend and render the final assistant response.

---

## Source Requirement 1 - Forecasting Models

The app must process historical data, train, evaluate, and test three competing models for next-day exchange-rate forecasting, Z+1, using the extracted CSV time series.

### Data Preprocessing

- Load historical data from CSV into a dataframe.
- Clean the data:
  - convert data types;
  - parse the `Date` column;
  - normalize `Value` into internal field `value`;
  - set the date as index where useful;
  - handle missing values, including weekends and Romanian legal holidays if needed.

### Train / Test Split

- Test set: the last 14 chronological days in the dataset.
- Train set: all previous data.
- Original source requirement says train data starts from `22/02/2020` until one day before the test set.
- Because the attached CSV contains data back to 2009, implementation must decide whether to:
  - filter training to start at `2020-02-22`, matching the original requirement; or
  - use all available history as an optional experiment.
- Default implementation should respect the original requirement and use data from `2020-02-22`.

### Feature Engineering

Generate derived columns, especially for XGBoost:

- lag features:
  - `t-1`;
  - `t-2`;
  - `t-3`;
- calendar features:
  - day of week;
  - month;
- moving averages:
  - 7-day moving average;
  - 14-day moving average.

### Models

Train and compare three time-series approaches:

1. Prophet
   - Useful for financial time series.
   - Handles missing calendar dates naturally.
   - Supports weekly/yearly seasonality.
   - Provides uncertainty intervals.

2. XGBoost Regressor
   - Uses engineered features.
   - Uses historical lag values to infer the next value.
   - Should be trained on tabular features derived from the time series.

3. ARIMA / SARIMA
   - Classical statistical model for univariate time-series forecasting.
   - Uses autocorrelation and seasonality properties from the BNR MXN series.

### Evaluation Report

Evaluate all three models on the same 14-day test set and produce a table with:

- MAE - Mean Absolute Error, in RON.
- RMSE - Root Mean Squared Error.
- MAPE - Mean Absolute Percentage Error.

Winner selection:

- The model with the lowest MAE/RMSE is declared the winner.
- If MAE and RMSE disagree, choose the model with the best overall stability and document the reason.

### Persist the Best Model

Persist the winning model locally using the appropriate format:

- `joblib`;
- `.pkl`;
- Prophet-specific serialization;
- or another model-specific format.

The persisted model must be loadable for Z+1 estimation without retraining the full pipeline.

### Plotly Forecasting Dashboard

The winning model must generate a replay forecast for the 14-day test set.

The Plotly chart must contain:

- actual official MXN rate line;
- forecast line from the winning model;
- upper and lower confidence interval, displayed as a shaded band.

---

## Source Requirement 2 - API

The local API should run at:

```text
http://localhost:7772
```

Required API endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/rates` | Return the list of MXN rates |
| GET | `/api/forecast/latest` | Return the latest/best forecast |
| GET | `/api/runs?limit=1` | Return the latest training run |
| POST | `/api/scrape` | Scrape/update BNR data |

Recommended additional endpoints for the new app:

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/train` | Trigger model training manually |
| GET | `/api/models/compare` | Return model comparison metrics |
| POST | `/api/chat` | Send a user message to the backend chatbot orchestrator |
| GET | `/api/health` | Health check |

---

## Source Requirement 3 - LLM Chatbot With Tools

### Goal

Add a chatbot based on an LLM model that uses application functions as tools.

### Chatbot Role

The chatbot is an intelligent assistant that answers questions about MXN exchange rates.

### Chatbot Behavior

- When the user asks for a rate, search the rates list.
- When the user asks for a forecast, search the forecast data.
- When the user asks for a comparison, search the model/run data.
- When the user asks to update data, call the BNR scrape function.

### Response Format

Normal chat:

- Return a normal natural-language response.

Tool call:

- Return JSON containing the function/tool to call and its parameters.

Example internal tool-call shape:

```json
{
  "tool": "get_rates",
  "params": {
    "currency": "MXN"
  }
}
```

Recommendation:

- The raw JSON tool call should be an internal backend contract.
- The user should usually see a natural-language answer unless the app is in debug mode.

### Frontend Task

- Add chatbot code in the frontend.
- Add the chat widget on the main page.
- Position the widget in the bottom-right corner.
- Transform as many relevant application functions as possible into LLM tools and add them to a registry so the LLM can use them automatically.

---

## LLM Tool Registry

Initial tool registry:

| Tool | Backend action | Used when | Parameters |
|---|---|---|---|
| `get_rates` | `GET /api/rates` | User asks for MXN rates or a specific date | `date`, `limit` |
| `get_latest_forecast` | `GET /api/forecast/latest` | User asks for the latest forecast | none or `horizon` |
| `get_latest_training_run` | `GET /api/runs?limit=1` | User asks about latest training or model results | `limit` |
| `compare_models` | `GET /api/models/compare` | User asks to compare models | none |
| `scrape_bnr_data` | `POST /api/scrape` | User asks to update BNR data | `force` |
| `train_models` | `POST /api/train` | User asks to retrain models | optional config |

Tool execution recommendation:

- User message goes to `POST /api/chat`.
- Backend calls the selected LLM provider.
- LLM returns either a direct answer or a tool call.
- Backend validates the tool call against the registry.
- Backend executes the local function/API action.
- Backend sends the tool result back to the LLM if needed.
- Backend returns the final answer to the React frontend.

---

## Agile Backlog

### Epic 1 - Project Setup

- Task 1.1: Create project structure in `C:\OwnProjects\cursPeso`.
- Task 1.2: Create FastAPI backend scaffold.
- Task 1.3: Create React frontend scaffold.
- Task 1.4: Configure local ports:
  - API: `7772`;
  - frontend: recommended Vite default or another available port.
- Task 1.5: Add environment file examples for API keys and provider settings.

### Epic 2 - Data Loading and Validation

- Task 2.1: Load `date_converted.csv`.
- Task 2.2: Normalize columns to `date`, `value`, `change`, `percent`.
- Task 2.3: Parse Romanian month names from the CSV.
- Task 2.4: Sort data chronologically.
- Task 2.5: Validate latest local row against BNR XML.
- Task 2.6: Store normalized MXN data locally.

### Epic 3 - Preprocessing and Feature Engineering

- Task 3.1: Clean numeric fields.
- Task 3.2: Handle missing dates and missing values.
- Task 3.3: Apply train/test split with last 14 chronological observations as test.
- Task 3.4: Apply default training start date `2020-02-22`.
- Task 3.5: Generate lag features.
- Task 3.6: Generate day-of-week and month features.
- Task 3.7: Generate 7-day and 14-day moving averages.

### Epic 4 - Forecasting Models

- Task 4.1: Implement Prophet training and prediction.
- Task 4.2: Implement XGBoost training and prediction.
- Task 4.3: Implement ARIMA/SARIMA training and prediction.
- Task 4.4: Standardize model interfaces.
- Task 4.5: Run all models on the same train/test split.

### Epic 5 - Evaluation and Persistence

- Task 5.1: Calculate MAE.
- Task 5.2: Calculate RMSE.
- Task 5.3: Calculate MAPE.
- Task 5.4: Generate model comparison report.
- Task 5.5: Select the winning model.
- Task 5.6: Save the winning model locally.
- Task 5.7: Load the winning model for Z+1 forecast.

### Epic 6 - API

- Task 6.1: Implement `GET /api/health`.
- Task 6.2: Implement `GET /api/rates`.
- Task 6.3: Implement `GET /api/forecast/latest`.
- Task 6.4: Implement `GET /api/runs?limit=1`.
- Task 6.5: Implement `POST /api/scrape`.
- Task 6.6: Implement `POST /api/train`.
- Task 6.7: Implement `GET /api/models/compare`.
- Task 6.8: Implement `POST /api/chat`.

### Epic 7 - Plotly Dashboard

- Task 7.1: Create frontend dashboard layout.
- Task 7.2: Display latest MXN rate.
- Task 7.3: Display latest forecast.
- Task 7.4: Display latest training run.
- Task 7.5: Render Plotly actual-vs-forecast chart.
- Task 7.6: Render confidence interval as shaded area.

### Epic 8 - LLM Chatbot

- Task 8.1: Create bottom-right React chat widget.
- Task 8.2: Add backend chatbot orchestrator.
- Task 8.3: Add OpenAI provider adapter.
- Task 8.4: Add Gemini provider adapter.
- Task 8.5: Add Ollama provider adapter.
- Task 8.6: Add provider priority and fallback logic.
- Task 8.7: Define tool schemas.
- Task 8.8: Implement tool registry and tool execution.
- Task 8.9: Test user intents:
  - ask for MXN rate;
  - ask for latest forecast;
  - ask for model comparison;
  - ask to update BNR data;
  - ask a normal general question.

### Epic 9 - Local QA and Documentation

- Task 9.1: Add README with setup and run instructions.
- Task 9.2: Add `.env.example`.
- Task 9.3: Add `.gitignore`.
- Task 9.4: Run backend checks.
- Task 9.5: Run frontend checks.
- Task 9.6: Test full local workflow.

### Epic 10 - Future GitHub Publication

- Task 10.1: User creates public GitHub repository.
- Task 10.2: Initialize Git when the user is ready.
- Task 10.3: Connect remote.
- Task 10.4: Push local project.

This epic is out of current scope because the user said to work locally without Git for now.

---

## Sprint Plan

### Sprint 0 - Approval and Workspace Preparation

Goal: confirm this document and prepare the implementation workspace.

Tasks:

- Review this implementation prompt.
- Confirm FastAPI as backend framework.
- Confirm backend-mediated tool execution.
- Confirm that writing to `C:\OwnProjects\cursPeso` is allowed when implementation starts.
- Confirm local-only Git-free workflow.

Acceptance criteria:

- User approves the document.
- User confirms implementation can start.
- Target folder decision is final.

### Sprint 1 - Project Skeleton and Data Pipeline

Goal: create the app skeleton and load/validate MXN data.

Tasks:

- Create backend scaffold.
- Create frontend scaffold.
- Load and parse CSV.
- Normalize columns.
- Validate latest CSV row against BNR XML.

Acceptance criteria:

- Backend starts locally on port `7772`.
- Frontend starts locally.
- CSV loads successfully.
- Latest MXN CSV value is validated against official BNR XML.

### Sprint 2 - Forecasting Pipeline

Goal: build preprocessing, feature engineering, model training, and evaluation.

Tasks:

- Train/test split.
- Feature engineering.
- Prophet model.
- XGBoost model.
- ARIMA/SARIMA model.
- MAE/RMSE/MAPE report.
- Winning model persistence.

Acceptance criteria:

- All three models run on the same test set.
- Evaluation report is generated.
- Winning model is saved locally.

### Sprint 3 - API and Dashboard

Goal: expose backend data and show it in React.

Tasks:

- Implement API endpoints.
- Build React dashboard.
- Add Plotly chart.
- Show rates, forecast, and latest run.

Acceptance criteria:

- API endpoints return structured JSON.
- Dashboard displays latest rate and forecast.
- Plotly chart includes actual line, forecast line, and confidence interval.

### Sprint 4 - Chatbot and Tool Registry

Goal: add the LLM chatbot with automatic tool usage.

Tasks:

- Add bottom-right chat widget.
- Add backend chat endpoint.
- Add OpenAI primary provider.
- Add Gemini secondary provider.
- Add Ollama local fallback provider.
- Add tool registry.
- Connect tools to app functions.

Acceptance criteria:

- Chat widget appears bottom-right.
- User can ask for an MXN rate.
- User can ask for the latest forecast.
- User can ask to compare models.
- User can ask to update BNR data.
- Chatbot returns natural-language answers after tool execution.

### Sprint 5 - QA and Documentation

Goal: make the local app usable and documented.

Tasks:

- Write README.
- Add `.env.example`.
- Add `.gitignore`.
- Run final checks.
- Document known limitations.

Acceptance criteria:

- User can run the app locally from documentation.
- Sensitive values are not committed or hardcoded.
- Local workflow is stable.

---

## API Contracts - Draft

### `GET /api/rates`

Returns MXN rates.

Example response:

```json
{
  "currency": "MXN",
  "rates": [
    {
      "date": "2026-05-15",
      "value": 0.2576,
      "change": -0.0010,
      "percent": -0.39
    }
  ]
}
```

### `GET /api/forecast/latest`

Returns the latest forecast from the winning model.

Example response:

```json
{
  "currency": "MXN",
  "date": "2026-05-18",
  "forecast_for": "2026-05-19",
  "model": "xgboost",
  "value": 0.2581,
  "confidence_interval": {
    "lower": 0.2548,
    "upper": 0.2612
  }
}
```

### `GET /api/runs?limit=1`

Returns the latest training run.

Example response:

```json
{
  "runs": [
    {
      "id": "2026-05-18T09-30-00",
      "currency": "MXN",
      "winner": "xgboost",
      "metrics": {
        "prophet": {
          "mae": 0.0,
          "rmse": 0.0,
          "mape": 0.0
        },
        "xgboost": {
          "mae": 0.0,
          "rmse": 0.0,
          "mape": 0.0
        },
        "arima_sarima": {
          "mae": 0.0,
          "rmse": 0.0,
          "mape": 0.0
        }
      }
    }
  ]
}
```

### `POST /api/scrape`

Updates local BNR data.

Recommendation:

- MVP: manual trigger only.
- Later: optional scheduler.

### `POST /api/chat`

Receives a user chat message and returns an assistant answer.

Example request:

```json
{
  "message": "What is the latest MXN rate?"
}
```

Example response:

```json
{
  "answer": "The latest official BNR MXN rate is 0.2576 RON for 2026-05-15.",
  "tool_calls": [
    {
      "tool": "get_rates",
      "params": {
        "limit": 1
      }
    }
  ]
}
```

---

## Environment Variables - Draft

```text
OPENAI_API_KEY=
GEMINI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
LLM_PROVIDER_PRIORITY=openai,gemini,ollama
BNR_XML_URL=https://www.bnr.ro/nbrfxrates.xml
APP_CURRENCY=MXN
API_PORT=7772
```

---

## Definition of Done

A task is done only when:

- the implementation is in English;
- it works locally;
- it does not break existing completed flows;
- it is connected to a documented acceptance criterion;
- it is tested manually or automatically;
- it keeps MXN as the only currency scope;
- it avoids hardcoded secrets;
- it is documented if the user needs to run or configure it.

---

## Open Questions Before Implementation

These are the remaining questions. Recommendations are included so the implementation can move once the user approves.

1. Backend framework: confirm FastAPI as the final choice.
   - Recommendation: FastAPI.
2. Tool execution architecture: should the backend execute tools instead of the frontend?
   - Recommendation: yes, backend-mediated tool execution.
3. Scrape security: should `POST /api/scrape` be protected?
   - Recommendation: for local MVP, no auth; later add an admin token if exposed beyond localhost.
4. Scrape scheduling: should updates be manual only or scheduled?
   - Recommendation: manual in MVP, scheduled later.
5. Write access: implementation will target `C:\OwnProjects\cursPeso`.
   - Note: this path is outside the current Codex writable workspace, so filesystem approval may be required when implementation starts.
6. OpenAI model: which model should be used for the chatbot?
   - Recommendation: use a current cost-effective OpenAI chat model at implementation time and document it in `.env.example`.

---

## Approval Checkpoint

Implementation must start only after the user explicitly confirms:

```text
I approve this document and you can start implementation.
```

Until then, this file is only a planning and implementation prompt.
