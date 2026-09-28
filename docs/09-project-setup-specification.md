# VeriCar — Project Setup Specification

## 1. Purpose

This document defines the initial development structure for VeriCar.

The goal is to create a small, understandable repository that supports:

- Python backend development
- Hindsight integration
- Groq integration
- frontend development
- automated testing
- documentation
- local development
- clean GitHub submission

The project should remain intentionally lightweight.

Do not introduce infrastructure or dependencies that are not required by the V1 product.

---

## 2. Repository Structure

The initial repository should use:

VeriCar/
|
├── backend/
│   ├── app/
│   └── tests/
│
├── frontend/
│
├── docs/
│
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt

---

## 3. Backend Structure

The backend is the central orchestrator of VeriCar.

Initial structure:

backend/
|
├── app/
│   ├── main.py
│   ├── config.py
│   │
│   ├── api/
│   │   └── routes/
│   │
│   ├── models/
│   │
│   ├── services/
│   │   ├── memory_service.py
│   │   ├── evidence_service.py
│   │   └── llm_service.py
│   │
│   └── core/
│
└── tests/

The structure should remain flexible.

Do not create additional modules until they have a concrete responsibility.

---

## 4. Backend Responsibilities

The backend is responsible for:

- receiving API requests
- validating input
- managing structured application data
- communicating with Hindsight
- retrieving historical memory
- creating structured evidence
- calculating source reliability
- calculating evidence confidence
- communicating with Groq
- returning structured responses
- handling failures explicitly

The frontend must not directly communicate with Hindsight or Groq.

---

## 5. Frontend Structure

V1 should use a lightweight frontend.

Initial structure:

frontend/
|
├── index.html
├── styles.css
└── app.js

The frontend should communicate with the Python backend through HTTP/JSON.

Do not introduce a frontend framework unless implementation requirements make one necessary.

The initial product does not require React, Next.js, Vue, or another frontend framework.

---

## 6. Documentation

The documentation directory should contain the design documents already created:

docs/
|
├── 01-project-concept.md
├── 02-hackathon-strategy.md
├── 03-system-architecture.md
├── 04-memory-model.md
├── 05-scoring-and-evidence-model.md
├── 06-data-model.md
├── 07-hindsight-memory-design.md
└── 08-hindsight-memory-contract.md

These documents describe the system before implementation.

New implementation decisions should update the relevant documentation rather than creating unnecessary new documents.

---

## 7. Python Environment

The backend should use an isolated Python virtual environment.

Recommended structure:

backend/
|
├── .venv/
├── app/
└── tests/

The virtual environment must not be committed to Git.

The project should use the Python version selected for development and record the required version in the project documentation.

---

## 8. Dependencies

Only dependencies with a concrete V1 responsibility should be installed.

The initial backend dependency categories are:

- web framework
- API server
- environment configuration
- Hindsight client/integration
- Groq client/integration
- testing tools

Do not install libraries merely because they might be useful later.

The exact Hindsight dependency must be determined from the verified Hindsight documentation.

---

## 9. Environment Variables

Secrets must never be hard-coded.

The project should use environment variables for:

- Hindsight configuration
- Hindsight authentication
- Groq API key
- backend configuration where necessary

Example:

HINDSIGHT_API_KEY=...
HINDSIGHT_BASE_URL=...
GROQ_API_KEY=...

The exact variable names should be finalized during implementation based on the actual SDK/API requirements.

---

## 10. .env.example

The repository should contain:

.env.example

It should document the required configuration without containing real credentials.

Example:

HINDSIGHT_API_KEY=
HINDSIGHT_BASE_URL=

GROQ_API_KEY=

APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000

Real `.env` files must not be committed.

---

## 11. .gitignore

The repository must ignore:

- virtual environments
- `.env`
- Python cache files
- test caches
- editor-specific files
- generated temporary files
- local databases if introduced
- build artifacts

The `.env.example` file must remain tracked.

---

## 12. Configuration

Configuration should be centralized.

Conceptually:

app/config.py

Responsibilities:

- load environment variables
- validate required configuration
- expose application configuration
- distinguish development/test configuration where necessary

Secrets should not be printed in logs.

---

## 13. API Entry Point

The backend should expose a single application entry point.

Conceptually:

app/main.py

Responsibilities:

- create the API application
- register routes
- configure middleware if required
- configure error handling
- expose the application object

Do not place business logic inside `main.py`.

---

## 14. Initial API Surface

V1 should start with a small API.

Potential endpoints:

GET /health

POST /api/reports

GET /api/vehicles/{vehicle_id}

GET /api/vehicles/{vehicle_id}/assessment

The exact endpoint set can be adjusted during implementation.

Do not create endpoints for functionality that the V1 product does not need.

---

## 15. Health Endpoint

The health endpoint exists to verify that the backend is running.

Example:

GET /health

Response:

{
  "status": "ok"
}

This endpoint should not require Hindsight or Groq to succeed.

It answers:

> Is the backend process running?

It does not answer:

> Are all external services available?

---

## 16. Report Endpoint

The primary workflow begins with:

POST /api/reports

The endpoint should:

1. validate the report
2. create the structured report
3. interpret the claim
4. write vehicle memory
5. write source memory
6. retrieve relevant historical memory
7. build evidence
8. calculate derived state
9. request explanation from Groq
10. return the updated assessment

This is the central V1 workflow.

---

## 17. Vehicle Endpoint

The vehicle endpoint should provide the information necessary for the frontend to display the vehicle's history.

Example:

GET /api/vehicles/{vehicle_id}

It may return:

- vehicle information
- historical reports
- relevant findings
- evidence references
- history availability

The response should remain structured.

---

## 18. Assessment Endpoint

The assessment endpoint provides the current derived assessment.

Example:

GET /api/vehicles/{vehicle_id}/assessment

It may return:

- findings
- assessment status
- evidence confidence
- supporting evidence count
- contradicting evidence count
- observation span
- explanation

The endpoint must distinguish:

- no history
- available history
- unavailable memory

---

## 19. Service Boundaries

The initial service boundaries are:

MemoryService
    |
    +-- Hindsight writes
    +-- Hindsight retrieval

EvidenceService
    |
    +-- claim interpretation results
    +-- historical evidence
    +-- source reliability
    +-- corroboration
    +-- contradiction
    +-- evidence confidence

LLMService
    |
    +-- Groq requests
    +-- structured interpretation
    +-- explanation generation

These services should have clear responsibilities.

---

## 20. MemoryService

MemoryService isolates Hindsight-specific implementation.

Conceptual interface:

class MemoryService:

    remember_vehicle_event(...)

    remember_source_event(...)

    retrieve_vehicle_history(...)

    retrieve_source_history(...)

The rest of the application should not depend directly on Hindsight SDK calls.

This allows the Hindsight integration to change without rewriting the evidence engine or API routes.

---

## 21. EvidenceService

EvidenceService contains deterministic reasoning.

It should handle:

- source reliability
- source independence
- supporting evidence
- contradicting evidence
- corroboration
- evidence confidence
- assessment status

It must not delegate numerical scoring to the LLM.

---

## 22. LLMService

LLMService isolates Groq-specific functionality.

It should handle:

- structured claim interpretation
- semantic issue grouping
- explanation generation

The LLM must receive controlled input.

User-provided report text must be treated as untrusted content.

The LLM must not be trusted to invent historical facts or numerical evidence.

---

## 23. Data Storage

The application needs a structured persistence mechanism for:

- vehicles
- sources
- reports
- claims
- evidence
- findings

The initial implementation should use the simplest reliable local persistence option.

Do not introduce a distributed database, message queue, caching layer, or microservice architecture unless the V1 requirements actually demand it.

The exact database choice will be finalized during backend implementation.

---

## 24. Testing Structure

Tests should exist from the beginning.

Structure:

backend/
|
├── app/
|
└── tests/
    ├── test_reports.py
    ├── test_evidence.py
    ├── test_scoring.py
    └── test_memory.py

The exact filenames may change as implementation develops.

---

## 25. Critical Tests

The implementation must eventually test at least:

1. Empty vehicle history

2. One owner report

3. Inspector report after owner report

4. Mechanic corroboration

5. Multiple independent sources

6. Contradictory reports

7. Repeated reports from the same source

8. Small source history

9. Large source history

10. Hindsight unavailable

11. Groq unavailable

12. Invalid report

13. Malicious or prompt-injection-like report text

---

## 26. Failure Isolation

External service failure must not destroy useful information.

If Hindsight fails:

- do not claim there is no history
- clearly identify memory as unavailable
- preserve the submitted report if possible
- do not calculate a false clean-history assessment

If Groq fails:

- preserve the structured evidence
- preserve deterministic scoring
- return the assessment without automated explanation
- clearly indicate that explanation generation failed

---

## 27. Logging

The backend should log important system events.

Useful events include:

- report received
- report accepted/rejected
- memory write success/failure
- memory retrieval success/failure
- evidence calculation
- Groq request success/failure
- API errors

Logs must not contain:

- API keys
- authentication tokens
- unnecessary sensitive information

---

## 28. Error Handling

Errors should be explicit.

Avoid:

try:
    ...
except:
    pass

Do not swallow failures.

Every external integration should have controlled error handling.

Errors should be translated into useful application-level states.

---

## 29. Security Baseline

V1 must follow these rules:

- secrets stay server-side
- API keys never appear in frontend code
- `.env` is ignored by Git
- user input is validated
- report length is limited
- user-provided text is treated as untrusted
- Hindsight credentials are never exposed to the browser
- Groq credentials are never exposed to the browser

---

## 30. Development Commands

The exact commands will be finalized during implementation.

The intended workflow is:

Create virtual environment

Install dependencies

Configure `.env`

Start backend

Start frontend

Run tests

The README should document the final commands actually used by the project.

---

## 31. Local Development Architecture

During development:

Browser
    |
    v
Frontend
    |
    | HTTP/JSON
    v
Python Backend
    |
    +---- Hindsight
    |
    +---- Groq
    |
    +---- Structured Storage

The browser never communicates directly with Hindsight or Groq.

---

## 32. No Premature Infrastructure

V1 does not require:

- Kubernetes
- Docker orchestration
- Redis
- Kafka
- background worker systems
- microservices
- complex authentication
- cloud infrastructure
- analytics pipelines
- monitoring platforms
- CI/CD complexity

These can be introduced only if an actual requirement appears.

The goal is a functional, understandable hackathon system.

---

## 33. Development Order

Implementation should proceed in this order:

1. Create repository structure

2. Create Python virtual environment

3. Install minimal dependencies

4. Create configuration system

5. Create backend application

6. Create health endpoint

7. Verify local backend startup

8. Verify Hindsight API configuration

9. Implement MemoryService

10. Test Hindsight retain/retrieve behavior

11. Implement structured data models

12. Implement report ingestion

13. Implement EvidenceService

14. Implement deterministic scoring

15. Implement LLMService

16. Connect Groq explanations

17. Build frontend

18. Connect frontend to API

19. Build end-to-end demo data

20. Test failure cases

21. Polish UX

22. Prepare submission materials

---

## 34. Definition of Done for Project Setup

Project setup is complete when:

[ ] Repository structure exists

[ ] Python virtual environment works

[ ] Dependencies are installed

[ ] `.gitignore` exists

[ ] `.env.example` exists

[ ] Real `.env` is ignored

[ ] Backend starts successfully

[ ] `/health` works

[ ] Configuration loads correctly

[ ] No secrets are committed

[ ] README contains local setup instructions

[ ] Test framework runs

[ ] Hindsight API requirements are documented

[ ] No unnecessary infrastructure has been introduced

---

## 35. Principle

The project should remain easy to understand.

Every file should have a reason to exist.

Every dependency should have a reason to exist.

Every service boundary should have a concrete responsibility.

Every external integration should have explicit failure handling.

The objective is not to build the largest architecture.

The objective is to build the smallest architecture that demonstrates:

persistent memory
+
historical retrieval
+
cross-time evidence reasoning
+
evolving vehicle assessment
+
clear human-facing explanation

That is the V1 foundation of VeriCar.