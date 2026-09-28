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

## Repository Structure

```text
backend/
└── app/
    ├── main.py
    └── config.py

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

It does not calculate evidence confidence or produce a final assessment.

## Status

The backend foundation and structured report-ingestion layer are implemented. Evidence processing, LLM reasoning, assessment APIs, and frontend functionality will be implemented incrementally.
