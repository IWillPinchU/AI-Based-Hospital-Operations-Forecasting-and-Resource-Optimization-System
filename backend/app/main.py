from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.database import init_db
from app.routes import router

API_DESCRIPTION = """
### Operational Intelligence Overlay System for Acute Care Capacity Management

This system acts as an operational decision-support overlay operating above existing Hospital Information Systems (HIS) and Electronic Health Records (EHR). It continuously answers four critical operational questions:

1. **What is happening in the hospital right now?** *(Layer 1 — Current State Telemetry)*
2. **What arrival volume should we anticipate next?** *(Layer 2 — ED Arrival Forecasting)*
3. **Is current operational behavior abnormal?** *(Layer 3 — Statistical Anomaly Detection)*
4. **How should available resources be allocated?** *(Layer 4 — Resource Optimization)*

---

### Core Operational Capabilities

- **Multi-Model Forecasting Zoo**: Compares Tree Ensembles (HistGradientBoosting), Deep Recurrent Networks (PyTorch LSTM), Statistical Exponential Smoothing (Holt-Winters), and Seasonal Naive empirical baselines.
- **Diurnal Anomaly Detection**: Evaluates current observations against historical hour-of-week distributions, persisting detected surges into an auditable SQLite event log.
- **Clinical Decision-Support Rules**: Generates actionable, constraint-bounded staffing recommendations and bed buffer alerts.
- **Automated Handover Reporting**: Generates clinical shift handover documentation in printable PDF and multi-tab Excel workbooks.
- **Real-Time Streaming**: High-frequency telemetry synchronization via bidirectional WebSocket (`/api/v1/ws/telemetry`).
"""

TAGS_METADATA = [
    {
        "name": "Layer 1 - Current State",
        "description": "Current department vitals, active patient census, and staffing load ratios.",
    },
    {
        "name": "Layer 2 - ED Forecasting",
        "description": "Next-hour arrival forecasts across multiple ML paradigms and comparative benchmark leaderboard.",
    },
    {
        "name": "Layer 3 - Anomaly Detection",
        "description": "Diurnal hour-of-week surge detection, persistent alert audit log, and supervisor resolution workflow.",
    },
    {
        "name": "Layer 4 - Resource Optimization",
        "description": "Clinical decision-support recommendations for nurse redeployment, bed turnaround, and capacity warnings.",
    },
    {
        "name": "Historical Analytics",
        "description": "Time-series query engine with window aggregates, moving averages, date filtering, and CSV export.",
    },
    {
        "name": "Reports",
        "description": "Automated clinical shift handover documentation generated in printable PDF and multi-tab Excel formats.",
    },
    {
        "name": "Ingestion",
        "description": "Operational CSV file upload with idempotent upserts and single-record live feed simulator ingestion.",
    },
    {
        "name": "WebSocket",
        "description": "Bidirectional real-time WebSocket telemetry stream for instant live dashboard synchronization.",
    },
    {
        "name": "Health",
        "description": "Container healthchecks, readiness probes, and service liveness checks.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database tables at startup without migrations
    init_db()
    yield


app = FastAPI(
    title="AI-Based Hospital Operations Forecasting & Resource Optimization API",
    description=API_DESCRIPTION,
    version="1.0.0",
    openapi_tags=TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    contact={
        "name": "Hospital Operations AI Project",
        "url": "http://localhost:3000",
    },
    license_info={
        "name": "MIT Academic License",
    },
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Register routes under /api/v1
app.include_router(router)


@app.get(
    "/health",
    tags=["Health"],
    summary="Service Health Check",
    description="Returns service liveness status and backend identifier for Docker and container probes.",
    response_description="Service status payload.",
)
def health_check():
    return {"status": "ok", "service": "hospital-operations-backend"}
