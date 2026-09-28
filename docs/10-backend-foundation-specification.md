# VeriCar — Backend Foundation Specification

## 1. Purpose

This stage creates the minimal working Python backend for VeriCar.

The goal is to establish:

- isolated Python environment
- dependency management
- configuration loading
- FastAPI application
- API routing
- health endpoint
- basic error handling
- test framework
- clean startup

This stage must NOT implement:

- Hindsight integration
- Groq integration
- evidence scoring
- report processing
- frontend
- authentication
- complex database infrastructure

The objective is to prove that the backend foundation works before adding external integrations.

---

## 2. Technology

Backend:

- Python
- FastAPI
- Uvicorn
- Pydantic / Pydantic Settings as required
- pytest

The exact Hindsight and Groq packages will be added later after their actual APIs are verified.

---

## 3. Backend Structure

Create:

backend/
|
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── health.py
│   │
│   ├── models/
│   │   └── __init__.py
│   │
│   ├── services/
│   │   └── __init__.py
│   │
│   └── core/
│       └── __init__.py
│
└── tests/
    ├── __init__.py
    └── test_health.py

Do not create empty service modules for future functionality unless they are required by the implementation.

The structure may evolve as real responsibilities are added.

---

## 4. Python Virtual Environment

Create an isolated virtual environment inside the backend directory.

Conceptually:

backend/
└── .venv/

The virtual environment must not be committed to Git.

The project should use the selected Python development version consistently.

---

## 5. Dependencies

Install only the dependencies required for this stage.

Required categories:

- FastAPI
- Uvicorn
- Pydantic configuration support if needed
- pytest

Do not install Hindsight or Groq yet unless their installation is required specifically to verify the environment.

Those integrations belong to later stages.

---

## 6. requirements.txt

Create:

backend/requirements.txt

It should contain only dependencies actually required by the current backend.

Example categories:

fastapi
uvicorn
pydantic-settings
pytest

Exact versions should be pinned or constrained deliberately rather than generated randomly.

---

## 7. Configuration

Create:

backend/app/config.py

Configuration responsibilities:

- load environment variables
- provide application settings
- validate required configuration
- provide sensible development defaults where appropriate

At this stage, configuration should include only backend-level settings.

Example:

APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000

Hindsight and Groq configuration will be added later.

---

## 8. Environment File

The repository root should contain:

.env.example

Example:

APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000

Do not place real secrets in this file.

A local `.env` file may be created during development.

The `.env` file must remain ignored by Git.

---

## 9. Application Entry Point

Create:

backend/app/main.py

Responsibilities:

- create the FastAPI application
- define application metadata
- register API routers
- configure global error handling only when needed

Business logic must not be placed in `main.py`.

Conceptually:

FastAPI application
        |
        +-- health router
        |
        +-- future report router
        |
        +-- future vehicle router
        |
        +-- future assessment router

---

## 10. Health Endpoint

Create:

GET /health

Expected response:

{
    "status": "ok"
}

Purpose:

Verify that the backend process is running.

This endpoint must NOT depend on:

- Hindsight
- Groq
- database
- frontend

It should work even when all external services are unavailable.

---

## 11. Health Router

Create:

backend/app/api/routes/health.py

The health router should contain the `/health` endpoint.

Do not place the endpoint directly into `main.py`.

This keeps routing modular while the application remains small.

---

## 12. API Prefix

Future API endpoints should use:

/api/

For example:

/api/reports
/api/vehicles/{vehicle_id}
/api/vehicles/{vehicle_id}/assessment

The health endpoint remains:

/health

This keeps infrastructure health separate from application APIs.

---

## 13. Error Handling

The backend should allow FastAPI's normal HTTP error handling to operate initially.

Do not create a large custom exception framework at this stage.

When custom application errors become necessary, introduce them based on an actual requirement.

Avoid:

try:
    ...
except:
    pass

Errors must never be silently swallowed.

---

## 14. Test Framework

Use pytest.

Create:

backend/tests/test_health.py

The first test should verify:

GET /health

returns:

HTTP 200

and:

{
    "status": "ok"
}

The test should use FastAPI's supported test client mechanism.

---

## 15. First Verification

After implementation, verify the following sequence:

1. Activate the virtual environment.

2. Install requirements.

3. Start the FastAPI server.

4. Open:

http://127.0.0.1:8000/health

5. Confirm the response:

{
    "status": "ok"
}

6. Open:

http://127.0.0.1:8000/docs

7. Confirm the FastAPI documentation interface loads.

8. Run pytest.

Expected result:

All tests pass.

---

## 16. Development Server

The development server should run using Uvicorn.

Conceptually:

uvicorn app.main:app --reload

The final README should document the exact command used by the project.

The `--reload` option is for development only.

---

## 17. API Documentation

FastAPI should provide its standard development documentation.

Expected:

/docs

and, if enabled by default:

/redoc

Do not build a custom API documentation system.

---

## 18. Logging

At this stage, keep logging minimal.

The backend should be able to report:

- application startup
- application shutdown
- unexpected errors

Do not introduce a complex logging infrastructure.

External-service logging will be designed when Hindsight and Groq are integrated.

---

## 19. CORS

Do not enable unrestricted CORS unnecessarily.

When the frontend is introduced, configure CORS specifically for the development and production frontend origins.

For this stage, CORS should not be added unless required by the local development setup.

---

## 20. Security

At this stage:

- no API keys
- no secrets in source code
- `.env` ignored
- no credentials returned by endpoints
- no unnecessary user data
- no authentication system

Security requirements will expand when external services and report submission are implemented.

---

## 21. Definition of Done

Backend Foundation is complete when:

[ ] backend directory exists

[ ] Python virtual environment works

[ ] required dependencies install successfully

[ ] requirements.txt exists

[ ] .env.example exists

[ ] .env is ignored by Git

[ ] FastAPI application starts

[ ] /health returns HTTP 200

[ ] /health returns {"status": "ok"}

[ ] /docs loads

[ ] pytest executes successfully

[ ] health test passes

[ ] no secrets are committed

[ ] no Hindsight code exists yet

[ ] no Groq code exists yet

[ ] no scoring code exists yet

[ ] no frontend code is required yet

---

## 22. Explicit Scope Boundary

At the end of this stage, the system should look like:

Browser / API Client
        |
        v
Python FastAPI Backend
        |
        v
GET /health
        |
        v
{"status": "ok"}

Nothing more is required.

The backend foundation is considered successful when this minimal system runs reliably.

---

## 23. Next Stage

After Backend Foundation is verified, move to:

11 — Hindsight Integration

That stage will:

- verify the actual Hindsight API
- configure Hindsight credentials
- implement MemoryService
- implement vehicle memory writes
- implement source memory writes
- implement memory retrieval
- test retain/retrieve behavior
- verify that Hindsight is genuinely persistent

Do not implement scoring or Groq until Hindsight memory has been successfully verified.