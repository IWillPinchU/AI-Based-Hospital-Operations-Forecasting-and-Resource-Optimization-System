# AI-Based Hospital Operations Forecasting and Resource Optimization System

## 1. Project Purpose

This project is a hospital-wide operational intelligence system that works on top of existing hospital data. It does not replace the hospital's management or Hospital Information System (HIS).

The system analyzes operational data to answer four questions:

1. What is happening in the hospital now?
2. Is anything unusual?
3. What is likely to happen next?
4. Given this information, how should available resources be allocated?

## 2. System Architecture

![Hospital operations system architecture](Hospital%20AI%20Workflow%20Architecture.png)

## 3. Layer 1 — Current Hospital State

**Purpose:** Represent the hospital's current operational condition.

The system assumes that the hospital provides clean, model-ready operational rows. Extracting information from raw patient records is outside the current scope.

Example:

```text
Timestamp:          14:00
ED arrivals:        57
ED patients:        43
Available beds:     42
ICU occupancy:      87%
Nurses available:   18
Doctors available:   7
...
```

Layer 1 represents the current state. It does not predict outcomes or make decisions.

## 4. Layer 2 — ED Arrival Forecasting

This is the first machine-learning model in the system.

**Primary target:**

> Forecast the number of ED arrivals in the next hour.

Example:

```text
Current ED arrivals:        57
              ↓
       Forecasting Model
              ↓
Expected next-hour arrivals: 61
```

The model is trained on historical hospital data. New hospital data is used for inference, not immediate retraining. Retraining can take place periodically.

For now, ED arrivals are the only forecasting target.

## 5. Layer 3 — Anomaly Detection

**Purpose:** Identify unusual conditions in the hospital's current operational data.

The anomaly detection system compares current observations against an independent historical baseline.

Example:

```text
Observed ED arrivals:    57
Normal for this period: ~40

→ ED arrivals are anomalously high
```

The anomaly system may eventually monitor multiple operational variables. Its initial focus can be ED arrivals. It operates independently of the forecasting model.

## 6. Layer 4 — Resource Optimization

This is the decision-support layer. It receives:

- Current hospital state
- ED arrival forecast
- Detected anomalies
- Available resources
- Known operational information
- Hospital constraints

It produces recommended resource allocations or actions.

Example:

> **Recommendation:** Consider allocating 2 additional nurses to the ED, subject to minimum staffing requirements in other departments.

Resources may include:

- Nurses
- Doctors
- Beds
- ICU capacity
- Department capacity

Example inputs and flow:

```text
Current ED demand       → High
ED arrivals anomaly     → Yes
Next-hour forecast      → 61
Nurses available        → 18
Beds available          → 42
Hospital constraints    → ...
                 ↓
          Optimization
                 ↓
      Resource recommendation
```

The optimization layer does not need to be a machine-learning model. It can use mathematical or constraint optimization.

## 7. Frontend

The frontend presents the system's outputs.

### Current State

> Current ED arrivals: 57

### Forecast

> Next-hour ED arrivals: 61

### Anomaly

> ED arrivals are 42.5% above the normal baseline.

### Resource Recommendation

> Review ED staffing and bed capacity given elevated current demand and forecasted arrivals.

## 8. Current Model and Algorithm Count

| Component | Type |
| --- | --- |
| Current State | Data processing |
| ED Forecasting | ML model |
| Anomaly Detection | Anomaly detection model or method |
| Resource Optimization | Optimization algorithm or model |
| Frontend | Application/UI |

## 9. Tech Stack

- **Frontend:** Next.js, TypeScript, Tailwind CSS
- **Backend API:** Python, FastAPI

## 10. How to Run

### 1. Install Backend Dependencies
Ensure the Python virtual environment (`.venv`) is activated or use its interpreter directly:
```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

### 2. Generate Synthetic Operational Data
Generate the baseline dataset (`hospital_operations_synthetic.csv`) and surge demo dataset (`surge_demo.csv`):
```powershell
.\.venv\Scripts\python.exe backend/scripts/generate_synthetic_data.py
```

### 3. Train the Forecasting Model
Extract lag features and train the HistGradientBoosting regressor:
```powershell
.\.venv\Scripts\python.exe backend/scripts/train_forecaster.py
```
This produces `backend/models/ed_forecaster.joblib`.

### 4. Start the Backend API
Run the FastAPI development server:
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --port 8000 --reload
```
The API documentation is available at `http://localhost:8000/docs`.

### 5. Install and Start the Frontend
In a separate terminal window:
```powershell
cd frontend
npm install
npm run dev
```
The Next.js dashboard will be served at `http://localhost:3000`.

### 6. Upload Operational CSV
1. Open `http://localhost:3000` in your browser.
2. Click **Upload Operational CSV** in the top navigation bar.
3. Select `hospital_operations_synthetic.csv` (or `surge_demo.csv` to demonstrate critical surge triage and nurse redeployment).
4. Click **Upload & Process**. The dashboard will ingest the records into SQLite and immediately display live telemetry, next-hour arrival forecasts, anomaly classifications, and advisory staffing recommendations.
