from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.assessment_pipeline import AssessmentPipelineResult
from core.condition import ConditionRecord
from core.models import Car, UNKNOWN


def _value(value: object) -> str:
    if value is None or value == "":
        return UNKNOWN
    return str(value)


def _inr(value: int | None) -> str:
    return UNKNOWN if value is None else f"INR {value:,}"


def _join_findings(findings: tuple[str, ...]) -> str:
    return "<br/>".join(f"• {finding}" for finding in findings) or "None recorded."


def build_assessment_pdf(
    car: Car,
    condition: ConditionRecord,
    result: AssessmentPipelineResult,
    *,
    generated_at: datetime | None = None,
) -> bytes:
    """Build a deterministic assessment report from stored evidence and assessment output."""
    if result.assessment is None:
        raise ValueError("A completed assessment is required to build the PDF report.")
    if result.profile_resolution.profile is None:
        raise ValueError("An expected profile is required to build the PDF report.")

    assessment = result.assessment
    profile = result.profile_resolution.profile
    generated_at = generated_at or datetime.now(timezone.utc)

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="VeriCar Assessment Report",
        author="VeriCar",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="VeriCarTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        alignment=TA_LEFT,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="VeriCarSection",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        spaceBefore=12,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="VeriCarBody",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13,
    ))
    styles.add(ParagraphStyle(
        name="VeriCarSmall",
        parent=styles["BodyText"],
        fontSize=7.5,
        leading=10,
        textColor=colors.grey,
    ))

    story: list[object] = [
        Paragraph("VeriCar Assessment Report", styles["VeriCarTitle"]),
        Paragraph(
            "Evidence-based used-vehicle assessment generated from the recorded vehicle condition "
            "and deterministic assessment pipeline.",
            styles["VeriCarBody"],
        ),
        Spacer(1, 5 * mm),
        Paragraph("Vehicle identity", styles["VeriCarSection"]),
    ]

    identity_rows = [
        ["Vehicle ID", _value(car.car_id), "Memory key", _value(car.memory_key)],
        ["Brand", _value(car.brand), "Model", _value(car.model)],
        ["Manufacture year", _value(car.manufacture_year), "Variant", _value(car.variant)],
        ["Fuel type", _value(car.fuel_type), "Transmission", _value(car.transmission)],
        ["VIN / chassis", _value(car.vin), "Registration state", _value(car.registration_state)],
        ["Odometer", f"{car.odometer_km:,} km" if car.odometer_km is not None else UNKNOWN,
         "Asking price", _inr(car.asking_price_inr)],
    ]
    story.append(_table(identity_rows))

    story.extend([
        Paragraph("Recorded condition", styles["VeriCarSection"]),
        _table([
            ["Repairs recorded", str(len(condition.repairs)), "Services recorded", str(len(condition.services))],
            ["Accident history", _value(condition.accident_status),
             "Repainted panels", _value(condition.repainted_panels)],
            ["Airbag deployed", _value(condition.airbag_deployed),
             "Seller claims", _value(condition.seller_claims)],
        ]),
        Paragraph("Assessment", styles["VeriCarSection"]),
        _table([
            ["Verdict", assessment.verdict, "Confidence", f"{assessment.confidence}%"],
            ["Near-term repair range", f"{_inr(assessment.near_term_repair_range_inr[0])} – {_inr(assessment.near_term_repair_range_inr[1])}",
             "Negotiation reduction", _inr(assessment.negotiation_reduction_inr)],
        ]),
        Paragraph("Findings", styles["VeriCarSection"]),
        Paragraph("<b>Critical findings</b>", styles["VeriCarBody"]),
        Paragraph(_join_findings(assessment.critical_findings), styles["VeriCarBody"]),
        Spacer(1, 2 * mm),
        Paragraph("<b>Warnings</b>", styles["VeriCarBody"]),
        Paragraph(_join_findings(assessment.warning_findings), styles["VeriCarBody"]),
        Spacer(1, 2 * mm),
        Paragraph("<b>Information</b>", styles["VeriCarBody"]),
        Paragraph(_join_findings(assessment.info_findings), styles["VeriCarBody"]),
        Paragraph("Next checks", styles["VeriCarSection"]),
        Paragraph(
            "<br/>".join(f"• {check}" for check in assessment.next_checks) or "None recorded.",
            styles["VeriCarBody"],
        ),
        Paragraph("Expected profile", styles["VeriCarSection"]),
        _table([
            ["Profile key", result.profile_resolution.profile_key],
            ["Profile source", _value(profile.source)],
            ["Known issues in profile", "<br/>".join(f"• {item}" for item in profile.known_issues) or "None recorded."],
            ["Maintenance notes", "<br/>".join(f"• {item}" for item in profile.maintenance_notes) or "None recorded."],
        ]),
        Paragraph("Report metadata and limitations", styles["VeriCarSection"]),
        Paragraph(
            f"Generated at: {generated_at.astimezone(timezone.utc).isoformat()}<br/>"
            "Assessment logic is deterministic; the PDF does not add or infer facts beyond the recorded evidence "
            "and assessment result.<br/>"
            "Reference profiles are synthetic seed data until external sources are integrated. "
            "Synthetic/demo data is not a substitute for an independent inspection, document verification, "
            "service-record verification, or professional mechanical advice.<br/>"
            "Unknown evidence remains unknown and may reduce confidence. A missing external memory source does not "
            "mean that the vehicle has no history.",
            styles["VeriCarSmall"],
        ),
    ])

    document.build(story)
    return buffer.getvalue()


def _table(rows: list[list[str]]) -> Table:
    column_count = max(len(row) for row in rows)
    if column_count == 2:
        widths = [58 * mm, 128 * mm]
        label_columns = (0,)
    elif column_count == 4:
        widths = [35 * mm, 58 * mm, 35 * mm, 58 * mm]
        label_columns = (0, 2)
    else:
        widths = [186 * mm / column_count] * column_count
        label_columns = ()
    table = Table(rows, colWidths=widths, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 11),
        *[
            ("BACKGROUND", (column, 0), (column, -1), colors.whitesmoke)
            for column in label_columns
        ],
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table
