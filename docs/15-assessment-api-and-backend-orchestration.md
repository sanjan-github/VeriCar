# Assessment API and Backend Orchestration Specification

## 1. Purpose

This document specifies the backend orchestration layer responsible for connecting VeriCar's report ingestion, persistent memory, evidence analysis, and LLM explanation services.

The orchestration layer provides the application-level workflow that transforms an incoming report into an updated vehicle assessment.

The primary responsibility is coordinating existing services rather than duplicating their logic.

The backend must maintain clear separation between:

* request validation
* report persistence
* memory operations
* evidence calculation
* explanation generation
* API response construction

---

# 2. Architectural Position

The backend request flow is:

```text
HTTP Request
     ↓
API Route
     ↓
Request Validation
     ↓
Report Service
     ↓
Memory Service
     ↓
History Retrieval
     ↓
Evidence Service
     ↓
Assessment State
     ↓
LLM Service
     ↓
Response Serialization
     ↓
HTTP Response
```

The API layer coordinates these services but does not implement their internal business logic.

---

# 3. Primary Endpoints

The initial backend API should expose:

```text
GET  /health

POST /api/reports

GET  /api/vehicles/{vehicle_id}

GET  /api/vehicles/{vehicle_id}/assessment
```

Additional endpoints should only be introduced when required by the product.

---

# 4. Endpoint Responsibilities

## `GET /health`

Provides a lightweight application health check.

Expected response:

```json
{
  "status": "ok"
}
```

This endpoint should not require Hindsight or Groq to be available.

---

## `POST /api/reports`

Accepts a new vehicle history report.

Responsibilities:

* validate the request
* create the report
* create or derive its claim
* persist the report
* write relevant historical memory
* retrieve relevant history
* calculate the resulting evidence state
* generate an explanation
* return the updated assessment context

---

## `GET /api/vehicles/{vehicle_id}`

Returns structured vehicle information and relevant historical reports.

The endpoint should provide enough information for the frontend to construct a vehicle history timeline.

It should not perform unnecessary LLM generation.

---

## `GET /api/vehicles/{vehicle_id}/assessment`

Returns the current deterministic assessment for the vehicle.

The endpoint should expose:

* findings
* evidence status
* evidence confidence
* supporting evidence
* contradictory evidence
* relevant timeline information

An explanation may be included when available.

---

# 5. Report Submission Request

The report submission request should follow the schema established by Structured Report Ingestion.

Example:

```json
{
  "vehicle_id": "VEH-001",
  "source_id": "SRC-027",
  "source_type": "mechanic",
  "observed_at": "2026-04-19",
  "text": "Transmission hesitation confirmed during test drive."
}
```

The request must be validated before any downstream operation is performed.

---

# 6. Request Validation

Validation must occur at the API boundary.

The backend should validate:

* required fields
* identifier formats
* source type
* date format
* report text
* report length
* supported values

Invalid requests must terminate before:

* report persistence
* Hindsight writes
* evidence calculation
* LLM invocation

---

# 7. API Layer Responsibilities

The API route should:

1. Receive the request.
2. Validate the request.
3. Invoke the appropriate application service.
4. Handle known application-level errors.
5. Serialize the result.
6. Return the appropriate HTTP status.

The API route should not:

* calculate evidence confidence
* calculate source reliability
* construct Hindsight payloads
* build LLM prompts
* parse provider-specific LLM responses
* contain database logic

---

# 8. Application Service

A dedicated application-level service should coordinate report processing.

Conceptual interface:

```python
class ReportProcessingService:
    def process_report(self, report_request):
        ...
```

Its responsibility is to orchestrate the workflow.

Conceptually:

```text
ReportProcessingService
        |
        +-- Report persistence
        |
        +-- Claim interpretation
        |
        +-- MemoryService
        |
        +-- EvidenceService
        |
        +-- LLMService
```

---

# 9. End-to-End Report Processing

The complete workflow is:

```text
1. Receive report
       ↓
2. Validate request
       ↓
3. Create report ID
       ↓
4. Persist report
       ↓
5. Interpret claim
       ↓
6. Persist claim
       ↓
7. Write vehicle memory
       ↓
8. Write source memory
       ↓
9. Retrieve relevant vehicle history
       ↓
10. Retrieve relevant source history
       ↓
11. Calculate evidence state
       ↓
12. Determine assessment change
       ↓
13. Generate explanation
       ↓
14. Build response
```

Each step must have a clearly defined responsibility.

---

# 10. Report Persistence

The application should persist the accepted report before attempting downstream reasoning.

The report must retain:

* report ID
* vehicle ID
* source ID
* source type
* observation date
* submission timestamp
* original text
* status

The original report must remain unchanged.

Accepted API reports are committed to SQLite together with their initial idempotency
processing state before any Hindsight operation begins. SQLite is the durable local
source of truth for the accepted report, including its original text and derived claim.
Hindsight remains an external memory system; the two systems do not share an atomic
transaction. A retry reconstructs the stable report identity from SQLite and resumes
only stages that have not completed.

---

# 11. Claim Processing

After report validation, the system derives the structured claim associated with the report.

The claim may contain:

* claim ID
* report ID
* normalized issue
* claim text
* polarity
* interpretation metadata

The claim must remain traceable to its originating report.

---

# 12. Claim Interpretation Failure

If semantic claim interpretation fails:

* the original report must remain persisted
* the failure must be represented explicitly
* unsupported claims must not be fabricated
* evidence scoring must not use an invented issue classification

The application may return a partial processing state depending on the persistence and memory guarantees implemented.

---

# 13. Vehicle Memory Write

For every accepted report, the system should write the relevant historical event to the vehicle's Hindsight memory.

The memory event should contain enough metadata to identify:

* vehicle
* report
* source
* observation date
* issue
* original observation

The exact Hindsight payload must follow the verified Hindsight API contract.

---

# 14. Source Memory Write

The same accepted report should contribute to the source's historical memory.

Source memory should allow the system to determine reporting behavior across vehicles.

Example:

```text
SRC-027
   |
   +-- VEH-001
   |     +-- RPT-004
   |
   +-- VEH-014
   |     +-- RPT-021
   |
   +-- VEH-031
         +-- RPT-039
```

This allows source reliability to be evaluated using historical reporting behavior rather than a single vehicle.

---

# 15. Memory Write Ordering

The application must establish a deterministic order for memory operations.

Recommended sequence:

```text
Persist Report
      ↓
Persist Claim
      ↓
Write Vehicle Memory
      ↓
Write Source Memory
```

If a memory operation fails, the application must expose the resulting partial state rather than claiming successful completion.

---

# 16. Memory Availability

The backend must distinguish:

### Available

Hindsight successfully responds.

### Empty

Hindsight responds successfully but no relevant history exists.

### Unavailable

Hindsight cannot be reached or returns an infrastructure failure.

These states must remain distinct throughout the application.

---

# 17. Historical Retrieval

After the new report is stored, the application retrieves relevant historical context.

The retrieval should include:

* related vehicle reports
* relevant historical observations
* supporting evidence
* contradictory evidence
* source history where required
* temporal context

The retrieval process must not filter out contradictory information merely because it conflicts with the current finding.

---

# 18. Retrieval Before Assessment

The Evidence Service must operate on accumulated historical context rather than only the newly submitted report.

Conceptually:

```text
New Report
    +
Historical Vehicle Memory
    +
Historical Source Memory
        ↓
EvidenceService
```

This is required for the assessment to evolve over time.

---

# 19. Evidence Calculation

The orchestration layer passes structured historical information to the Evidence Service.

Conceptual call:

```python
assessment = evidence_service.calculate(
    vehicle_history=vehicle_history,
    source_history=source_history,
    claims=claims
)
```

The Evidence Service determines:

* supporting evidence
* contradicting evidence
* source reliability
* source independence
* corroboration
* evidence confidence
* evidence status

The orchestration layer must not duplicate these calculations.

---

# 20. Assessment Change Detection

The application should compare the newly calculated assessment with the previous assessment state.

Conceptually:

```text
Previous Assessment
        ↓
Current Assessment
        ↓
Assessment Change
```

Example:

```json
{
  "previous_status": "limited",
  "current_status": "moderate",
  "trigger_report_id": "RPT-009"
}
```

The change record provides structured information for the explanation service.

---

# 21. Assessment State

The backend should maintain a structured representation of the current assessment.

Example:

```json
{
  "vehicle_id": "VEH-001",
  "finding": "transmission_shift_behavior",
  "evidence_status": "strong",
  "evidence_confidence": 86,
  "supporting_sources": 3,
  "contradicting_sources": 1
}
```

The exact representation may evolve with implementation.

---

# 22. Explanation Generation

Once the Evidence Service completes, the backend may invoke the LLM Service.

Conceptual flow:

```python
explanation = llm_service.explain_assessment(
    finding=assessment.finding,
    evidence_state=assessment,
    timeline=timeline,
    assessment_change=assessment_change
)
```

The explanation service receives structured application state.

It must not independently determine the assessment.

---

# 23. Explanation Failure

If LLM generation fails:

* the deterministic assessment remains valid
* the API should return the assessment
* explanation availability should be represented explicitly

Example:

```json
{
  "explanation": null,
  "explanation_status": "unavailable"
}
```

The system must not convert an LLM failure into an evidence failure.

---

# 24. Hindsight Failure

If Hindsight is unavailable, the system must not represent the vehicle as having no history.

Example state:

```json
{
  "memory_status": "unavailable"
}
```

This differs from:

```json
{
  "memory_status": "empty"
}
```

The frontend can then communicate the appropriate state.

---

# 25. Partial Processing

External services can fail independently.

Possible state:

```text
Report persistence      SUCCESS
Claim processing        SUCCESS
Vehicle memory          SUCCESS
Source memory           FAILURE
Evidence calculation    NOT RUN
LLM explanation         NOT RUN
```

The API should expose an explicit processing error rather than returning a successful assessment based on incomplete history.

---

# 26. Idempotency

Report submission must avoid accidental duplicate reports.

A client retry should not create multiple identical report records merely because the original request response was lost.

The implementation should use an idempotency mechanism appropriate to the application.

For example:

```text
Idempotency-Key
```

may be accepted on report creation requests.

The exact mechanism should be finalized during implementation.

---

# 27. Duplicate Detection

Idempotency and semantic duplicate detection are separate concerns.

### Idempotency

Prevents the same request from being processed multiple times.

### Semantic duplicate detection

Determines whether two independently submitted reports describe the same event or observation.

The latter must not be used aggressively.

Two similar reports from different sources may represent independent observations.

---

# 28. Response Contract

A successful report-processing response should provide enough information for the frontend to update the current vehicle state without making additional unnecessary requests.

Conceptual response:

```json
{
  "report": {
    "report_id": "RPT-009",
    "vehicle_id": "VEH-001",
    "source_id": "SRC-041",
    "source_type": "inspector",
    "observed_at": "2026-05-03",
    "status": "active"
  },
  "claim": {
    "claim_id": "CLM-009",
    "issue": "transmission_shift_behavior",
    "polarity": "supporting"
  },
  "memory": {
    "status": "available"
  },
  "assessment": {
    "finding": "transmission_shift_behavior",
    "status": "strong",
    "evidence_confidence": 86
  },
  "explanation": {
    "status": "available",
    "summary": "Multiple independent reports describe transmission shift concerns."
  }
}
```

The API response should not expose provider-specific Hindsight or Groq implementation details.

---

# 29. Vehicle History Response

`GET /api/vehicles/{vehicle_id}` should return structured historical information.

Conceptual response:

```json
{
  "vehicle_id": "VEH-001",
  "history": [
    {
      "report_id": "RPT-001",
      "source_type": "owner",
      "observed_at": "2026-01-10",
      "text": "Transmission operated normally."
    },
    {
      "report_id": "RPT-004",
      "source_type": "inspector",
      "observed_at": "2026-04-19",
      "text": "Hard 2->3 shift observed."
    }
  ]
}
```

The endpoint should preserve chronological ordering.

---

# 30. Assessment Response

`GET /api/vehicles/{vehicle_id}/assessment` should return the current deterministic assessment.

Conceptual response:

```json
{
  "vehicle_id": "VEH-001",
  "findings": [
    {
      "issue": "transmission_shift_behavior",
      "status": "strong",
      "evidence_confidence": 86,
      "supporting_sources": 3,
      "contradicting_sources": 1
    }
  ]
}
```

The response should remain valid even if the LLM explanation service is unavailable.

---

# 31. API Error Model

Errors should use a consistent structure.

Example:

```json
{
  "error": {
    "code": "MEMORY_UNAVAILABLE",
    "message": "Historical memory is temporarily unavailable."
  }
}
```

Error codes should be stable and machine-readable.

Messages should be appropriate for the client.

---

# 32. Recommended Error Categories

Initial categories:

```text
VALIDATION_ERROR
REPORT_NOT_FOUND
VEHICLE_NOT_FOUND
MEMORY_UNAVAILABLE
MEMORY_WRITE_FAILED
CLAIM_INTERPRETATION_FAILED
ASSESSMENT_FAILED
EXPLANATION_UNAVAILABLE
INTERNAL_ERROR
```

Only categories required by the implementation should be retained.

---

# 33. HTTP Status Codes

Recommended mapping:

```text
200 OK
    Successful retrieval

201 Created
    Report successfully created

400 Bad Request
    Invalid request structure

404 Not Found
    Requested vehicle or report does not exist

409 Conflict
    Duplicate/idempotency conflict

422 Unprocessable Entity
    Semantically invalid input

503 Service Unavailable
    Required external dependency unavailable

500 Internal Server Error
    Unexpected server failure
```

The final mapping should follow the framework's conventions and application requirements.

---

# 34. Transaction Boundaries

The application must distinguish local persistence from external memory operations.

Hindsight operations cannot necessarily participate in the same transaction as local application storage.

Therefore, the system must explicitly represent partial failures.

The implementation must not assume:

```text
Database transaction
+
Hindsight write
```

is automatically atomic.

---

# 35. Consistency Strategy

For report processing:

```text
1. Validate
2. Persist report
3. Persist claim
4. Write memory
5. Retrieve history
6. Calculate assessment
7. Generate explanation
```

If a later operation fails, the system should preserve the successful earlier operations and record the failure state.

Recovery and retry mechanisms should operate on explicit state rather than silently repeating the entire workflow.

---

# 36. Concurrency

Two reports for the same vehicle may arrive close together.

The implementation must prevent inconsistent assessment state.

For example:

```text
Request A
    ↓
reads history

Request B
    ↓
writes new report

Request A
    ↓
calculates from stale history
```

The application should define a strategy for handling concurrent updates.

For the initial implementation, serialized assessment calculation per vehicle may be sufficient if required by the storage architecture.

Complex distributed locking should not be introduced without a concrete need.

---

# 37. Assessment Recalculation

The current assessment should be reproducible from:

```text
vehicle history
+
source history
+
evidence rules
```

The application should not depend solely on a previously stored score.

This allows assessment state to be recomputed if scoring rules change.

---

# 38. Caching

Caching should not be introduced for authoritative evidence calculations until correctness requirements are established.

Historical memory and assessment state are time-sensitive.

If caching is introduced later, cache invalidation must occur whenever relevant reports or source history change.

---

# 39. Security Boundaries

The backend must:

* keep API keys server-side
* validate all external input
* treat report content as untrusted
* prevent prompt injection from becoming application instructions
* avoid exposing internal service credentials
* avoid exposing unnecessary internal identifiers
* avoid logging sensitive data unnecessarily

The frontend must never communicate directly with Hindsight or Groq using server credentials.

---

# 40. Service Dependency Rules

The dependency direction should remain:

```text
API
 ↓
Application Services
 ↓
Domain Services
 ↓
Infrastructure Services
```

Conceptually:

```text
API Routes
    ↓
ReportProcessingService
    ↓
+----------------------+
|                      |
v                      v
EvidenceService    MemoryService
                       |
                       v
                    Hindsight

ReportProcessingService
            |
            v
       LLMService
            |
            v
           Groq
```

Infrastructure-specific implementation details should remain isolated.

---

# 41. Suggested Backend Structure

The implementation may use:

```text
backend/
└── app/
    ├── main.py
    ├── config.py
    │
    ├── api/
    │   └── routes/
    │       ├── health.py
    │       ├── reports.py
    │       └── vehicles.py
    │
    ├── models/
    │   ├── reports.py
    │   ├── claims.py
    │   ├── assessments.py
    │   └── responses.py
    │
    ├── services/
    │   ├── report_service.py
    │   ├── memory_service.py
    │   ├── evidence_service.py
    │   └── llm_service.py
    │
    ├── repositories/
    │   └── ...
    │
    └── core/
        ├── errors.py
        └── ...
```

The exact structure should remain lightweight.

Files should only be introduced when they provide a clear responsibility.

---

# 42. API Dependency Injection

FastAPI dependency injection may be used to provide:

* configuration
* services
* repositories
* external clients

Routes should receive abstractions rather than constructing external clients directly.

Example:

```python
def create_report(
    request: ReportRequest,
    service: ReportProcessingService = Depends(...)
):
    ...
```

The exact implementation should follow the project's testing requirements.

---

# 43. Testing Architecture

The orchestration layer should be testable without requiring live Groq or Hindsight services for every test.

Use service boundaries that allow:

```text
FakeMemoryService
FakeLLMService
DeterministicEvidenceService
```

for unit and application-level tests.

Live external integrations should be covered separately.

---

# 44. Unit Tests

Test:

* request validation
* report processing
* claim persistence
* service invocation
* error propagation
* response construction
* assessment change detection
* explanation failure handling
* memory failure handling

---

# 45. Integration Tests

Integration tests should verify:

```text
POST /api/reports
        ↓
Report
        ↓
Hindsight
        ↓
Evidence
        ↓
Assessment
        ↓
Explanation
```

The tests should use controlled external service implementations or a test environment.

---

# 46. End-to-End Processing Example

Input:

```json
{
  "vehicle_id": "VEH-001",
  "source_id": "SRC-041",
  "source_type": "mechanic",
  "observed_at": "2026-05-03",
  "text": "Transmission hesitation confirmed."
}
```

Processing:

```text
1. Validate request
2. Create RPT-009
3. Create CLM-009
4. Persist report
5. Write vehicle memory
6. Write source memory
7. Retrieve existing vehicle history
8. Retrieve source history
9. Calculate evidence
10. Compare previous assessment
11. Generate explanation
12. Return response
```

Result:

```json
{
  "report_id": "RPT-009",
  "assessment": {
    "issue": "transmission_shift_behavior",
    "status": "strong",
    "evidence_confidence": 86
  },
  "explanation": {
    "status": "available"
  }
}
```

---

# 47. Failure Example

Suppose:

```text
Report persistence = successful
Vehicle memory write = successful
Source memory write = failed
```

The application must not return:

```json
{
  "status": "success"
}
```

It should return an explicit processing state or error.

Example:

```json
{
  "error": {
    "code": "MEMORY_WRITE_FAILED",
    "message": "The report was stored, but historical memory could not be updated."
  }
}
```

The system should retain enough state to retry the failed memory operation without creating another report.

---

# 48. Observability

The backend should generate a request or processing identifier for multi-stage report processing.

Example:

```text
request_id = req_8f3a...
```

This identifier should allow operators to correlate:

```text
API request
    ↓
report processing
    ↓
memory operations
    ↓
evidence calculation
    ↓
LLM request
```

Sensitive report content should not be included in logs merely for traceability.

---

# 49. Performance

The initial implementation should prioritize correctness and traceability.

Potential latency contributors include:

* Hindsight writes
* Hindsight retrieval
* LLM requests

The backend should measure these independently.

Example internal timing:

```text
validation:       5 ms
persistence:     10 ms
memory write:    120 ms
history retrieval: 90 ms
evidence:          3 ms
LLM:             700 ms
```

Actual values must be measured rather than assumed.

---

# 50. Timeout Handling

External operations should have explicit timeouts.

At minimum:

* Hindsight requests
* Groq requests

A timeout must produce an explicit failure state.

The backend must not wait indefinitely for an external dependency.

---

# 51. Retry Boundaries

Retries should be applied only to operations where retrying is safe.

Memory writes require idempotent handling before automatic retry.

LLM explanation requests are safer to retry because they do not modify authoritative state.

The retry policy should be bounded.

---

# 52. Data Flow Summary

The complete backend architecture is:

```text
                        ┌─────────────────┐
                        │     Client      │
                        └────────┬────────┘
                                 │
                                 │ HTTP/JSON
                                 ▼
                        ┌─────────────────┐
                        │    API Layer    │
                        └────────┬────────┘
                                 │
                                 ▼
                  ┌───────────────────────────┐
                  │ ReportProcessingService  │
                  └──────┬────────┬───────────┘
                         │        │
             ┌───────────┘        └─────────────┐
             ▼                                  ▼
    ┌─────────────────┐                ┌─────────────────┐
    │ Report Storage  │                │  MemoryService  │
    └─────────────────┘                └────────┬────────┘
                                                │
                                                ▼
                                          ┌─────────────┐
                                          │  Hindsight  │
                                          └──────┬──────┘
                                                 │
                                                 │ history
                                                 ▼
                                        ┌─────────────────┐
                                        │ EvidenceService │
                                        └────────┬────────┘
                                                 │
                                                 │ assessment
                                                 ▼
                                          ┌────────────┐
                                          │ LLMService │
                                          └─────┬──────┘
                                                │
                                                ▼
                                              Groq
```

---

# 53. API Contract Summary

### `GET /health`

Purpose:

```text
Application health check
```

### `POST /api/reports`

Purpose:

```text
Create and process a vehicle history report
```

### `GET /api/vehicles/{vehicle_id}`

Purpose:

```text
Retrieve vehicle history
```

### `GET /api/vehicles/{vehicle_id}/assessment`

Purpose:

```text
Retrieve current vehicle assessment
```

---

# 54. Definition of Done

The Assessment API and Backend Orchestration layer is complete when:

* [ ] `/health` is operational
* [ ] `/api/reports` accepts validated reports
* [ ] report persistence is implemented
* [ ] claim processing is integrated
* [ ] vehicle memory writes are integrated
* [ ] source memory writes are integrated
* [ ] historical retrieval is integrated
* [ ] EvidenceService is integrated
* [ ] assessment changes are detected
* [ ] LLMService is integrated
* [ ] LLM failure does not invalidate deterministic assessment
* [ ] Hindsight failure is represented explicitly
* [ ] empty memory and unavailable memory are distinct
* [ ] API errors use a consistent structure
* [ ] report submission supports idempotent handling
* [ ] partial processing states are handled
* [ ] external dependencies have timeouts
* [ ] service responsibilities remain separated
* [ ] API routes do not contain business logic
* [ ] provider-specific implementation details remain isolated
* [ ] unit tests cover orchestration logic
* [ ] integration tests cover the complete report workflow
* [ ] sensitive credentials remain server-side
* [ ] logs do not expose secrets or unnecessary sensitive content

---

# 55. Scope Boundary

This specification defines the backend orchestration required to connect VeriCar's core services.

After implementation, the backend will support the complete server-side workflow:

```text
Report
  ↓
Validation
  ↓
Persistence
  ↓
Claim
  ↓
Hindsight
  ↓
Historical Retrieval
  ↓
Evidence Assessment
  ↓
LLM Explanation
  ↓
Structured API Response
```

The next specification defines the client-facing application responsible for presenting this information and collecting new reports:

```text
16-frontend-specification.md
```
