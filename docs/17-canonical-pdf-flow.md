# Canonical PDF report flow

## Decision

The PDF report is now part of the canonical FastAPI browser product surface.

The browser uses:

    GET /api/vehicles/{vehicle_id}

for durable local history,

    GET /api/vehicles/{vehicle_id}/assessment/explanation

for the historical-memory assessment and optional explanation, and

    GET /api/vehicles/{vehicle_id}/assessment/report.pdf

for the downloadable deterministic assessment report.

## Source of truth

The browser PDF is generated from the same deterministic assessment pipeline used by the existing Streamlit workflow.

The report generator does not call Hindsight or Groq directly. It uses the locally stored vehicle and condition records and the deterministic assessment pipeline. This keeps PDF generation available when external memory or explanation services are unavailable.

The PDF does not create a second assessment implementation. It is a presentation of the existing assessment result.

## Preconditions

A PDF can be generated only when:

- the vehicle exists in durable SQLite storage;
- a saved condition record exists;
- a completed deterministic assessment can be produced;
- an expected profile is available for the vehicle configuration.

Otherwise the API returns an explicit error instead of generating an incomplete report.

## Browser flow

1. The user reviews a vehicle.
2. Durable local history is loaded first.
3. The PDF download action becomes available for that vehicle.
4. The user selects Download inspection report.
5. FastAPI generates the report from durable local vehicle/condition data and the deterministic assessment pipeline.
6. The browser downloads vericar-assessment-{vehicle_id}.pdf.

## Failure semantics

- Unknown vehicle: 404 VEHICLE_NOT_FOUND.
- Vehicle without a saved condition record: 409 CONDITION_NOT_AVAILABLE.
- Vehicle data exists but a completed assessment/profile is not available: 409 REPORT_NOT_READY.
- PDF generation fails unexpectedly: 503 PDF_GENERATION_FAILED.
- PDF generation does not depend on Hindsight availability.

The PDF must not imply that missing external memory means no vehicle history exists.

## Streamlit compatibility

The Streamlit application continues to expose the existing download action. Both browser and Streamlit paths use core.pdf_report.build_assessment_pdf.

## Local verification

Run the complete test suite:

    python -m pytest -q -W default

The canonical PDF API coverage is in:

    tests/test_pdf_report_api.py

The existing PDF document coverage remains in:

    tests/test_pdf_report.py
