# VeriCar

VeriCar is a vehicle-history evidence system that preserves historical reports, evaluates corroboration and contradiction across time, and presents evidence-based assessments.

## Architecture

```text
Browser
   |
   v
Python backend
   |
   +--> Hindsight memory
   |
   +--> Groq LLM
```

The backend is the system orchestrator. External service credentials are never exposed to the frontend.

The deterministic evidence engine is the source of truth for findings, confidence, source counts, support, and contradiction. Groq is used only to explain that evidence in natural language.

## Repository Structure

```text
backend/
└── app/
    ├── main.py
    ├── config.py
    ├── models/
    ├── repositories/
    └── services/

frontend/
docs/
```

## Local Development

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
```

Activate the environment using your operating system's shell, then install dependencies:

```bash
pip install -r requirements.txt
```

Copy the environment template and configure Hindsight. Configure Groq only when explanation generation is needed:

```text
.env
```

Start the API:

```bash
uvicorn backend.app.main:app --reload
```

Health endpoint:

```text
GET http://127.0.0.1:8000/health
```

## API

### Create a vehicle history report

`POST /api/reports`

Example request:

```json
{
  "vehicle_id": "VEH-001",
  "vin": "VIN-VERICAR-001",
  "source_id": "SRC-003",
  "source_type": "mechanic",
  "observed_at": "2026-04-19",
  "text": "Transmission hesitation confirmed during test drive."
}
```

The endpoint validates the report, creates a traceable claim, and stores the report in both vehicle and source Hindsight memory.

### Get deterministic vehicle assessment

`GET /api/vehicles/{vehicle_id}/assessment?issue=transmission_shift_behavior`

The assessment endpoint recalls historical memory, reconstructs evidence records, and applies the deterministic evidence model. It returns evidence status, confidence, support/contradiction weights, source counts, and underlying evidence.

### Get evidence-backed explanation

`GET /api/vehicles/{vehicle_id}/assessment/explanation?issue=transmission_shift_behavior`

This endpoint first computes the deterministic assessment, then asks Groq to explain that assessment.

The LLM receives the structured assessment and evidence only. It is not allowed to create source counts, dates, reliability values, confidence values, diagnoses, or evidence IDs. Returned evidence IDs are validated against the assessment before the explanation is exposed.

If Groq is unavailable or returns invalid output, the deterministic assessment remains available and the response reports:

```json
{
  "explanation_status": "unavailable",
  "explanation": null
}
```

If Hindsight is unavailable, the assessment endpoints return `503 MEMORY_UNAVAILABLE`.

## Status

The backend now supports:

- structured report ingestion
- persistent vehicle and source memory
- historical recall
- deterministic evidence reconstruction
- evidence confidence and contradiction handling
- deterministic vehicle assessment API
- evidence-backed Groq explanation API

Frontend functionality, broader issue extraction, live Hindsight validation, and production deployment remain to be implemented.
