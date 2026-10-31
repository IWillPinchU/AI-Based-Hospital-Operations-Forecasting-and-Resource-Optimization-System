export interface IngestionResponse {
  status: string;
  filename: string;
  rows_processed: number;
  rows_inserted: number;
  rows_updated: number;
  latest_timestamp: string;
}

export interface DepartmentMetrics {
  patient_to_nurse_ratio: number;
  patient_to_doctor_ratio: number;
}

export interface CurrentStateResponse {
  timestamp: string;
  ed_arrivals: number;
  ed_patients: number;
  available_beds: number;
  icu_occupancy_pct: number;
  nurses_available: number;
  doctors_available: number;
  metrics: DepartmentMetrics;
}

export interface HourlyArrival {
  timestamp: string;
  arrivals: number;
}

export interface ModelMetadata {
  model_name: string;
  version: string;
}

export interface ForecastResponse {
  target_timestamp: string;
  current_ed_arrivals: number;
  predicted_ed_arrivals: number;
  expected_net_change: number;
  recent_arrivals: HourlyArrival[];
  model_metadata: ModelMetadata;
}

export type AnomalySeverity =
  | "NORMAL"
  | "MODERATE_SURGE"
  | "CRITICAL_SURGE"
  | "MODERATE_DROP"
  | "UNUSUAL_DROP";

export interface AnomalyResponse {
  timestamp: string;
  observed_value: number;
  expected_baseline: number;
  deviation_pct: number;
  is_anomaly: boolean;
  severity: AnomalySeverity;
  explanation: string;
}

export interface RecommendationItem {
  id: string;
  category: string;
  priority: string;
  action: string;
  rationale: string;
  constraints_checked?: string | null;
}

export interface ResourceState {
  projected_ed_patients: number;
  target_nurses_needed: number;
  current_nurses_allocated: number;
  nurse_deficit: number;
}

export interface RecommendationResponse {
  timestamp: string;
  advisory_disclaimer: string;
  status_summary: string;
  recommendations: RecommendationItem[];
  resource_state: ResourceState;
}

export interface ApiError {
  detail: string;
  status: number;
}
