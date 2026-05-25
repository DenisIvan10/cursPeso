# Demo Steps - MXN BNR Exchange App

## 1. Start the Backend

Open a PowerShell terminal:

```powershell
cd C:\OwnProjects\cursPeso\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 7772 --reload
```

Open the API documentation:

```text
http://127.0.0.1:7772/docs
```

Explain:

- The backend is built with FastAPI.
- It exposes the data, forecast, training, scraping, and chatbot endpoints.
- The main currency scope is MXN only.

---

## 2. Start the Frontend

Open a second PowerShell terminal:

```powershell
cd C:\OwnProjects\cursPeso\frontend
npm run dev
```

Open the frontend:

```text
http://127.0.0.1:5173
```

Explain:

- The frontend is built with React.
- It displays the MXN dashboard.
- It includes a bottom-right chatbot widget.

---

## 3. Show the Data Source

Explain:

- The app uses the CSV file copied into:

```text
C:\OwnProjects\cursPeso\data\raw\date_converted.csv
```

- The CSV originally has these columns:

```text
Date, Value, Change, Percent
```

- The backend normalizes them internally to:

```text
date, value, change, percent
```

- The latest verified MXN value is:

```text
2026-05-15 = 0.2576 RON
```

---

## 4. Validate Against BNR

In the frontend, use the validation button if available.

Or open this endpoint:

```text
http://127.0.0.1:7772/api/rates/validate
```

Explain:

- The app checks the latest local CSV value against the official BNR XML feed.
- Official source:

```text
https://www.bnr.ro/nbrfxrates.xml
```

- The latest local row matches the official BNR value.

---

## 5. Show the Main API Endpoints

Open FastAPI docs:

```text
http://127.0.0.1:7772/docs
```

Show these endpoints:

```text
GET  /api/health
GET  /api/rates
GET  /api/forecast/latest
GET  /api/runs?limit=1
GET  /api/models/compare
GET  /api/plot-data
POST /api/train
POST /api/scrape
POST /api/chat
```

Explain:

- `/api/rates` returns the MXN exchange-rate list.
- `/api/train` trains and evaluates the forecasting models.
- `/api/models/compare` returns MAE, RMSE, and MAPE for each model.
- `/api/chat` powers the chatbot.

---

## 6. Train the Models

In the frontend, click:

```text
Train models
```

Or call:

```text
POST http://127.0.0.1:7772/api/train
```

Explain:

- The app splits the data chronologically.
- The last 14 observations are used as the test set.
- The previous data is used for training.
- The app compares three model families:
  - Prophet
  - XGBoost
  - ARIMA/SARIMA

---

## 7. Explain Feature Engineering

Explain that the ML model uses derived features:

- previous value `t-1`
- previous value `t-2`
- previous value `t-3`
- day of week
- month
- 7-day moving average
- 14-day moving average

These features help the model learn the short-term behavior of the MXN/RON exchange rate.

---

## 8. Explain Model Evaluation

Show the model comparison table in the frontend or call:

```text
http://127.0.0.1:7772/api/models/compare
```

Explain the metrics:

- MAE: average absolute error in RON.
- RMSE: penalizes larger errors more strongly.
- MAPE: average percentage error.

Current result:

```text
Winner: XGBoost
```

Note:

- XGBoost and ARIMA/SARIMA run successfully.
- Prophet is integrated, but on Windows it needs CmdStan for the full backend.
- If CmdStan is not installed, the app uses a fallback so the pipeline remains functional.

---

## 9. Show the Plotly Forecast Chart

In the frontend, show the chart section.

Explain:

- The green/official line represents the real MXN BNR rate.
- The forecast line represents the winning model prediction.
- The shaded area represents the confidence interval.

---

## 10. Demonstrate the Chatbot

Open the bottom-right chat widget.

Try these questions:

```text
What is the latest MXN rate?
```

```text
What is the latest forecast?
```

```text
Compare the models.
```

```text
Update BNR data.
```

Explain:

- The chatbot does not only answer textually.
- It can call backend tools.
- Tool execution is handled by the backend, not directly by the frontend.

Tool examples:

```text
get_rates
get_latest_forecast
compare_models
scrape_bnr_data
train_models
```

---

## 11. Final Explanation

Use this short summary:

```text
This application forecasts the MXN/RON exchange rate published by BNR.
It loads historical data from CSV, validates the latest value against the official BNR XML feed,
trains and compares forecasting models, selects the best model using MAE/RMSE/MAPE,
and displays the results in a React dashboard with a Plotly chart and a tool-enabled chatbot.
```

---

## 12. Known Limitations

- Prophet may require CmdStan on Windows.
- The chatbot can run in deterministic fallback mode if no OpenAI/Gemini/Ollama credentials are configured.
- GitHub publishing is not part of the current local demo.
- The app is currently designed for MXN only.
