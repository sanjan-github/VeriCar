# VeriCar

**An evidence-first vehicle history, condition assessment, and memory-backed inspection system.**

VeriCar helps used-car buyers and inspectors transform disparate inspection notes, service records, repair invoices, document verifications, test-drive observations, and seller claims into a structured, durable vehicle record. It reconciles recorded evidence against deterministic reference profiles, maintains historical provenance in vehicle memory, evaluates findings using transparent rules, and generates verifiable PDF reports with optional LLM explanations.

> **Core Invariant**: *Record what is known, preserve what is unknown, and never present an unavailable external service as if it contained no history.*

---

## Why VeriCar?

Evaluating a used vehicle is fundamentally an **evidence-reconciliation problem**:
- **Information Asymmetry**: Buyers receive conflicting claims from sellers, mechanics, and previous owners.
- **Silent Degradation**: Traditional systems often interpret missing records or failed API lookups as a "clean" history.
- **Uncontrolled AI Hallucination**: Pure LLM-based solutions risk inventing maintenance history, misinterpreting mechanical severity, or overriding facts.

VeriCar solves this by separating **durable storage**, **deterministic assessment rules**, **historical memory**, and **LLM explanation** into distinct architectural layers.

---

## What It Does

1. **Structured Ingestion**: Ingests vehicle condition records and chronological inspection reports with client-side and backend idempotency protection.
2. **Durable Local Persistence**: Persists all vehicle metadata, claims, and reports in SQLite before attempting downstream memory sync.
3. **Deterministic Assessment**: Evaluates odometer sanity, service intervals, recurring repairs, structural damage indicators, and document consistency using fixed rules.
4. **Historical Memory (Hindsight)**: Retains longitudinal vehicle and source reports, tracking corroboration, contradictions, and source reliability over time.
5. **LLM Explanation (Groq)**: Generates structured, evidence-backed natural-language explanations without granting the LLM authority to alter scores, findings, or verdicts.
6. **Deterministic PDF Reports**: Generates formal A4 inspection reports directly from SQLite and deterministic assessment data without external network dependencies.

---

## Architecture

```text
                           ┌─────────────────────────────────────┐
                           │      Canonical Browser UI           │
                           │  (HTML5 / Vanilla JS / Responsive)  │
                           └──────────────────┬──────────────────┘
                                              │ HTTP / JSON
                                              ▼
                           ┌─────────────────────────────────────┐
                           │       FastAPI Application           │
                           │       (backend/app/main.py)         │
                           └───────┬──────────────┬──────────────┘
                                   │              │
                ┌──────────────────┼──────────────┴──────────────────┐
                ▼                  ▼                                 ▼
     ┌────────────────────┐ ┌─────────────────────────┐    ┌────────────────────┐
     │  SQLite Database   │ │  Deterministic Rules    │    │  Hindsight Memory  │
     │  (core/database)   │ │  & Assessment Engine    │    │  (Vectorize API)   │
     │  • cars            │ │  (core/rules.py,        │    │  • vehicle history │
     │  • conditions      │ │   core/assessment.py,   │    │  • source memory   │
     │  • api_reports     │ │   backend/services)     │    │  • longitudinal    │
     │  • idempotency     │ └────────────┬────────────┘    └────────────────────┘
     └────────────────────┘              │
                                         ├──────────────────────────┐
                                         ▼                          ▼
                              ┌────────────────────┐     ┌────────────────────┐
                              │  Groq LLM Service  │     │  PDF Report Engine │
                              │  (Explanation-Only)│     │  (ReportLab / A4)  │
                              └────────────────────┘     └────────────────────┘
```

### Architectural Roles & Separation of Concerns

- **SQLite = Durable Application State**: The authoritative local source of truth for vehicles, conditions, accepted reports, and idempotency status.
- **Deterministic Engine = Assessment Authority**: Rules, findings, confidence scoring, and verdicts (`BUY`, `NEGOTIATE`, `AVOID`) are 100% deterministic and reproducible.
- **Hindsight = Evidence & Context Memory**: An external longitudinal store for multi-source observations and cross-report contradictions.
- **Groq = Optional Explanation Layer**: Fenced prompt execution that structures explanations strictly from supplied evidence IDs without authority to alter verdicts.
- **PDF Generation = Standalone Artifact**: Builds downloadable reports from local structured data without requiring external service availability.

---

## Core Design Principles

1. **Evidence First**: Observed facts, reference profiles, derived findings, and memory reflections are strictly decoupled. Assumptions are never converted into facts.
2. **Unknown is a First-Class State**: Missing information is recorded as `Unknown`. It is never treated as `No` and explicitly discounts assessment confidence.
3. **Deterministic Source of Truth**: The rules engine is the sole authority for verdicts. LLMs cannot invent findings or override calculations.
4. **Memory is Evidence, Not Authority**: Historical memory provides context. An external memory failure never invalidates local history.
5. **Strict Failure Isolation (`Hindsight unavailable ≠ No history`)**: If Hindsight or Groq is unreachable, VeriCar surfaces explicit degraded states (`503 MEMORY_UNAVAILABLE` or `explanation_status: "unavailable"`) while preserving full access to durable SQLite records.
6. **Provenance & Source Reliability**: Every claim records its source ID, source type (owner, buyer, mechanic, inspector), and observation timestamp, tracking credibility independently from claim polarity.

---

## Key Features

- **Idempotent Report Ingestion (`POST /api/reports`)**:
  - Safe client retry handling with SHA-256 payload fingerprinting and unique idempotency keys.
  - Distributed lease lock reclamation (`30.0s` timeout) for interrupted in-flight requests.
  - Atomic multi-stage persistence tracking (`vehicle_memory`, `source_memory`, `resolution`).
- **Vehicle History API (`GET /api/vehicles/{vehicle_id}`)**:
  - Chronologically ordered, isolated history records with full claim and provenance metadata.
- **Deterministic Assessment API (`GET /api/vehicles/{vehicle_id}/assessment`)**:
  - Weighted evidence calculation based on source type credibility and historical corroboration.
- **Explanation Layer (`GET /api/vehicles/{vehicle_id}/assessment/explanation`)**:
  - JSON-constrained LLM output validated against verified evidence IDs.
- **Inspection PDF API (`GET /api/vehicles/{vehicle_id}/assessment/report.pdf`)**:
  - A4 summary with breakdown of critical findings, warning flags, repair estimates, and next checks.
- **Health & Readiness Endpoints**:
  - `GET /health`: Fast process liveness probe.
  - `GET /readiness`: Comprehensive dependency check (SQLite connectivity required; optional Hindsight/Groq status reported without false outages).

---

## Tech Stack

- **Backend**: Python 3.11, FastAPI, Starlette, Uvicorn, Pydantic v2
- **Persistence**: SQLite (WAL-mode compatible, foreign key constraints enabled)
- **External Integrations**:
  - [Hindsight Client](https://github.com/vectorize-io/hindsight) (Longitudinal vehicle memory banks)
  - Groq API / LLaMA 3.3 70B (JSON-mode structured explanations)
  - HTTPX (Asynchronous HTTP transport)
- **Reporting & UI**:
  - ReportLab & PyPDF (Deterministic A4 PDF compilation)
  - HTML5, CSS3 (CSS Variables, Responsive Grid, Dark Mode), Vanilla JavaScript
  - Streamlit (Optional manual condition-input workstation)
- **Quality & Testing**: Pytest, Pytest-Asyncio, Python-Dotenv

---

## Project Structure

```text
VeriCar/
├── backend/
│   ├── app/
│   │   ├── config.py              # Environment parsing & validation
│   │   ├── main.py                # FastAPI endpoints & lifespan
│   │   ├── models/                # Pydantic schemas (report, memory, evidence)
│   │   ├── repositories/          # Hindsight repository adapter
│   │   └── services/              # Assessment, evidence, explanation & PDF services
│   └── tests/                     # API, config, hardening & scenario test suite
├── core/
│   ├── models.py                  # Vehicle data model
│   ├── condition.py               # Inspection & condition checklist model
│   ├── database.py                # SQLite schema, transactions & idempotency
│   ├── rules.py                   # Deterministic assessment rules
│   ├── comparison.py              # Expected profile vs. actual evidence comparison
│   ├── assessment.py              # Verdict & confidence scoring logic
│   ├── assessment_pipeline.py     # End-to-end assessment orchestration
│   ├── memory_recall.py           # Historical memory retrieval
│   ├── history_reconciliation.py  # Current vs. historical cross-check
│   └── pdf_report.py              # ReportLab PDF generator
├── frontend/
│   ├── index.html                 # Canonical browser application
│   ├── app.js                     # State management, API calls & error handling
│   └── styles.css                 # Responsive layout & theme variables
├── app/
│   └── main.py                    # Streamlit condition-entry workstation
├── data/
│   └── expected_profiles.json     # Synthetic reference vehicle profiles
├── tests/                         # Core unit & integration tests
├── requirements.txt
├── .env.example
└── README.md
```

---

## Running Locally

### 1. Prerequisites
- **Python 3.11** installed.
- Git installed.

### 2. Setup Virtual Environment
```powershell
# Clone repository
git clone https://github.com/sanjan-github/VeriCar.git
cd VeriCar

# Create virtual environment
python -m venv .venv

# Activate environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate environment (macOS / Linux)
# source .venv/bin/activate

# Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Start Canonical FastAPI Application
```powershell
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
Open your browser at **`http://127.0.0.1:8000/`**.

*(Optional)* To run the legacy Streamlit condition workstation:
```powershell
streamlit run app/main.py
```

---

## Configuration

Copy `.env.example` to `.env` to configure optional external services:

```ini
# Application & Server
APP_ENV=development
APP_NAME=VeriCar
HOST=127.0.0.1
PORT=8000
DB_PATH=data/vericar.db

# Hindsight (Optional: persistent memory banks)
HINDSIGHT_BASE_URL=https://api.hindsight.vectorize.io
HINDSIGHT_API_KEY=
HINDSIGHT_TIMEOUT=30
HINDSIGHT_STARTUP_CHECK=false

# Groq (Optional: LLM natural-language explanations)
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TIMEOUT=20
```

*Note: Neither Hindsight nor Groq credentials are required to run the local test suite or core assessment workflows.*

---

## Testing

Run the full automated test suite:

```powershell
python -m pytest -q
```

All 227 tests execute locally without live external network dependencies via isolated fixtures and mock transports.

---

## Failure Semantics & Resilience Matrix

| Failure Condition | System Behavior | User Impact |
| :--- | :--- | :--- |
| **Hindsight Offline / Timeout** | Assessment returns `503 MEMORY_UNAVAILABLE` | Frontend keeps durable SQLite history visible; flags assessment as temporarily unavailable. |
| **Hindsight Unconfigured** | Readiness reports `hindsight: unconfigured` | Application operates normally in local-only mode. |
| **Hindsight Malformed Data** | Normalized recall parser rejects payload | Returns controlled 503 instead of corrupting evidence metrics. |
| **Groq Offline / API Key Missing** | Endpoint catches error; sets `explanation_status: unavailable` | Deterministic assessment and findings display cleanly without explanations. |
| **Interrupted Ingest / Crash** | Idempotency record preserves stage (`PARTIAL`) | Subsequent retry resumes pending downstream stages without duplicate rows. |
| **Database Unreachable** | Readiness returns `503 SERVICE_UNAVAILABLE` | Health check distinguishes process liveness from database readiness. |

---

## Resume / Portfolio Highlights

- **Durable Write-Ahead Idempotency**: Designed an atomic SQLite idempotency mechanism supporting distributed lease recovery, SHA-256 fingerprint verification, and multi-stage downstream transaction resumption.
- **Deterministic & Bounded Scoring Engine**: Built a transparent rules-based scoring pipeline that calculates confidence bounds, repair cost intervals, and buy/negotiate/avoid verdicts from structured inspection evidence.
- **Graceful Degradation Architecture**: Implemented strict failure isolation preventing external LLM and vector memory outages from corrupting local records or misrepresenting failed lookups as clean vehicle histories.
- **Secure LLM Guardrails**: Architected a prompt-fenced explanation service with temperature zero, JSON-schema constraints, and post-generation evidence ID validation preventing hallucinated claims.
- **Comprehensive Quality Assurance**: Maintained a 227-test automated test suite verifying edge cases across race conditions, schema migrations, and external failure modes.

---

## Limitations & Future Work

- **Indian Vehicle Registry Integrations**: VeriCar is designed for the Indian pre-owned car market. Direct integrations with VAHAN/mParivahan, insurance databases, and PUC portals are intentionally deferred until official, licensed APIs with verified provenance are available.
- **Reference Profiles**: The seeded profiles in `data/expected_profiles.json` are synthetic reference datasets for demonstration and testing, not authoritative manufacturer specifications.
- **Inspection Disclaimer**: VeriCar is an evidence-organizing decision support tool and does not substitute for an on-site physical mechanical inspection.

---

## License

This project is licensed under the [MIT License](LICENSE).
