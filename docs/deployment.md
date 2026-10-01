# VeriCar deployment and operations

## Runtime

The supported target is Python 3.11. The application is started with:

    streamlit run app/main.py

The default local URL is:

    http://localhost:8501

## Required configuration

Copy `.env.example` to `.env` for local development and configure only the integrations you use.

Hindsight:

    HINDSIGHT_BASE_URL=https://api.hindsight.vectorize.io
    HINDSIGHT_API_KEY=...
    HINDSIGHT_TIMEOUT=30

Groq is optional for live explanation generation. Its credential must be supplied through the existing environment-variable configuration and must never be committed.

## External services

VeriCar is designed to keep the deterministic assessment usable when optional external services are unavailable.

- SQLite stores structured local evidence.
- Hindsight stores longitudinal vehicle memory when configured.
- NHTSA public APIs provide optional vehicle/recall evidence.
- Groq provides an optional explanation layer.

Provider failures must remain distinguishable from successful lookups that returned no data.

## Deployment checklist

Before deploying:

1. Use Python 3.11.
2. Install from `requirements.txt`.
3. Configure secrets through the hosting platform's secret/environment-variable mechanism.
4. Do not commit `.env`, API keys, or generated SQLite databases.
5. Run:

       python -m compileall -q app core memory tests
       python -m pytest -q

6. Verify the Streamlit application starts.
7. Verify Hindsight connectivity separately from local SQLite operation.
8. Verify optional NHTSA/Groq failures do not prevent deterministic assessment.

## Observability

The application deliberately keeps external-service availability separate from vehicle evidence.

When operational monitoring is added, track at minimum:

- application start failures
- assessment failures
- Hindsight retain failures
- Hindsight recall failures
- NHTSA provider failures
- Groq explanation failures
- test/CI failures

Do not log API keys, raw authentication headers, or unnecessary personal/vehicle identifiers.

## Data and privacy

SQLite is local structured storage. Hindsight is an external memory service when configured.

Before using real customer data in a deployed environment, review:

- data retention requirements
- access controls
- provider terms
- regional/privacy requirements
- whether VIN or registration information should be retained

The current project is a prototype and does not claim production-grade compliance.

## CI

GitHub Actions runs Python compilation and the automated test suite on pushes to `main` and pull requests.

The CI job uses placeholder credentials and does not require live Hindsight, Groq, or NHTSA access.