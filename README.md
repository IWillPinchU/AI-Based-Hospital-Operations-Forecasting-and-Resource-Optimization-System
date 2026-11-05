# AI-Based Hospital Operations Forecasting & Resource Optimization System

[![CI/CD Pipeline](https://github.com/placeholder/repo/actions/workflows/ci.yml/badge.svg)](https://github.com)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16.4-black.svg)](https://nextjs.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C.svg)](https://pytorch.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An intelligent, multi-layered decision-support platform designed for hospital command centers, nursing supervisors, and emergency department (ED) administrators. Operating directly on top of hospital telemetry and existing electronic health record (EHR) feeds, the system provides real-time situational awareness, multi-model time-series forecasting, diurnal anomaly detection, and capacity-constrained staff redeployment recommendations.

---

## 1. System Overview & The 4 Decision Layers

The architecture operates across four coordinated analytical layers designed to answer critical clinical operations questions:

```text
  [ Hospital Telemetry / Live Feeds ]
                  │
                  ▼
   ┌─────────────────────────────────────────┐
   │ LAYER 1: CURRENT HOSPITAL STATE         │  ◄── "What is happening right now?"
   │ Census, active load, staffing ratios    │
   └──────────────────┬──────────────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
   ┌──────────────────┐      ┌─────────────────────────┐
   │ LAYER 2:         │      │ LAYER 3:                │
   │ FORECASTING ZOO  │      │ ANOMALY DETECTION       │  ◄── "What is likely to happen next?"
   │ Multi-Model ED   │      │ Hour-of-Week Diurnal    │  ◄── "Is current demand unusual?"
   │ Arrival Predict. │      │ Deviation & Audit Trail │
   └─────────┬────────┘      └────────────┬────────────┘
             │                            │
             └────────────┬───────────────┘
                          ▼
   ┌─────────────────────────────────────────┐
   │ LAYER 4: RESOURCE OPTIMIZATION          │  ◄── "How should resources be reallocated?"
   │ Constraint-aware nurse redeployment &   │
   │ inpatient bed turnover recommendations  │
   └─────────────────────────────────────────┘
```

![Hospital operations system architecture](Hospital%20AI%20Workflow%20Architecture.png)

### Layer 1 — Real-Time Operational State
- **Purpose**: Establishes ground-truth clinical conditions without heuristic bias.
- **Vitals Monitored**: Total hourly ED arrivals, active patient census, available inpatient beds, ICU occupancy rate, active ED nurses, and attending physicians.
- **Derived Clinical Ratios**: Real-time **patient-to-nurse ratio** and **patient-to-doctor ratio** computed against departmental safety benchmarks.

### Layer 2 — Multi-Model ED Forecasting Zoo
- **Purpose**: Predicts expected ED patient arrivals for upcoming operational horizons.
- **Model Zoo**:
  1. **Histogram Gradient Boosting Regressor (HistGBR)**: Primary tabular ensemble leveraging 168-hour lag features, 6h/24h rolling statistics, and cyclical calendar transforms.
  2. **PyTorch Deep LSTM**: Sequential neural network capturing non-linear temporal dynamics across multivariate lag matrices.
  3. **Holt-Winters Triple Exponential Smoothing**: Classical statistical model capturing additive baseline trend and 24-hour diurnal seasonality.
  4. **Seasonal Naive Benchmark**: Baseline model matching historical hour-of-the-week arrivals for transparent performance comparison.
- **Dynamic Model Switcher & Leaderboard**: Inspect comparative performance metrics (**MAE**, **RMSE**, **MAPE**) directly within the dashboard modal and switch active models on the fly.

### Layer 3 — Diurnal Anomaly Detection & Persistent Audit Trail
- **Purpose**: Detects surges, mass-casualty events, and abnormal operational deviations against an hour-of-the-week baseline (168 hourly time slots).
- **Classification**: Z-score deviation thresholding categorizes conditions into `Normal`, `Elevated`, or `Critical Surge`.
- **Persistent Audit Trail**: Anomalies are logged to an internal SQLite `AnomalyEvent` table with supervisory acknowledgment workflows, mitigation note capture, and resolution timestamps.

### Layer 4 — Constraint-Aware Resource Optimization Engine
- **Purpose**: Actionable decision support translating forecasts and anomalies into staffing adjustments.
- **Operational Logic**: Formulates nurse redeployment requirements using target patient-to-nurse ratios (default `4.0`) against projected net demand.
- **Clinical Bounds**: Strict constraint adherence including maximum nurse transfer quotas (e.g., maximum 4 nurses) and guaranteed minimum coverage preservation for inpatient floors.

---

## 2. Key Features

- **⚡ Real-Time WebSocket Streaming (`/api/v1/ws/telemetry`)**: Bidirectional streaming pushes instantaneous telemetry updates to connected dashboards with automatic reconnect and 10s polling fallback.
- **📈 Historical Analytics & 24h Moving Average (SMA)**: Dedicated analytics workspace featuring interactive time-series scrubbing (24h, 7d, 30d, all-time), toggleable 24-hour SMA trend smoothing, and statistical summaries (mean, min, max, standard deviation, peak timestamp).
- **📋 Clinical Shift Handover Reports**: Generates formal clinical handover reports for 8-hour, 12-hour, or 24-hour supervisory shifts in two turnkey formats:
  - **Native Printable PDF**: Built with ReportLab, featuring executive summary vitals, anomaly logs, staffing ratios, and supervisor sign-off lines.
  - **Multi-Tab Excel Workbook**: Formatted with openpyxl, containing structured sheets for Shift Overview, Anomaly Events, and Raw Hourly Telemetry.
- **🌙 High-Contrast Clinical Dark Mode**: Purpose-built for low-light clinical stations (`#0C1417` canvas, `#142024` surface) with zero flash-of-unauthenticated-theme (anti-FOUC) and persistent client-state sync.
- **📱 Responsive Tablet & Mobile Workstation UI**: Fluid, collapsible layout adapted for tablet-mounted nursing stations, mobile phones, and ultra-wide operations walls.
- **📖 Interactive API Documentation**: Comprehensive OpenAPI 3.0 documentation categorized across 9 operational tags at `/docs` (Swagger UI) and `/redoc` (ReDoc), with a 1-click link from the top navigation bar.
- **🔄 Automated CI/CD Pipeline**: GitHub Actions workflow (`.github/workflows/ci.yml`) validating backend PyTorch tests, frontend TypeScript and ESLint checks, Next.js production builds, and Docker configurations.

---

## 3. Technology Stack

| Layer | Technologies |
| --- | --- |
| **Frontend Dashboard** | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS, Recharts, Lucide Icons |
| **Backend REST & WebSocket** | Python 3.12, FastAPI, Uvicorn, AnyIO, WebSockets, Starlette |
| **Machine Learning & Stats** | PyTorch, Scikit-Learn, Statsmodels, Pandas, NumPy, Joblib |
| **Reporting & Persistence** | ReportLab (PDF), openpyxl (Excel), SQLite (WAL Mode), SQLAlchemy |
| **DevOps & Containerization** | Docker, Docker Compose, Multi-stage Alpine builds, GitHub Actions |

---

## 4. Quickstart & Deployment

### 🚀 Turnkey Docker Compose (Recommended)

Run the full system (backend API and frontend dashboard) with a single command. The container automatically runs an idempotent bootstrap script (`init_system.py`) to generate baseline datasets, train/validate the forecasting models, initialize the SQLite database, and seed initial telemetry:

```bash
docker compose up --build
```

- **Dashboard UI**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Interactive Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **FastAPI Alternative Docs (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Backend Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

Telemetry data and SQLite state persist in the named Docker volume `sqlite_data`.

---

### 💻 Local Development Setup

#### Prerequisites
- **Python 3.12+**
- **Node.js 20+** and **npm**

#### 1. Backend Setup
Create and activate a virtual environment, then install dependencies:

```powershell
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

#### 2. Initialize Data & Train Models
Run the automated system initializer to generate synthetic data and train all forecasters:

```bash
python backend/scripts/init_system.py
```
*Alternatively, run individual scripts:*
- `python backend/scripts/generate_synthetic_data.py`
- `python backend/scripts/train_forecaster.py`

#### 3. Start the Backend API
```bash
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

#### 4. Frontend Setup & Launch
In a separate terminal window:

```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 5. Simulating Live Operations

With the backend running and initial telemetry loaded, you can simulate live streaming data arriving in real time:

```bash
python backend/scripts/simulate_live_feed.py --count 20 --interval 2
```

- `--count`: Number of hourly records to generate and push (default: `10`).
- `--interval`: Delay between record pushes in seconds (default: `2.0`).

Each record is ingested via `POST /api/v1/ingest/record` and broadcast immediately to all active dashboard clients via the WebSocket stream.

---

## 6. API Reference Summary

The backend exposes a structured, OpenAPI-compliant REST API under `/api/v1`:

| Tag | Method | Endpoint | Description |
| --- | --- | --- | --- |
| **Layer 1** | `GET` | `/api/v1/current-state` | Fetch latest operational vitals, active census, and patient ratios |
| **Layer 2** | `GET` | `/api/v1/forecast/next-hour` | Next-hour arrival forecast, confidence interval, and active model metadata |
| **Layer 2** | `GET` | `/api/v1/forecast/models` | Benchmark leaderboard comparing HistGBR, LSTM, Holt-Winters, and Naive models |
| **Layer 3** | `GET` | `/api/v1/anomalies/detect` | Current arrival anomaly classification, baseline value, and z-score |
| **Layer 3** | `GET` | `/api/v1/anomalies/events` | Audit log of historical anomaly surge events |
| **Layer 3** | `PATCH` | `/api/v1/anomalies/events/{id}/resolve` | Supervisor action to acknowledge or resolve an anomaly event |
| **Layer 4** | `GET` | `/api/v1/recommendations/resources` | Advisory nurse redeployment and bed turnover recommendations |
| **Historical** | `GET` | `/api/v1/history/telemetry` | Filtered time-series historical records with 24h rolling SMA aggregates |
| **Reports** | `GET` | `/api/v1/reports/shift` | Download formal shift handover report (`?format=pdf` or `?format=xlsx`) |
| **Ingestion** | `POST` | `/api/v1/ingest/csv` | Upload operational CSV file with schema validation and idempotent upsert |
| **Ingestion** | `POST` | `/api/v1/ingest/record` | Ingest a single operational telemetry record for live simulation |
| **WebSocket** | `WS` | `/api/v1/ws/telemetry` | Bidirectional real-time telemetry feed with heartbeat ping/pong |
| **Health** | `GET` | `/health` | Liveness probe for Docker container healthchecks |

---

## 7. Testing & Quality Assurance

### Backend Test Suite
Run the 51 unit and integration tests with pytest:
```bash
pytest backend/tests -v
```
Test coverage includes:
- Schema validation and data transformations
- Multi-model forecasting zoo inference and fallback logic
- Diurnal anomaly z-score thresholds and persistent event resolution
- Resource optimization constraints and ratios
- PDF and Excel binary report generation
- WebSocket stream handshake, ping/pong, and broadcast broadcasting

### Frontend Quality Checks
```bash
cd frontend
npm run lint          # ESLint validation
npx tsc --noEmit      # Strict TypeScript typechecking
npm run build         # Next.js production build verification
```

---

## 8. Repository Layout

```text
├── .github/
│   └── workflows/
│       └── ci.yml                 # Multi-job GitHub Actions CI/CD
├── backend/
│   ├── app/
│   │   ├── config.py              # Application settings & CORS
│   │   ├── database.py            # SQLite engine, models, and session management
│   │   ├── main.py                # FastAPI factory, OpenAPI tags, and lifespan
│   │   ├── routes.py              # REST API endpoints and WebSocket handler
│   │   └── schemas.py             # Pydantic v2 validation models
│   ├── models/
│   │   ├── ed_forecaster.joblib   # Trained HistGradientBoosting regressor
│   │   ├── lstm_forecaster.pt     # Trained PyTorch Deep LSTM weights
│   │   └── model_zoo.py           # Multi-model inference & benchmark engine
│   ├── scripts/
│   │   ├── generate_synthetic_data.py
│   │   ├── init_system.py         # Self-bootstrapping container script
│   │   ├── simulate_live_feed.py  # Real-time telemetry generator
│   │   └── train_forecaster.py    # Training pipeline
│   ├── tests/                     # 51 pytest tests
│   ├── Dockerfile                 # Python 3.12-slim backend container
│   ├── docker-entrypoint.sh       # Container entrypoint with auto-init
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── globals.css        # Clinical theme tokens & Tailwind v4
│   │   │   ├── layout.tsx         # Root layout with anti-FOUC theme script
│   │   │   └── page.tsx           # Live & Historical tab orchestration
│   │   ├── components/            # Visual cards, charts, and modals
│   │   └── lib/                   # API client, ThemeContext, formatters
│   ├── Dockerfile                 # Multi-stage Alpine container
│   └── package.json
├── docker-compose.yml             # Turnkey multi-container orchestration
├── Hospital AI Workflow Architecture.png
└── README.md
```

---

## 9. Academic Scope & Disclaimer

This system is developed as an engineering major project focusing on operational machine learning, time-series forecasting, and clinical decision support systems. 

**Clinical Disclaimer**: This software is intended strictly for administrative and operational decision support (capacity management, nurse staffing, and bed turnover). It does **not** perform clinical triage, diagnostic evaluation, or medical treatment planning. All recommendations are advisory and require clinical supervisor verification.
