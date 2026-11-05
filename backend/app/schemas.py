from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from app.utils import ensure_utc_validator


class OperationalRowSchema(BaseModel):
    """Pydantic validation schema for a single operational hourly record."""
    timestamp: datetime
    ed_arrivals: int = Field(..., ge=0, description="Number of ED arrivals in the hour")
    ed_patients: int = Field(..., ge=0, description="Active patients in ED")
    available_beds: int = Field(..., ge=0, description="Available inpatient beds")
    icu_occupancy_pct: float = Field(..., ge=0.0, le=100.0, description="ICU occupancy % (0-100)")
    nurses_available: int = Field(..., ge=0, description="ED-only active nurses on duty")
    doctors_available: int = Field(..., ge=0, description="ED-only active doctors on duty")


class IngestionResponse(BaseModel):
    """Response returned upon successful CSV upload."""
    status: str
    filename: str
    rows_processed: int
    rows_inserted: int
    rows_updated: int
    latest_timestamp: datetime

    @field_validator("latest_timestamp", mode="before")
    @classmethod
    def ensure_utc(cls, v):
        return ensure_utc_validator(v)


class RecordIngestionResponse(BaseModel):
    """Response returned after a single live record is stored."""
    status: str
    action: str  # inserted | updated
    timestamp: datetime

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc(cls, v):
        return ensure_utc_validator(v)


class DepartmentMetrics(BaseModel):
    """Calculated operational load ratios for Layer 1 Current State."""
    patient_to_nurse_ratio: float
    patient_to_doctor_ratio: float


class CurrentStateResponse(BaseModel):
    """Layer 1 Current State response schema."""
    timestamp: datetime
    ed_arrivals: int
    ed_patients: int
    available_beds: int
    icu_occupancy_pct: float
    nurses_available: int
    doctors_available: int
    metrics: DepartmentMetrics

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc(cls, v):
        return ensure_utc_validator(v)


# Schemas for future layers (declared here per plan.md §11.1)
class ModelMetadata(BaseModel):
    model_name: str
    version: str
    paradigm: Optional[str] = None
    model_id: Optional[str] = None
    mae: Optional[float] = None
    latency_ms: Optional[float] = None


class ModelBenchmarkItem(BaseModel):
    id: str
    name: str
    paradigm: str
    library: str
    mae: float
    rmse: float
    latency_ms: float
    description: str
    is_default: bool = False


class ModelBenchmarkResponse(BaseModel):
    timestamp: str
    evaluation_split: str
    models: List[ModelBenchmarkItem]


class HourlyArrival(BaseModel):
    timestamp: datetime
    arrivals: int

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc(cls, v):
        return ensure_utc_validator(v)


class ForecastResponse(BaseModel):
    """Layer 2 Next-Hour Forecast response schema."""
    target_timestamp: datetime
    current_ed_arrivals: int
    predicted_ed_arrivals: float
    expected_net_change: float
    recent_arrivals: List[HourlyArrival] = []
    model_metadata: ModelMetadata
    available_models: List[str] = ["hist_gbr", "lstm", "holt_winters", "seasonal_naive"]

    @field_validator("target_timestamp", mode="before")
    @classmethod
    def ensure_utc(cls, v):
        return ensure_utc_validator(v)


class AnomalyResponse(BaseModel):
    """Layer 3 Anomaly Detection response schema."""
    timestamp: datetime
    observed_value: int
    expected_baseline: float
    deviation_pct: float
    is_anomaly: bool
    severity: str
    explanation: str

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc(cls, v):
        return ensure_utc_validator(v)


class RecommendationItem(BaseModel):
    id: str
    category: str
    priority: str
    action: str
    rationale: str
    constraints_checked: Optional[str] = None


class ResourceState(BaseModel):
    projected_ed_patients: int
    target_nurses_needed: int
    current_nurses_allocated: int
    nurse_deficit: int


class RecommendationResponse(BaseModel):
    """Layer 4 Resource Recommendation response schema."""
    timestamp: datetime
    advisory_disclaimer: str
    status_summary: str
    recommendations: List[RecommendationItem]
    resource_state: ResourceState

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc(cls, v):
        return ensure_utc_validator(v)


class HistoricalRecord(BaseModel):
    """Single hourly historical observation."""
    timestamp: datetime
    ed_arrivals: int
    ed_patients: int
    available_beds: int
    icu_occupancy_pct: float
    nurses_available: int
    doctors_available: int

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc(cls, v):
        return ensure_utc_validator(v)


class MetricSummary(BaseModel):
    """Statistical summary of a telemetry metric over a time window."""
    min: float
    max: float
    avg: float
    total: Optional[float] = None


class HistoricalSummary(BaseModel):
    """Aggregated period summary for historical dashboard analysis."""
    total_records: int
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    peak_arrival_timestamp: Optional[datetime] = None
    peak_arrivals: int = 0
    ed_arrivals: MetricSummary
    ed_patients: MetricSummary
    available_beds: MetricSummary
    icu_occupancy_pct: MetricSummary

    @field_validator("start_timestamp", "end_timestamp", "peak_arrival_timestamp", mode="before")
    @classmethod
    def ensure_utc(cls, v):
        return ensure_utc_validator(v) if v is not None else None


class HistoricalResponse(BaseModel):
    """Response payload for historical telemetry queries."""
    records: List[HistoricalRecord]
    summary: Optional[HistoricalSummary] = None

