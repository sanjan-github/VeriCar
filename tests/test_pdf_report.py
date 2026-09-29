from datetime import date, datetime, timezone

from pypdf import PdfReader

from core.assessment_pipeline import run_assessment
from core.database import Database
from core.demo_scenarios import get_demo_scenario
from core.pdf_report import build_assessment_pdf


def test_assessment_pdf_contains_required_sections(tmp_path):
    scenario = get_demo_scenario("critical")
    result = run_assessment(
        scenario.car,
        scenario.condition,
        Database(tmp_path / "report.db"),
        today=date(2026, 9, 29),
    )

    pdf = build_assessment_pdf(
        scenario.car,
        scenario.condition,
        result,
        generated_at=datetime(2026, 9, 29, 10, 30, tzinfo=timezone.utc),
    )

    assert pdf.startswith(b"%PDF")
    reader = PdfReader(__import__("io").BytesIO(pdf))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    for expected in (
        "VeriCar Assessment Report",
        "Vehicle identity",
        "Recorded condition",
        "Assessment",
        "AVOID",
        "Confidence",
        "Findings",
        "Next checks",
        "Expected profile",
        "synthetic seed data",
        "Generated at: 2026-09-29T10:30:00+00:00",
    ):
        assert expected in text


def test_assessment_pdf_rejects_incomplete_pipeline_result(tmp_path):
    scenario = get_demo_scenario("clean")
    result = run_assessment(
        scenario.car,
        scenario.condition,
        Database(tmp_path / "missing.db"),
        today=date(2026, 9, 29),
        seed_missing_profiles=False,
    )

    try:
        build_assessment_pdf(scenario.car, scenario.condition, result)
    except ValueError as exc:
        assert "completed assessment" in str(exc) or "expected profile" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
