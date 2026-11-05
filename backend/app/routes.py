from fastapi import APIRouter, Depends, UploadFile, File, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion import ingest_operational_csv, ingest_single_record
from app.state import get_current_hospital_state
from app.forecast import get_ed_forecast, get_model_benchmark
from app.anomaly import detect_ed_anomalies
from app.optimizer import get_resource_recommendations
from app.websocket_manager import manager
from app.schemas import (
    IngestionResponse,
    OperationalRowSchema,
    RecordIngestionResponse,
    CurrentStateResponse,
    ForecastResponse,
    ModelBenchmarkResponse,
    AnomalyResponse,
    RecommendationResponse,
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


@router.get("/recommendations", response_model=RecommendationResponse, tags=["Layer 4"])
def read_resource_recommendations(db: Session = Depends(get_db)):
    """Layer 4: Returns advisory nurse staffing and bed turnover adjustments."""
    return get_resource_recommendations(db)
