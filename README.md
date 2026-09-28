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

The backend, deterministic evidence engine, Hindsight integration, Groq explanation layer, assessment APIs, and browser UI are implemented. The current UI focuses on the transmission shift-behavior finding while the evidence model is validated against representative scenarios.

## Run the application

The browser UI is served by the FastAPI application; do not open `frontend/index.html` directly as a `file://` URL.

```bash
uvicorn backend.app.main:app --reload
```

Then open:

`http://127.0.0.1:8000/`

The application requires a reachable Hindsight service for historical retrieval and report persistence. Configure `HINDSIGHT_BASE_URL` and `HINDSIGHT_API_KEY` as required by the deployed Hindsight instance. Groq is optional: if its API is unavailable, the deterministic evidence assessment and timeline remain available.

### Common local failure modes

- **The page loads but review fails:** verify that Hindsight is running and that `HINDSIGHT_BASE_URL` is reachable.
- **The browser shows a connection error:** verify that FastAPI is running on `127.0.0.1:8000`.
- **Opening `frontend/index.html` directly does not work:** use the FastAPI URL above so the browser can call the backend API.
- **Automated explanation is unavailable:** this does not invalidate the deterministic assessment; Groq is an optional explanation layer.