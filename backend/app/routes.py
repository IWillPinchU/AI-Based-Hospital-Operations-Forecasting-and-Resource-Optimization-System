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


@router.post("/ingest/csv", response_model=IngestionResponse, tags=["Ingestion"])
async def upload_operational_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Ingests a CSV containing hourly operational metrics with idempotent upsert and broadcasts update."""
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


@router.post("/ingest/record", response_model=RecordIngestionResponse, tags=["Ingestion"])
async def upload_operational_record(record: OperationalRowSchema, db: Session = Depends(get_db)):
    """Ingests one live hourly record with upsert on its UTC timestamp and broadcasts update."""
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
    """Real-time WebSocket stream broadcasting hospital telemetry updates."""
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


@router.get("/current-state", response_model=CurrentStateResponse, tags=["Layer 1"])
def read_current_state(db: Session = Depends(get_db)):
    """Layer 1: Returns the latest operational hospital state and load ratios."""
    return get_current_hospital_state(db)


@router.get("/forecast/models", response_model=ModelBenchmarkResponse, tags=["Layer 2"])
def read_forecasting_models_benchmark():
    """Layer 2: Returns the comparative benchmark leaderboard comparing all models."""
    return get_model_benchmark()


@router.get("/forecast", response_model=ForecastResponse, tags=["Layer 2"])
def read_ed_forecast(
    model: str = "hist_gbr",
    db: Session = Depends(get_db),
):
    """Layer 2: Returns next-hour ED arrival prediction using requested model paradigm."""
    return get_ed_forecast(db, model_name=model)


@router.get("/anomalies", response_model=AnomalyResponse, tags=["Layer 3"])
def read_ed_anomalies(db: Session = Depends(get_db)):
    """Layer 3: Compares current ED arrivals against historical hour-of-week baseline."""
    return detect_ed_anomalies(db)


@router.get("/anomalies/history", response_model=AnomalyHistoryResponse, tags=["Layer 3"])
def read_anomaly_history(
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL_SURGE, MODERATE_SURGE, etc."),
    resolved: Optional[bool] = Query(None, description="Filter by resolved status: true / false"),
    limit: int = Query(50, ge=1, le=500, description="Max anomaly events to return"),
    db: Session = Depends(get_db),
):
    """Returns persistent anomaly alert history log and aggregate statistics."""
    return get_anomaly_history(db, severity=severity, resolved=resolved, limit=limit)


@router.post("/anomalies/{event_id}/resolve", response_model=AnomalyResolveResponse, tags=["Layer 3"])
def set_anomaly_resolution(
    event_id: int,
    resolved: bool = Query(True, description="Target resolved state"),
    db: Session = Depends(get_db),
):
    """Updates the resolved / acknowledged status of a specific anomaly alert event."""
    return resolve_anomaly_event(db, event_id=event_id, resolved=resolved)


@router.post("/anomalies/scan", tags=["Layer 3"])
def scan_historical_anomalies(db: Session = Depends(get_db)):
    """Scans all historical database rows and backfills anomaly events into the persistent log."""
    count = scan_and_record_all_anomalies(db)
    return {"status": "success", "new_anomalies_recorded": count}


@router.get("/recommendations", response_model=RecommendationResponse, tags=["Layer 4"])
def read_resource_recommendations(db: Session = Depends(get_db)):
    """Layer 4: Returns advisory nurse staffing and bed turnover adjustments."""
    return get_resource_recommendations(db)


@router.get("/history", response_model=HistoricalResponse, tags=["Historical Analytics"])
def read_historical_data(
    start: Optional[str] = Query(None, description="Start UTC timestamp (inclusive, ISO-8601)"),
    end: Optional[str] = Query(None, description="End UTC timestamp (inclusive, ISO-8601)"),
    limit: int = Query(720, ge=1, le=2000, description="Max records to return"),
    db: Session = Depends(get_db),
):
    """Returns historical operational records and window aggregates for trends and charts."""
    try:
        start_dt = parse_query_datetime(start)
        end_dt = parse_query_datetime(end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return get_historical_telemetry(db, start=start_dt, end=end_dt, limit=limit)


@router.get("/reports/shift", tags=["Reports"])
def download_shift_report(
    hours: int = Query(12, ge=1, le=72, description="Shift window in hours (e.g. 8, 12, 24)"),
    format: str = Query("pdf", description="Report file format: pdf or excel"),
    db: Session = Depends(get_db),
):
    """Generates and downloads a formatted PDF or Excel operational shift handover report."""
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
