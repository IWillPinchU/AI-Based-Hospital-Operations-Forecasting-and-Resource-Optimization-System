import {
  CurrentStateResponse,
  ForecastResponse,
  AnomalyResponse,
  RecommendationResponse,
  IngestionResponse,
  ModelBenchmarkResponse,
  HistoricalResponse,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function getWebSocketUrl(): string {
  const isSecure = API_BASE.startsWith("https");
  const protocol = isSecure ? "wss:" : "ws:";
  const host = API_BASE.replace(/^https?:\/\//, "");
  return `${protocol}//${host}/api/v1/ws/telemetry`;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errorJson = await res.json();
      if (errorJson && errorJson.detail) {
        errorDetail =
          typeof errorJson.detail === "string"
            ? errorJson.detail
            : JSON.stringify(errorJson.detail);
      }
    } catch {
      // Fallback to status text
      errorDetail = res.statusText || errorDetail;
    }
    const err = new Error(errorDetail) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export async function fetchCurrentState(): Promise<CurrentStateResponse> {
  const res = await fetch(`${API_BASE}/api/v1/current-state`, {
    cache: "no-store",
  });
  return handleResponse<CurrentStateResponse>(res);
}

export async function fetchForecast(model: string = "hist_gbr"): Promise<ForecastResponse> {
  const query = model ? `?model=${encodeURIComponent(model)}` : "";
  const res = await fetch(`${API_BASE}/api/v1/forecast${query}`, {
    cache: "no-store",
  });
  return handleResponse<ForecastResponse>(res);
}

export async function fetchModelBenchmarks(): Promise<ModelBenchmarkResponse> {
  const res = await fetch(`${API_BASE}/api/v1/forecast/models`, {
    cache: "no-store",
  });
  return handleResponse<ModelBenchmarkResponse>(res);
}

export async function fetchAnomalies(): Promise<AnomalyResponse> {
  const res = await fetch(`${API_BASE}/api/v1/anomalies`, {
    cache: "no-store",
  });
  return handleResponse<AnomalyResponse>(res);
}

export async function fetchRecommendations(): Promise<RecommendationResponse> {
  const res = await fetch(`${API_BASE}/api/v1/recommendations`, {
    cache: "no-store",
  });
  return handleResponse<RecommendationResponse>(res);
}

export async function uploadOperationalCsv(file: File): Promise<IngestionResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/v1/ingest/csv`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<IngestionResponse>(res);
}

export async function fetchHistory(params?: {
  start?: string;
  end?: string;
  limit?: number;
}): Promise<HistoricalResponse> {
  const queryParts: string[] = [];
  if (params?.start) queryParts.push(`start=${encodeURIComponent(params.start)}`);
  if (params?.end) queryParts.push(`end=${encodeURIComponent(params.end)}`);
  if (params?.limit) queryParts.push(`limit=${params.limit}`);
  const qs = queryParts.length > 0 ? `?${queryParts.join("&")}` : "";
  const res = await fetch(`${API_BASE}/api/v1/history${qs}`, {
    cache: "no-store",
  });
  return handleResponse<HistoricalResponse>(res);
}
