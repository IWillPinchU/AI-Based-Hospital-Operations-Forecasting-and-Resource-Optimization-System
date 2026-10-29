import os

# Environment configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hospital_operations.db")
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]

# PROVISIONAL PLACEHOLDER CONSTRAINTS - NOT CLINICAL POLICY
# (Designed for college project demo & viva explainability; easily adjusted as needed)

# Layer 4 Staffing Ratios
TARGET_PATIENTS_PER_NURSE: float = 4.0
TARGET_PATIENTS_PER_DOCTOR: float = 15.0

# Layer 4 Staffing Redeployment Limits (per hour)
MAX_NURSES_REDEPLOYABLE: int = 4
MAX_DOCTORS_REDEPLOYABLE: int = 2

# Layer 4 Forecast Weight on Net Surge
FORECAST_WEIGHT: float = 0.5

# Layer 4 Bed & ICU Warning Thresholds
MIN_AVAILABLE_BEDS_THRESHOLD: int = 50
ICU_OCCUPANCY_WARNING_PCT: float = 88.0

# Layer 3 Anomaly Detection Percentage Deviation Thresholds
ANOMALY_CRITICAL_SURGE_PCT: float = 30.0
ANOMALY_MODERATE_SURGE_PCT: float = 15.0
ANOMALY_MODERATE_DROP_PCT: float = -15.0
ANOMALY_UNUSUAL_DROP_PCT: float = -30.0
