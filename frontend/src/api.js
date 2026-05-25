const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:7772";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with status ${response.status}`);
  }

  return response.json();
}

export const api = {
  health: () => request("/api/health"),
  rates: (limit = 30) => request(`/api/rates?limit=${limit}`),
  validateRates: () => request("/api/rates/validate"),
  latestForecast: () => request("/api/forecast/latest"),
  latestRun: () => request("/api/runs?limit=1"),
  compareModels: () => request("/api/models/compare"),
  plotData: () => request("/api/plot-data"),
  scrape: () => request("/api/scrape", { method: "POST" }),
  train: () => request("/api/train", { method: "POST" }),
  chat: (message) =>
    request("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message })
    })
};
