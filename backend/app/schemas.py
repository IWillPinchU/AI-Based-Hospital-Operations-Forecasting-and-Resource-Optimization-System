from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


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
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


# Schemas for future layers (declared here per plan.md §11.1)
class ModelMetadata(BaseModel):
    model_name: str
    version: str


class ForecastResponse(BaseModel):
    """Layer 2 Next-Hour Forecast response schema."""
    target_timestamp: datetime
    current_ed_arrivals: int
    predicted_ed_arrivals: float
    expected_net_change: float
    model_metadata: ModelMetadata

    @field_validator("target_timestamp", mode="before")
    @classmethod
    def ensure_utc(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


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
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class RecommendationItem(BaseModel):
    id: str
    category: str
    priority: str
    action: str
    rationale: str
    constraints_checked: str


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
