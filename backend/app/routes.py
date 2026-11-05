from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, WebSocket, WebSocketDisconnect, Query, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion import ingest_operational_csv, ingest_single_record
from app.state import get_current_hospital_state
from app.forecast import get_ed_forecast, get_model_benchmark
from app.anomaly import (
    detect_ed_anomalies,
    get_anomaly_history,
    resolve_anomaly_event,
    scan_and_record_all_anomalies,
)
from app.optimizer import get_resource_recommendations
from app.history import get_historical_telemetry
from app.reports import gather_shift_data, generate_shift_pdf, generate_shift_excel
from app.utils import parse_query_datetime
from app.websocket_manager import manager
from app.schemas import (
    IngestionResponse,
    OperationalRowSchema,
    RecordIngestionResponse,
    CurrentStateResponse,
    ForecastResponse,
    ModelBenchmarkResponse,
    AnomalyResponse,
    AnomalyHistoryResponse,
    AnomalyResolveResponse,
    RecommendationResponse,
    HistoricalResponse,
)

router = APIRouter(prefix="/api/v1")


@router.post(
    "/ingest/csv",
    response_model=IngestionResponse,
    tags=["Ingestion"],
    summary="Upload Operational Telemetry CSV",
    description="Ingests a CSV containing hourly hospital operational telemetry with idempotent timestamp-keyed upsert and notifies live clients over WebSocket.",
    response_description="Ingestion processing summary statistics including processed, inserted, and updated row counts.",
)
async def upload_operational_csv(file: UploadFile = File(..., description="Hourly operations CSV file matching standard 7-field schema"), db: Session = Depends(get_db)):
    result = ingest_operational_csv(file, db)
    await manager.broadcast({
        "event": "data_updated",
        "source": "csv_upload",
        "rows_processed": result.rows_processed,
        "rows_inserted": result.rows_inserted,
        "rows_updated": result.rows_updated,
        "latest_timestamp": result.latest_timestamp.isoformat() if result.latest_timestamp else None,
    })
    return result


@router.post(
    "/ingest/record",
    response_model=RecordIngestionResponse,
    tags=["Ingestion"],
    summary="Ingest Single Telemetry Record",
    description="Ingests a single hourly telemetry record (used by live streaming simulators) with idempotent upsert.",
    response_description="Action taken (inserted / updated) and validated timestamp.",
)
async def upload_operational_record(record: OperationalRowSchema, db: Session = Depends(get_db)):
    result = ingest_single_record(record, db)
    await manager.broadcast({
        "event": "data_updated",
        "source": "live_feed",
        "action": result.action,
        "timestamp": result.timestamp.isoformat() if result.timestamp else None,
    })
    return result


@router.websocket("/ws")
@router.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """Real-time bidirectional WebSocket stream broadcasting live telemetry notifications and heartbeats."""
    await manager.connect(websocket)
    try:
        await websocket.send_json({
            "event": "connected",
            "message": "Connected to real-time hospital operations stream",
        })
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@router.get(
    "/current-state",
    response_model=CurrentStateResponse,
    tags=["Layer 1 - Current State"],
    summary="Get Current Operational Hospital State",
    description="Layer 1: Returns the latest operational census, ED volume, bed headroom, and calculated patient-to-staff ratios.",
    response_description="Current hospital operational telemetry and staffing ratios.",
)
def read_current_state(db: Session = Depends(get_db)):
    return get_current_hospital_state(db)


@router.get(
    "/forecast/models",
    response_model=ModelBenchmarkResponse,
    tags=["Layer 2 - ED Forecasting"],
    summary="Get Multi-Model Forecasting Benchmark Leaderboard",
    description="Layer 2: Returns comparative evaluation metrics (MAE, RMSE, inference latency in ms) across all four model paradigms (HistGBR, PyTorch LSTM, Holt-Winters, Seasonal Naive) evaluated on holdout temporal data.",
    response_description="Model evaluation leaderboard and metadata.",
)
def read_forecasting_models_benchmark():
    return get_model_benchmark()


@router.get(
    "/forecast",
    response_model=ForecastResponse,
    tags=["Layer 2 - ED Forecasting"],
    summary="Predict Next-Hour ED Arrivals",
    description="Layer 2: Returns the next-hour emergency department arrival prediction using the specified model paradigm along with the 24-hour historical trajectory.",
    response_description="Predicted arrival count, net change, and 24-hour historical window.",
)
def read_ed_forecast(
    model: str = Query("hist_gbr", description="Forecasting paradigm: hist_gbr | lstm | holt_winters | seasonal_naive"),
    db: Session = Depends(get_db),
):
    return get_ed_forecast(db, model_name=model)


@router.get(
    "/anomalies",
    response_model=AnomalyResponse,
    tags=["Layer 3 - Anomaly Detection"],
    summary="Detect Current Arrival Pattern Anomalies",
    description="Layer 3: Compares current observed arrivals against the historical hour-of-week diurnal baseline to classify volume surges or drops.",
    response_description="Anomaly status, classification severity, percentage deviation, and clinical explanation.",
)
def read_ed_anomalies(db: Session = Depends(get_db)):
    return detect_ed_anomalies(db)


@router.get(
    "/anomalies/history",
    response_model=AnomalyHistoryResponse,
    tags=["Layer 3 - Anomaly Detection"],
    summary="Query Persistent Anomaly Audit Log",
    description="Layer 3: Returns chronologically ordered anomaly history log with filtering by severity, resolution state, and aggregate summary KPIs.",
    response_description="List of persisted anomaly events and aggregate statistics.",
)
def read_anomaly_history(
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL_SURGE, MODERATE_SURGE, MODERATE_DROP, UNUSUAL_DROP"),
    resolved: Optional[bool] = Query(None, description="Filter by resolution state: true (acknowledged) / false (open)"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of anomaly records to return"),
    db: Session = Depends(get_db),
):
    return get_anomaly_history(db, severity=severity, resolved=resolved, limit=limit)


@router.post(
    "/anomalies/{event_id}/resolve",
    response_model=AnomalyResolveResponse,
    tags=["Layer 3 - Anomaly Detection"],
    summary="Acknowledge or Reopen Anomaly Event",
    description="Layer 3: Updates the acknowledged / resolved status of a specific persistent anomaly alert event for supervisor workflows.",
    response_description="Updated resolution status and timestamp.",
)
def set_anomaly_resolution(
    event_id: int,
    resolved: bool = Query(True, description="Target resolved state: true to acknowledge, false to reopen"),
    db: Session = Depends(get_db),
):
    return resolve_anomaly_event(db, event_id=event_id, resolved=resolved)


@router.post(
    "/anomalies/scan",
    tags=["Layer 3 - Anomaly Detection"],
    summary="Backfill Anomaly Audit Log from Historical Telemetry",
    description="Layer 3: Scans all historical database records against the diurnal baseline and indexes uncataloged surge events into the persistent audit log.",
    response_description="Count of newly discovered and recorded anomaly events.",
)
def scan_historical_anomalies(db: Session = Depends(get_db)):
    count = scan_and_record_all_anomalies(db)
    return {"status": "success", "new_anomalies_recorded": count}


@router.get(
    "/recommendations",
    response_model=RecommendationResponse,
    tags=["Layer 4 - Resource Optimization"],
    summary="Generate Advisory Resource Allocations",
    description="Layer 4: Decision-support optimization engine evaluating current load, arrival forecasts, and hospital constraints to recommend nurse redeployments and bed turnover adjustments.",
    response_description="Action queue of prioritized clinical recommendations with rationale and constraints.",
)
def read_resource_recommendations(db: Session = Depends(get_db)):
    return get_resource_recommendations(db)


@router.get(
    "/history",
    response_model=HistoricalResponse,
    tags=["Historical Analytics"],
    summary="Query Historical Time-Series Telemetry",
    description="Returns filtered historical operational records, rolling averages, peak inflows, and window aggregate summaries for trends and interactive charts.",
    response_description="Historical time-series observation records and statistical summary.",
)
def read_historical_data(
    start: Optional[str] = Query(None, description="Start UTC timestamp (inclusive, ISO-8601, e.g. '2026-10-01T00:00:00Z')"),
    end: Optional[str] = Query(None, description="End UTC timestamp (inclusive, ISO-8601, e.g. '2026-10-07T23:00:00Z')"),
    limit: int = Query(720, ge=1, le=2000, description="Maximum observation records to return"),
    db: Session = Depends(get_db),
):
    try:
        start_dt = parse_query_datetime(start)
        end_dt = parse_query_datetime(end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return get_historical_telemetry(db, start=start_dt, end=end_dt, limit=limit)


@router.get(
    "/reports/shift",
    tags=["Reports"],
    summary="Generate Clinical Shift Handover Report",
    description="Generates an automated, auditable shift handover report in printable PDF (ReportLab) or multi-tab Excel (openpyxl) format covering the last N hours.",
    response_description="Binary file stream (PDF or XLSX) with Content-Disposition attachment header.",
)
def download_shift_report(
    hours: int = Query(12, ge=1, le=72, description="Shift window duration in hours (e.g. 8, 12, 24)"),
    format: str = Query("pdf", description="Report file format: 'pdf' or 'excel'"),
    db: Session = Depends(get_db),
):
    fmt = format.lower().strip()
    if fmt not in ["pdf", "excel", "xlsx"]:
        raise HTTPException(status_code=400, detail="Invalid format. Supported formats are 'pdf' or 'excel'.")

    data = gather_shift_data(db, hours=hours)
    ts_str = data["end_time"].strftime("%Y%m%d_%H%M")

    if fmt == "pdf":
        content = generate_shift_pdf(data)
        media_type = "application/pdf"
        filename = f"hospital_shift_report_{hours}h_{ts_str}.pdf"
    else:
        content = generate_shift_excel(data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"hospital_shift_report_{hours}h_{ts_str}.xlsx"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
