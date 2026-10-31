import math
from datetime import timezone
from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import (
    ADVISORY_DISCLAIMER,
    FORECAST_WEIGHT,
    ICU_OCCUPANCY_WARNING_PCT,
    MAX_NURSES_REDEPLOYABLE,
    MIN_AVAILABLE_BEDS_THRESHOLD,
    TARGET_PATIENTS_PER_NURSE,
)
from app.database import OperationalMetrics
from app.forecast import get_ed_forecast
from app.schemas import (
    RecommendationItem,
    RecommendationResponse,
    ResourceState,
)


def get_resource_recommendations(db: Session) -> RecommendationResponse:
    """Layer 4: Generates advisory nurse staffing and bed management recommendations."""
    # 1. Fetch latest operational state
    latest = (
        db.query(OperationalMetrics)
        .order_by(desc(OperationalMetrics.timestamp))
        .first()
    )

    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No operational data available. Please upload an operational CSV first.",
        )

    # 2. Query Layer 2 forecast (requires >= 25 hours of lag data and trained model)
    forecast = get_ed_forecast(db)

    # 3. Compute Projected ED Active Load (L_proj) per §7.3
    # L_proj = ed_patients_t + max(0, ceil(w_fc * (y_hat_t+1 - y_t)))
    net_arrival_delta = forecast.predicted_ed_arrivals - latest.ed_arrivals
    surge_patients = max(0, math.ceil(FORECAST_WEIGHT * net_arrival_delta))
    projected_ed_patients = latest.ed_patients + surge_patients

    # 4. Compute target staffing needs
    target_nurses_needed = math.ceil(projected_ed_patients / TARGET_PATIENTS_PER_NURSE)

    # 5. Compute deficits and capped redeployment deltas
    nurse_deficit = max(target_nurses_needed - latest.nurses_available, 0)
    delta_nurses = min(nurse_deficit, MAX_NURSES_REDEPLOYABLE)

    recommendations = []

    # 6. Rule 1: Staffing Adjustment Recommendation (REC-001)
    if delta_nurses > 0:
        nurse_noun = "nurses" if delta_nurses > 1 else "nurse"
        recommendations.append(
            RecommendationItem(
                id="REC-001",
                category="STAFFING_NURSE",
                priority="HIGH",
                action=f"Consider allocating {delta_nurses} additional {nurse_noun} to the ED",
                rationale=(
                    f"Projected active load of {projected_ed_patients} patients "
                    f"({latest.ed_patients} active + {surge_patients} net forecasted surge; discharges excluded in v1) "
                    f"requires {target_nurses_needed} nurses at {TARGET_PATIENTS_PER_NURSE:.1f} patients/nurse "
                    f"(current ED staffing: {latest.nurses_available} nurses)."
                ),
                constraints_checked=(
                    f"Within max redeployment budget ({MAX_NURSES_REDEPLOYABLE} nurses max). "
                    f"Assumes minimum inpatient floor coverage maintained."
                ),
            )
        )

    # 7. Rule 2: Bed & ICU Buffer Review Recommendation (REC-002)
    bed_alert = latest.available_beds < MIN_AVAILABLE_BEDS_THRESHOLD
    icu_alert = latest.icu_occupancy_pct >= ICU_OCCUPANCY_WARNING_PCT

    if bed_alert or icu_alert:
        fired_conditions = []
        if bed_alert:
            fired_conditions.append(
                f"Available beds ({latest.available_beds}) below minimum threshold ({MIN_AVAILABLE_BEDS_THRESHOLD})"
            )
        if icu_alert:
            fired_conditions.append(
                f"ICU occupancy ({latest.icu_occupancy_pct:.1f}%) at or above warning level ({ICU_OCCUPANCY_WARNING_PCT:.1f}%)"
            )

        rationale_text = " and ".join(fired_conditions) + "."

        recommendations.append(
            RecommendationItem(
                id="REC-002",
                category="BED_MANAGEMENT",
                priority="HIGH",
                action="Review inpatient bed turnover",
                rationale=rationale_text,
                constraints_checked=None,
            )
        )

    # 8. Determine overall status summary
    if delta_nurses > 0 and (bed_alert or icu_alert):
        status_summary = "High ED demand surge forecasted; staffing adjustment and bed turnover review recommended."
    elif delta_nurses > 0:
        status_summary = "High ED demand surge forecasted; staffing adjustment recommended."
    elif bed_alert or icu_alert:
        status_summary = "Bed buffer or ICU capacity alert; turnover review recommended."
    else:
        status_summary = "Operational capacity and staffing within acceptable limits."

    ts = (
        latest.timestamp.replace(tzinfo=timezone.utc)
        if latest.timestamp.tzinfo is None
        else latest.timestamp.astimezone(timezone.utc)
    )

    return RecommendationResponse(
        timestamp=ts,
        advisory_disclaimer=ADVISORY_DISCLAIMER,
        status_summary=status_summary,
        recommendations=recommendations,
        resource_state=ResourceState(
            projected_ed_patients=projected_ed_patients,
            target_nurses_needed=target_nurses_needed,
            current_nurses_allocated=latest.nurses_available,
            nurse_deficit=nurse_deficit,
        ),
    )
