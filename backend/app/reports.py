import io
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
import numpy as np

from app.database import OperationalMetrics, AnomalyEvent
from app.state import get_current_hospital_state
from app.forecast import get_ed_forecast
from app.optimizer import get_resource_recommendations
from app.utils import to_utc

# ReportLab components for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)

# Openpyxl components for Excel generation
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def gather_shift_data(db: Session, hours: int = 12) -> Dict[str, Any]:
    """Collects telemetry, statistics, anomalies, and recommendations for the specified shift duration."""
    latest_metric = (
        db.query(OperationalMetrics)
        .order_by(desc(OperationalMetrics.timestamp))
        .first()
    )

    if not latest_metric:
        raise HTTPException(
            status_code=404,
            detail="No operational records available. Ingest operational telemetry before generating a shift report.",
        )

    end_time = to_utc(latest_metric.timestamp)
    start_time = end_time - timedelta(hours=hours)

    # In SQLite, timestamps are stored as naive UTC
    naive_start = start_time.replace(tzinfo=None)
    naive_end = end_time.replace(tzinfo=None)

    rows = (
        db.query(OperationalMetrics)
        .filter(OperationalMetrics.timestamp >= naive_start)
        .filter(OperationalMetrics.timestamp <= naive_end)
        .order_by(asc(OperationalMetrics.timestamp))
        .all()
    )

    if not rows:
        rows = [latest_metric]

    # Shift aggregate metrics
    arrivals = [r.ed_arrivals for r in rows]
    patients = [r.ed_patients for r in rows]
    beds = [r.available_beds for r in rows]
    icu = [r.icu_occupancy_pct for r in rows]
    nurses = [r.nurses_available for r in rows]
    doctors = [r.doctors_available for r in rows]

    peak_idx = int(np.argmax(arrivals))
    peak_record = rows[peak_idx]

    # Query anomaly events that occurred in this shift window
    anomalies = (
        db.query(AnomalyEvent)
        .filter(AnomalyEvent.timestamp >= naive_start)
        .filter(AnomalyEvent.timestamp <= naive_end)
        .order_by(asc(AnomalyEvent.timestamp))
        .all()
    )

    # Contextual handover forecasts and optimization recommendations
    try:
        current_state = get_current_hospital_state(db)
    except Exception:
        current_state = None

    try:
        forecast = get_ed_forecast(db)
    except Exception:
        forecast = None

    try:
        recommendations = get_resource_recommendations(db)
    except Exception:
        recommendations = None

    return {
        "hours": hours,
        "start_time": to_utc(rows[0].timestamp),
        "end_time": end_time,
        "rows": rows,
        "total_records": len(rows),
        "aggregates": {
            "total_arrivals": int(np.sum(arrivals)),
            "avg_arrivals": round(float(np.mean(arrivals)), 1),
            "peak_arrivals": int(arrivals[peak_idx]),
            "peak_arrival_time": to_utc(peak_record.timestamp),
            "avg_patients": round(float(np.mean(patients)), 1),
            "peak_patients": int(np.max(patients)),
            "min_beds": int(np.min(beds)),
            "avg_beds": round(float(np.mean(beds)), 1),
            "max_icu": round(float(np.max(icu)), 1),
            "avg_icu": round(float(np.mean(icu)), 1),
            "avg_nurses": round(float(np.mean(nurses)), 1),
            "avg_doctors": round(float(np.mean(doctors)), 1),
            "avg_pt_nurse_ratio": round(float(np.mean(patients) / max(np.mean(nurses), 1)), 2),
            "avg_pt_doctor_ratio": round(float(np.mean(patients) / max(np.mean(doctors), 1)), 2),
        },
        "anomalies": anomalies,
        "current_state": current_state,
        "forecast": forecast,
        "recommendations": recommendations,
        "generated_at": datetime.now(timezone.utc),
    }


def generate_shift_pdf(data: Dict[str, Any]) -> bytes:
    """Generates an executive, printable PDF shift report using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Brand color palette
    c_teal = colors.HexColor("#0A6E73")
    c_teal_dark = colors.HexColor("#08565A")
    c_ink = colors.HexColor("#122B32")
    c_muted = colors.HexColor("#4A6369")
    c_canvas = colors.HexColor("#F3F6F4")
    c_line = colors.HexColor("#D5DFDB")
    c_red = colors.HexColor("#C92A2A")
    c_amber = colors.HexColor("#D97706")
    c_green = colors.HexColor("#166534")

    # Typography styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=c_teal_dark,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=c_muted,
    )
    section_h1 = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=c_ink,
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=c_ink,
    )
    body_bold = ParagraphStyle(
        "BodyBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=c_ink,
    )
    small_muted = ParagraphStyle(
        "SmallMuted",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=c_muted,
    )

    story = []

    # 1. Header Banner & Title
    story.append(Paragraph("AI HOSPITAL OPERATIONS FORECASTING & RESOURCE OPTIMIZATION", subtitle_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph(f"Operational Shift Handover Report ({data['hours']}-Hour Window)", title_style))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            f"<b>Shift Window:</b> {data['start_time'].strftime('%b %d, %Y %H:%M UTC')} &mdash; {data['end_time'].strftime('%b %d, %Y %H:%M UTC')} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Generated:</b> {data['generated_at'].strftime('%b %d, %Y %H:%M UTC')}",
            small_muted,
        )
    )
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_teal, spaceBefore=2, spaceAfter=10))

    # 2. Executive Shift KPI Scorecard (4 Summary Tiles)
    agg = data["aggregates"]
    scorecard_data = [
        [
            Paragraph(f"<font color='#4A6369'><b>TOTAL ED INFLOW</b></font><br/><font size=14 color='#122B32'><b>{agg['total_arrivals']}</b></font> arrivals<br/><font size=7.5 color='#4A6369'>Avg: {agg['avg_arrivals']} / hr</font>", body_style),
            Paragraph(f"<font color='#4A6369'><b>PEAK ARRIVAL SURGE</b></font><br/><font size=14 color='#C92A2A'><b>{agg['peak_arrivals']}</b></font> / hr<br/><font size=7.5 color='#4A6369'>At: {agg['peak_arrival_time'].strftime('%H:%M UTC')}</font>", body_style),
            Paragraph(f"<font color='#4A6369'><b>INPATIENT BED HEADROOM</b></font><br/><font size=14 color='#122B32'><b>{agg['avg_beds']}</b></font> avg beds<br/><font size=7.5 color='#4A6369'>Critical Min: {agg['min_beds']} beds</font>", body_style),
            Paragraph(f"<font color='#4A6369'><b>ICU OCCUPANCY LOAD</b></font><br/><font size=14 color='{'#C92A2A' if agg['max_icu'] >= 85 else '#122B32'}'><b>{agg['avg_icu']}%</b></font> avg<br/><font size=7.5 color='#4A6369'>Peak: {agg['max_icu']}%</font>", body_style),
        ]
    ]
    scorecard_table = Table(scorecard_data, colWidths=[135, 135, 135, 135])
    scorecard_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_canvas),
            ("BOX", (0, 0), (-1, -1), 1, c_line),
            ("INNERGRID", (0, 0), (-1, -1), 1, c_line),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    story.append(scorecard_table)
    story.append(Spacer(1, 10))

    # 3. Staffing & Department Load Overview
    story.append(Paragraph("1. Staffing & Department Load Metrics", section_h1))
    staff_data = [
        [
            Paragraph("<b>Metric</b>", body_bold),
            Paragraph("<b>Shift Average</b>", body_bold),
            Paragraph("<b>Current Value</b>", body_bold),
            Paragraph("<b>Operating Threshold / Benchmark</b>", body_bold),
        ],
        [
            Paragraph("ED Nurses on Duty", body_style),
            Paragraph(f"{agg['avg_nurses']} nurses", body_style),
            Paragraph(f"{data['rows'][-1].nurses_available} nurses", body_style),
            Paragraph("Nominal baseline: ~10 (Min ratio &le; 4.0 pts/nurse)", small_muted),
        ],
        [
            Paragraph("ED Doctors on Duty", body_style),
            Paragraph(f"{agg['avg_doctors']} doctors", body_style),
            Paragraph(f"{data['rows'][-1].doctors_available} doctors", body_style),
            Paragraph("Nominal baseline: ~4 (Min ratio &le; 8.0 pts/doctor)", small_muted),
        ],
        [
            Paragraph("Patient-to-Nurse Ratio", body_style),
            Paragraph(f"{agg['avg_pt_nurse_ratio']}:1", body_style),
            Paragraph(f"{round(data['rows'][-1].ed_patients / max(data['rows'][-1].nurses_available, 1), 2)}:1", body_style),
            Paragraph("Target &le; 3.5:1 &bull; Alert &gt; 4.0:1", small_muted),
        ],
        [
            Paragraph("Patient-to-Doctor Ratio", body_style),
            Paragraph(f"{agg['avg_pt_doctor_ratio']}:1", body_style),
            Paragraph(f"{round(data['rows'][-1].ed_patients / max(data['rows'][-1].doctors_available, 1), 2)}:1", body_style),
            Paragraph("Target &le; 8.0:1 &bull; Alert &gt; 10.0:1", small_muted),
        ],
    ]
    staff_table = Table(staff_data, colWidths=[150, 100, 100, 190])
    staff_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), c_canvas),
            ("BOX", (0, 0), (-1, -1), 0.5, c_line),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, c_line),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(staff_table)
    story.append(Spacer(1, 10))

    # 4. Hourly Operational Telemetry Log (up to 24 rows)
    story.append(Paragraph(f"2. Hourly Telemetry Log ({len(data['rows'])} Observations)", section_h1))
    table_rows = [
        [
            Paragraph("<b>Timestamp (UTC)</b>", body_bold),
            Paragraph("<b>Arrivals</b>", body_bold),
            Paragraph("<b>ED Pts</b>", body_bold),
            Paragraph("<b>Beds</b>", body_bold),
            Paragraph("<b>ICU %</b>", body_bold),
            Paragraph("<b>Nurses</b>", body_bold),
            Paragraph("<b>Doctors</b>", body_bold),
            Paragraph("<b>Pt/Nurse</b>", body_bold),
        ]
    ]

    for r in data["rows"]:
        ts_str = to_utc(r.timestamp).strftime("%b %d %H:%M")
        ratio = round(r.ed_patients / max(r.nurses_available, 1), 1)
        ratio_color = "#C92A2A" if ratio > 4.0 else "#122B32"
        icu_color = "#C92A2A" if r.icu_occupancy_pct >= 85.0 else "#122B32"

        table_rows.append([
            Paragraph(ts_str, small_muted),
            Paragraph(str(r.ed_arrivals), body_style),
            Paragraph(str(r.ed_patients), body_style),
            Paragraph(str(r.available_beds), body_style),
            Paragraph(f"<font color='{icu_color}'>{r.icu_occupancy_pct}%</font>", body_style),
            Paragraph(str(r.nurses_available), body_style),
            Paragraph(str(r.doctors_available), body_style),
            Paragraph(f"<font color='{ratio_color}'>{ratio}:1</font>", body_style),
        ])

    telemetry_table = Table(table_rows, colWidths=[95, 60, 60, 60, 65, 65, 65, 70])
    telemetry_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), c_teal),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.5, c_line),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, c_line),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, c_canvas]),
            ("PADDING", (0, 0), (-1, -1), 3),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(telemetry_table)
    story.append(Spacer(1, 10))

    # 5. Shift Incident & Anomaly Audit Log
    story.append(Paragraph(f"3. Shift Incident & Anomaly Audit ({len(data['anomalies'])} Events Logged)", section_h1))
    if data["anomalies"]:
        anomaly_rows = [
            [
                Paragraph("<b>Timestamp (UTC)</b>", body_bold),
                Paragraph("<b>Severity</b>", body_bold),
                Paragraph("<b>Observed vs Expected</b>", body_bold),
                Paragraph("<b>Deviation</b>", body_bold),
                Paragraph("<b>Status</b>", body_bold),
                Paragraph("<b>Clinical Explanation</b>", body_bold),
            ]
        ]
        for a in data["anomalies"]:
            a_ts = to_utc(a.timestamp).strftime("%b %d %H:%M")
            sev_color = "#C92A2A" if "CRITICAL" in a.severity else ("#D97706" if "MODERATE" in a.severity else "#2563EB")
            status_text = "RESOLVED" if a.resolved else "ACTIVE"
            status_color = "#166534" if a.resolved else "#C92A2A"

            anomaly_rows.append([
                Paragraph(a_ts, small_muted),
                Paragraph(f"<font color='{sev_color}'><b>{a.severity}</b></font>", small_muted),
                Paragraph(f"{a.observed_value} vs {round(a.expected_baseline, 1)}", small_muted),
                Paragraph(f"{'+' if a.deviation_pct > 0 else ''}{round(a.deviation_pct, 1)}%", small_muted),
                Paragraph(f"<font color='{status_color}'><b>{status_text}</b></font>", small_muted),
                Paragraph(a.explanation, small_muted),
            ])

        anomaly_table = Table(anomaly_rows, colWidths=[80, 85, 75, 55, 60, 185])
        anomaly_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), c_canvas),
                ("BOX", (0, 0), (-1, -1), 0.5, c_line),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, c_line),
                ("PADDING", (0, 0), (-1, -1), 3),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        story.append(anomaly_table)
    else:
        story.append(
            Paragraph(
                "<i>No anomalous arrival surges or drops were detected during this shift window. Operations remained within expected baseline tolerances.</i>",
                small_muted,
            )
        )
    story.append(Spacer(1, 10))

    # 6. Shift Handover Context: Forecast & Optimization Actions
    handover_elements = []
    handover_elements.append(Paragraph("4. Shift Handover Briefing & Advisory Optimization", section_h1))

    forecast_info = "Forecasting model uninitialized."
    if data["forecast"]:
        f = data["forecast"]
        diff = round(float(f.predicted_ed_arrivals) - float(f.current_ed_arrivals), 1)
        model_name = f.model_metadata.model_name if f.model_metadata else "HistGBR"
        forecast_info = f"<b>Next-Hour ED Arrival Projection:</b> <b>{f.predicted_ed_arrivals} arrivals</b> (Current: {f.current_ed_arrivals}, &Delta;: {diff:+0.1f}) using model <i>{model_name}</i>. Target timestamp: {f.target_timestamp.strftime('%H:%M UTC')}."

    recs_info = []
    if data["recommendations"] and data["recommendations"].recommendations:
        for r in data["recommendations"].recommendations:
            badge_color = "#C92A2A" if r.priority == "CRITICAL" else ("#D97706" if r.priority == "HIGH" else "#0A6E73")
            recs_info.append(
                f"&bull; <font color='{badge_color}'><b>[{r.priority}] {r.category} ({r.id})</b></font>: {r.action} &mdash; <i>{r.rationale}</i>"
            )
    else:
        recs_info.append("<i>Standard operational routine. No staffing reallocations currently advised.</i>")

    handover_content = [
        [
            Paragraph(
                f"<font color='#0A6E73'><b>NEXT-HOUR INFLOW OUTLOOK</b></font><br/>{forecast_info}<br/><br/>"
                f"<font color='#0A6E73'><b>HANDOVER RECOMMENDATIONS FOR INCOMING SUPERVISOR</b></font><br/>"
                + "<br/>".join(recs_info),
                body_style,
            )
        ]
    ]
    handover_table = Table(handover_content, colWidths=[540])
    handover_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_canvas),
            ("BOX", (0, 0), (-1, -1), 1, c_line),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    handover_elements.append(handover_table)
    story.append(KeepTogether(handover_elements))

    # Build the document
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_shift_excel(data: Dict[str, Any]) -> bytes:
    """Generates an executive, multi-worksheet Excel workbook using openpyxl."""
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Styles
    f_title = Font(name="Calibri", size=14, bold=True, color="08565A")
    f_section = Font(name="Calibri", size=11, bold=True, color="122B32")
    f_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    f_body = Font(name="Calibri", size=10, color="122B32")
    f_bold = Font(name="Calibri", size=10, bold=True, color="122B32")
    f_muted = Font(name="Calibri", size=9, italic=True, color="4A6369")

    fill_teal = PatternFill(start_color="0A6E73", end_color="0A6E73", fill_type="solid")
    fill_canvas = PatternFill(start_color="F3F6F4", end_color="F3F6F4", fill_type="solid")
    fill_alert = PatternFill(start_color="FFF5F5", end_color="FFF5F5", fill_type="solid")

    thin_border = Border(
        left=Side(style="thin", color="D5DFDB"),
        right=Side(style="thin", color="D5DFDB"),
        top=Side(style="thin", color="D5DFDB"),
        bottom=Side(style="thin", color="D5DFDB"),
    )

    # ================= Sheet 1: Shift Summary =================
    ws1 = wb.create_sheet(title="Shift Summary")
    ws1.views.sheetView[0].showGridLines = True

    ws1.append(["AI-Based Hospital Operations Forecasting and Resource Optimization System"])
    ws1.cell(1, 1).font = f_title
    ws1.append([f"Executive Shift Handover Report ({data['hours']}-Hour Window)"])
    ws1.cell(2, 1).font = f_section
    ws1.append([
        f"Shift: {data['start_time'].strftime('%Y-%m-%d %H:%M UTC')} to {data['end_time'].strftime('%Y-%m-%d %H:%M UTC')} | Generated: {data['generated_at'].strftime('%Y-%m-%d %H:%M UTC')}"
    ])
    ws1.cell(3, 1).font = f_muted
    ws1.append([])

    # KPI Summary Table
    ws1.append(["Shift Aggregate Metric", "Value", "Operating Benchmark / Reference"])
    for col in range(1, 4):
        c = ws1.cell(5, col)
        c.font = f_header
        c.fill = fill_teal
        c.alignment = Alignment(horizontal="left", vertical="center")

    agg = data["aggregates"]
    kpis = [
        ("Total ED Arrivals", agg["total_arrivals"], f"Avg: {agg['avg_arrivals']} arrivals / hr"),
        ("Peak Arrival Surge", f"{agg['peak_arrivals']} / hr", f"Recorded at {agg['peak_arrival_time'].strftime('%H:%M UTC')}"),
        ("Active ED Patients (Average)", agg["avg_patients"], f"Shift Peak: {agg['peak_patients']} active patients"),
        ("Inpatient Available Beds (Average)", agg["avg_beds"], f"Critical Minimum: {agg['min_beds']} beds available"),
        ("ICU Occupancy Rate (Average)", f"{agg['avg_icu']}%", f"Shift Peak: {agg['max_icu']}% (Alert &ge; 85%)"),
        ("Nurses on Duty (Average)", agg["avg_nurses"], f"Current on duty: {data['rows'][-1].nurses_available}"),
        ("Doctors on Duty (Average)", agg["avg_doctors"], f"Current on duty: {data['rows'][-1].doctors_available}"),
        ("Patient-to-Nurse Ratio (Average)", f"{agg['avg_pt_nurse_ratio']}:1", "Target &le; 3.5:1 (Critical &gt; 4.0:1)"),
        ("Patient-to-Doctor Ratio (Average)", f"{agg['avg_pt_doctor_ratio']}:1", "Target &le; 8.0:1 (Critical &gt; 10.0:1)"),
    ]

    for kpi in kpis:
        ws1.append(list(kpi))
        row_idx = ws1.max_row
        for col_idx in range(1, 4):
            cell = ws1.cell(row_idx, col_idx)
            cell.font = f_bold if col_idx == 2 else f_body
            cell.border = thin_border
            if row_idx % 2 == 1:
                cell.fill = fill_canvas

    ws1.append([])
    ws1.append(["Shift Handover Briefing & Optimization Advisory"])
    ws1.cell(ws1.max_row, 1).font = f_section

    if data["forecast"]:
        f = data["forecast"]
        diff = round(float(f.predicted_ed_arrivals) - float(f.current_ed_arrivals), 1)
        model_name = f.model_metadata.model_name if f.model_metadata else "HistGBR"
        ws1.append([f"Next-Hour ED Arrival Projection: {f.predicted_ed_arrivals} arrivals (Current: {f.current_ed_arrivals}, Delta: {diff:+0.1f}) [Model: {model_name}]"])
        ws1.cell(ws1.max_row, 1).font = f_body

    if data["recommendations"] and data["recommendations"].recommendations:
        for r in data["recommendations"].recommendations:
            ws1.append([f"[{r.priority}] {r.category} ({r.id}): {r.action} - {r.rationale}"])
            ws1.cell(ws1.max_row, 1).font = f_body

    # ================= Sheet 2: Hourly Telemetry =================
    ws2 = wb.create_sheet(title="Hourly Telemetry")
    ws2.views.sheetView[0].showGridLines = True

    headers = [
        "Timestamp (UTC)",
        "ED Arrivals",
        "Active ED Patients",
        "Available Beds",
        "ICU Occupancy %",
        "Nurses Available",
        "Doctors Available",
        "Pt / Nurse Ratio",
        "Pt / Doctor Ratio",
    ]
    ws2.append(headers)
    for col in range(1, len(headers) + 1):
        c = ws2.cell(1, col)
        c.font = f_header
        c.fill = fill_teal
        c.alignment = Alignment(horizontal="center", vertical="center")

    for r in data["rows"]:
        ts_str = to_utc(r.timestamp).strftime("%Y-%m-%d %H:%M")
        pt_nurse = round(r.ed_patients / max(r.nurses_available, 1), 2)
        pt_doc = round(r.ed_patients / max(r.doctors_available, 1), 2)
        ws2.append([
            ts_str,
            r.ed_arrivals,
            r.ed_patients,
            r.available_beds,
            r.icu_occupancy_pct,
            r.nurses_available,
            r.doctors_available,
            pt_nurse,
            pt_doc,
        ])
        curr_row = ws2.max_row
        for col_idx in range(1, len(headers) + 1):
            cell = ws2.cell(curr_row, col_idx)
            cell.font = f_body
            cell.border = thin_border
            if curr_row % 2 == 1:
                cell.fill = fill_canvas
            if col_idx >= 2:
                cell.alignment = Alignment(horizontal="right")

    # ================= Sheet 3: Anomaly Alerts =================
    ws3 = wb.create_sheet(title="Anomaly Incident Log")
    ws3.views.sheetView[0].showGridLines = True

    a_headers = [
        "Timestamp (UTC)",
        "Severity",
        "Observed Arrivals",
        "Expected Baseline",
        "Deviation %",
        "Resolution Status",
        "Clinical Explanation",
    ]
    ws3.append(a_headers)
    for col in range(1, len(a_headers) + 1):
        c = ws3.cell(1, col)
        c.font = f_header
        c.fill = fill_teal
        c.alignment = Alignment(horizontal="center", vertical="center")

    if data["anomalies"]:
        for a in data["anomalies"]:
            a_ts = to_utc(a.timestamp).strftime("%Y-%m-%d %H:%M")
            ws3.append([
                a_ts,
                a.severity,
                a.observed_value,
                round(a.expected_baseline, 1),
                f"{'+' if a.deviation_pct > 0 else ''}{round(a.deviation_pct, 1)}%",
                "RESOLVED" if a.resolved else "ACTIVE",
                a.explanation,
            ])
            curr_row = ws3.max_row
            for col_idx in range(1, len(a_headers) + 1):
                cell = ws3.cell(curr_row, col_idx)
                cell.font = f_body
                cell.border = thin_border
                if not a.resolved:
                    cell.fill = fill_alert
    else:
        ws3.append(["No anomalous surge or drop incidents logged during this shift window."])

    # Auto-adjust column widths across all sheets
    for ws in [ws1, ws2, ws3]:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = str(cell.value or "")
                if len(val) > max_len and len(val) < 80:
                    max_len = len(val)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
