import React, { useEffect, useMemo, useState } from "react";
import Plot from "react-plotly.js";
import { Activity, BrainCircuit, DatabaseZap, RefreshCcw, TrendingUp } from "lucide-react";
import { api } from "./api";
import ChatWidget from "./components/ChatWidget.jsx";

function formatNumber(value, digits = 4) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }
  return Number(value).toFixed(digits);
}

function StatusPill({ label, tone = "neutral" }) {
  return <span className={`status-pill status-pill--${tone}`}>{label}</span>;
}

function MetricTable({ comparison }) {
  const models = comparison?.models || {};
  const entries = Object.entries(models);
  if (!entries.length) {
    return <p className="muted">No model run is available yet. Start training to generate metrics.</p>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Model</th>
            <th>Status</th>
            <th>MAE</th>
            <th>RMSE</th>
            <th>MAPE</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([name, result]) => (
            <tr key={name}>
              <td>
                <strong>{name}</strong>
                {comparison.winner === name ? <StatusPill label="winner" tone="good" /> : null}
              </td>
              <td>{result.status}</td>
              <td>{formatNumber(result.metrics?.mae, 6)}</td>
              <td>{formatNumber(result.metrics?.rmse, 6)}</td>
              <td>{formatNumber(result.metrics?.mape, 4)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ForecastChart({ plotData }) {
  const records = plotData?.records || [];
  const chart = useMemo(() => {
    const dates = records.map((item) => item.date);
    return [
      {
        x: dates,
        y: records.map((item) => item.actual),
        mode: "lines+markers",
        name: "Official rate",
        line: { color: "#1f6f5b", width: 3 }
      },
      {
        x: dates,
        y: records.map((item) => item.forecast),
        mode: "lines+markers",
        name: "Forecast",
        line: { color: "#3454d1", width: 3 }
      },
      {
        x: [...dates, ...dates.slice().reverse()],
        y: [
          ...records.map((item) => item.upper),
          ...records.map((item) => item.lower).reverse()
        ],
        fill: "toself",
        fillcolor: "rgba(52, 84, 209, 0.14)",
        line: { color: "rgba(52, 84, 209, 0)" },
        hoverinfo: "skip",
        name: "95% interval",
        type: "scatter"
      }
    ];
  }, [records]);

  if (!records.length) {
    return <div className="empty-chart">Train the models to render the forecast chart.</div>;
  }

  return (
    <Plot
      data={chart}
      layout={{
        autosize: true,
        margin: { l: 48, r: 24, t: 18, b: 42 },
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        legend: { orientation: "h", y: -0.22 },
        xaxis: { gridcolor: "#e5ebf0" },
        yaxis: { gridcolor: "#e5ebf0", tickformat: ".4f" }
      }}
      config={{ displayModeBar: false, responsive: true }}
      className="plot"
      useResizeHandler
      style={{ width: "100%", height: "390px" }}
    />
  );
}

export default function App() {
  const [health, setHealth] = useState(null);
  const [rates, setRates] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [run, setRun] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [plotData, setPlotData] = useState(null);
  const [validation, setValidation] = useState(null);
  const [loadingAction, setLoadingAction] = useState("");
  const [error, setError] = useState("");

  async function loadDashboard() {
    setError("");
    try {
      const [healthData, ratesData, forecastData, runData, comparisonData, plotDataResponse] =
        await Promise.all([
          api.health(),
          api.rates(20),
          api.latestForecast(),
          api.latestRun(),
          api.compareModels(),
          api.plotData()
        ]);
      setHealth(healthData);
      setRates(ratesData.rates || []);
      setForecast(forecastData);
      setRun(runData.runs?.[0] || null);
      setComparison(comparisonData);
      setPlotData(plotDataResponse);
    } catch (err) {
      setError(err.message);
    }
  }

  async function runAction(name, action) {
    setLoadingAction(name);
    setError("");
    try {
      const result = await action();
      if (name === "validate") {
        setValidation(result);
      }
      await loadDashboard();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingAction("");
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  const latestRate = rates[0];

  return (
    <main className="app-shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">BNR reference rate</p>
          <h1>MXN Exchange Dashboard</h1>
        </div>
        <div className="topbar-actions">
          <button
            type="button"
            className="icon-button"
            title="Refresh dashboard"
            onClick={loadDashboard}
            disabled={Boolean(loadingAction)}
          >
            <RefreshCcw size={18} />
            <span>Refresh</span>
          </button>
          <button
            type="button"
            className="primary-button"
            title="Train forecasting models"
            onClick={() => runAction("train", api.train)}
            disabled={Boolean(loadingAction)}
          >
            <BrainCircuit size={18} />
            <span>{loadingAction === "train" ? "Training..." : "Train models"}</span>
          </button>
        </div>
      </section>

      {error ? <div className="alert alert--error">{error}</div> : null}

      <section className="summary-grid">
        <article className="summary-tile">
          <div className="tile-icon tile-icon--green">
            <TrendingUp size={22} />
          </div>
          <div>
            <p>Latest MXN rate</p>
            <strong>{latestRate ? `${formatNumber(latestRate.value)} RON` : "-"}</strong>
            <span>{latestRate?.date || "No rate loaded"}</span>
          </div>
        </article>
        <article className="summary-tile">
          <div className="tile-icon tile-icon--blue">
            <Activity size={22} />
          </div>
          <div>
            <p>Latest forecast</p>
            <strong>
              {forecast?.value ? `${formatNumber(forecast.value)} RON` : "Not trained"}
            </strong>
            <span>{forecast?.forecast_for || forecast?.message || "Run training first"}</span>
          </div>
        </article>
        <article className="summary-tile">
          <div className="tile-icon tile-icon--amber">
            <DatabaseZap size={22} />
          </div>
          <div>
            <p>Training run</p>
            <strong>{run?.winner || "No winner"}</strong>
            <span>{run?.id || "No run yet"}</span>
          </div>
        </article>
      </section>

      <section className="action-band">
        <div>
          <h2>Local data controls</h2>
          <p>Validate the latest CSV value against BNR XML or fetch the newest official MXN rate.</p>
        </div>
        <div className="action-buttons">
          <button
            type="button"
            className="secondary-button"
            onClick={() => runAction("validate", api.validateRates)}
            disabled={Boolean(loadingAction)}
          >
            {loadingAction === "validate" ? "Checking..." : "Validate BNR XML"}
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={() => runAction("scrape", api.scrape)}
            disabled={Boolean(loadingAction)}
          >
            {loadingAction === "scrape" ? "Updating..." : "Update BNR data"}
          </button>
        </div>
      </section>

      {validation ? (
        <section className="validation-line">
          <StatusPill label={validation.matches ? "BNR match" : "BNR mismatch"} tone={validation.matches ? "good" : "warn"} />
          <span>
            Local {validation.local?.date}: {formatNumber(validation.local?.value)} | BNR{" "}
            {validation.remote?.date}: {formatNumber(validation.remote?.value)}
          </span>
        </section>
      ) : null}

      <section className="content-grid">
        <article className="panel panel--wide">
          <div className="panel-header">
            <div>
              <h2>Forecast replay</h2>
              <p>Official rate, winning-model forecast, and 95% confidence interval.</p>
            </div>
            {plotData?.model ? <StatusPill label={plotData.model} tone="neutral" /> : null}
          </div>
          <ForecastChart plotData={plotData} />
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <h2>Recent rates</h2>
              <p>Latest local MXN observations.</p>
            </div>
          </div>
          <div className="rate-list">
            {rates.slice(0, 8).map((rate) => (
              <div className="rate-row" key={rate.date}>
                <span>{rate.date}</span>
                <strong>{formatNumber(rate.value)}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="panel panel--wide">
          <div className="panel-header">
            <div>
              <h2>Model comparison</h2>
              <p>MAE, RMSE, and MAPE on the same 14-observation test set.</p>
            </div>
          </div>
          <MetricTable comparison={comparison} />
        </article>
      </section>

      <ChatWidget onDashboardRefresh={loadDashboard} />
    </main>
  );
}
