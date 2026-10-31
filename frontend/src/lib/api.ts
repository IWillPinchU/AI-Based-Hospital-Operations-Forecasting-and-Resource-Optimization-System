import {
  CurrentStateResponse,
  ForecastResponse,
  AnomalyResponse,
  RecommendationResponse,
  IngestionResponse,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

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

export async function fetchForecast(): Promise<ForecastResponse> {
  const res = await fetch(`${API_BASE}/api/v1/forecast`, {
    cache: "no-store",
  });
  return handleResponse<ForecastResponse>(res);
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
