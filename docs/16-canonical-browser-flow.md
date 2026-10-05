# Canonical browser product flow

## Decision

The FastAPI application is the canonical VeriCar product surface for the browser. It serves frontend/index.html at /, serves the browser assets under /assets, and exposes the application API under /api.

The older Streamlit application remains in app/main.py for compatibility and development workflows, but it is not the canonical browser product surface.

## Request flow

Browser
  │
  ├── GET /health
  │
  ├── GET /api/vehicles/{vehicle_id}
  │       └── durable SQLite history
  │
  ├── GET /api/vehicles/{vehicle_id}/assessment/explanation
  │       └── historical-memory assessment + optional explanation
  │
  └── POST /api/reports
          └── durable SQLite persistence + idempotent memory processing

The browser retrieves durable local history before requesting the memory-backed assessment. This makes the durable history endpoint part of the normal product flow rather than an API that exists only for programmatic consumers.

## Failure semantics

- If the vehicle has no durable record and no accepted reports, the history request returns 404 VEHICLE_NOT_FOUND.
- If durable history exists but the external memory service is unavailable, the browser keeps the local history visible and marks the assessment as unavailable.
- Memory unavailability is never rendered as an empty history.
- The browser continues to send an Idempotency-Key for report submission and reuses that key until the form is reset.

## Source-of-truth boundaries

Durable SQLite history is the source for accepted browser/API reports. Hindsight provides historical-memory context for assessment. Deterministic assessment logic remains authoritative for the assessment itself. The optional LLM explanation does not replace the deterministic result.

## Local development

Run the canonical browser product with the FastAPI application:

    uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

Then open:

    http://127.0.0.1:8000/

Do not open frontend/index.html directly from the filesystem; the page expects the same-origin FastAPI routes.

The Streamlit application can still be used separately when working on the existing Streamlit workflow, but new browser-facing product behavior should target the FastAPI-served application and its API contracts.
