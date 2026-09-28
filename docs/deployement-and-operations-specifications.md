# 19 — Deployment and Operations Specification

## 1. Purpose

This document defines the deployment, runtime configuration, security, observability, reliability, and operational requirements for VeriCar.

The goal is to provide a production-oriented operational boundary for the system without coupling the application unnecessarily to a specific hosting provider.

The deployed system consists of:

```text id="c5q0bf"
Browser
   |
   v
Frontend
   |
   | HTTPS
   v
Python Backend
   |
   +-----------> Hindsight
   |
   +-----------> Groq
```

The backend remains the trusted orchestration layer.

---

# 2. Deployment Principles

Deployment must follow these principles:

1. Secrets never reach the browser.
2. Production configuration is environment-specific.
3. External services are treated as dependencies, not trusted components.
4. Health checks distinguish application health from dependency health.
5. Failures must degrade explicitly.
6. Logs must be useful without exposing sensitive data.
7. Production and test memory must remain isolated.
8. Deployments must be reproducible.
9. Configuration must not be hardcoded.
10. Operational behavior must be observable.

---

# 3. Deployment Topology

The initial production topology should remain intentionally small.

```text id="v5kjqk"
                  ┌──────────────────┐
                  │      Browser     │
                  └────────┬─────────┘
                           │ HTTPS
                           ▼
                  ┌──────────────────┐
                  │    Frontend      │
                  └────────┬─────────┘
                           │ HTTPS / JSON
                           ▼
                  ┌──────────────────┐
                  │ Python Backend   │
                  │                  │
                  │ API              │
                  │ Evidence Engine  │
                  │ Memory Adapter   │
                  │ LLM Adapter      │
                  └──────┬─────┬─────┘
                         │     │
                         ▼     ▼
                 ┌──────────┐ ┌──────────┐
                 │ Hindsight│ │   Groq   │
                 └──────────┘ └──────────┘
```

Do not introduce additional infrastructure unless it solves an identified requirement.

---

# 4. Environment Separation

At minimum, maintain:

```text id="5zzq77"
development
test
production
```

Each environment must have separate configuration.

Most importantly:

```text id="m8z2gc"
development → development memory
test        → test memory
production  → production memory
```

Production vehicle history must never be used as an automated test fixture.

---

# 5. Configuration

Configuration must be loaded through environment variables or an equivalent secure configuration mechanism.

Example:

```text id="nd6v4q"
APP_ENV=production

API_HOST=0.0.0.0
API_PORT=8000

HINDSIGHT_BASE_URL=...
HINDSIGHT_API_KEY=...

GROQ_API_KEY=...
GROQ_MODEL=...

LOG_LEVEL=INFO

REPORT_MAX_LENGTH=...
```

Actual values must not be committed to Git.

---

# 6. Configuration Categories

Configuration should be separated conceptually into:

### Application configuration

```text id="lq8yn4"
environment
host
port
log level
allowed origins
```

### Evidence configuration

```text id="3ce3r1"
source priors
alpha
beta
reliability blending parameter
evidence sufficiency parameter
qualitative thresholds
```

### External service configuration

```text id="kqz20v"
Hindsight endpoint
Hindsight credentials
Groq endpoint/configuration
Groq credentials
model identifier
timeouts
```

### Security configuration

```text id="0h0z6y"
CORS origins
authentication settings where applicable
request limits
trusted hosts
```

---

# 7. Secrets Management

The following are secrets:

```text id="2i9g9m"
Hindsight credentials
Groq API key
authentication secrets
signing keys
deployment credentials
```

They must never be stored in:

```text id="5u1b3c"
source code
Git history
frontend JavaScript
README files
test fixtures
screenshots
logs
```

Use the deployment platform's secret-management mechanism or environment-secret facility.

---

# 8. Local Environment Files

For local development, a file such as:

```text id="3p3xvi"
.env
```

may be used.

It must be excluded from version control.

Recommended:

```text id="r3n1xk"
.env
.env.*
!.env.example
```

The repository should contain:

```text id="j0l5ud"
.env.example
```

containing placeholder values only.

Example:

```text id="qz2w5n"
HINDSIGHT_BASE_URL=
HINDSIGHT_API_KEY=

GROQ_API_KEY=
GROQ_MODEL=

APP_ENV=development
```

---

# 9. Secret Rotation

Secrets must be replaceable without code changes.

Rotation procedure:

```text id="qg3m17"
Create new credential
       ↓
Update deployment secret
       ↓
Restart/redeploy service
       ↓
Verify dependency connectivity
       ↓
Revoke old credential
```

Credentials must not be embedded into container images or compiled frontend assets.

---

# 10. Frontend Secret Boundary

The frontend must never receive:

```text id="4i9j2q"
GROQ_API_KEY
HINDSIGHT_API_KEY
database credentials
internal service credentials
```

The browser communicates only with the public backend API.

---

# 11. CORS

The backend must use an explicit allowed-origin configuration.

Development may allow:

```text id="7c7w9m"
http://localhost:...
```

Production should allow only the deployed frontend origin.

Avoid:

```text id="3yn2uk"
Access-Control-Allow-Origin: *
```

when the application requires controlled cross-origin access.

---

# 12. HTTPS

Production browser-to-backend communication must use HTTPS.

The system should not transmit:

* vehicle history
* report text
* source information
* API credentials

over unencrypted production HTTP.

HTTP may be acceptable for local development.

---

# 13. Backend Runtime

The backend should run as a production application server rather than the development server.

The runtime should support:

* process management
* graceful shutdown
* configurable worker/process count
* health checks
* structured logging
* environment configuration

The exact hosting/runtime command should remain deployment-specific.

---

# 14. Containerization

Containerization is recommended if it simplifies reproducible deployment.

Conceptual structure:

```text id="g7pnwq"
Docker image
├── Python runtime
├── application dependencies
├── backend application
└── production configuration interface
```

Secrets must not be baked into the image.

---

# 15. Container Build Requirements

The production image should:

* use a supported Python runtime
* install pinned application dependencies
* run as a non-root user where practical
* contain only required runtime dependencies
* exclude development secrets
* exclude unnecessary test data
* expose only the application port
* provide a health-check mechanism where supported

---

# 16. Dependency Pinning

Production dependencies should be reproducible.

Use a lockfile or pinned dependency strategy appropriate to the Python tooling selected by the project.

The build should not silently upgrade dependencies during deployment.

Dependency updates should be deliberate and tested.

---

# 17. Frontend Deployment

The frontend may be deployed as static assets behind:

```text id="qj43yo"
CDN / static hosting
```

or served through infrastructure appropriate to the selected hosting platform.

The frontend requires configuration only for public backend endpoints.

It must not contain private credentials.

---

# 18. Backend API URL

The frontend should obtain the backend URL through deployment configuration.

Example:

```text id="6jz8ws"
PUBLIC_API_BASE_URL=https://api.example.com
```

Do not hardcode development URLs into production builds.

---

# 19. Health Checks

The backend should expose:

```http id="h8umh3"
GET /health
```

The endpoint should confirm that the application process is running.

Example:

```json id="4m9ux0"
{
  "status": "ok"
}
```

The health endpoint should remain lightweight.

---

# 20. Readiness vs Liveness

Where the deployment platform supports both concepts, distinguish:

### Liveness

Is the application process alive?

```text id="b4t7st"
GET /health
```

### Readiness

Can the application accept normal traffic?

```text id="8ax7em"
GET /health/ready
```

Readiness may check required dependencies according to operational requirements.

Do not make the liveness endpoint depend on Hindsight or Groq.

A temporary external-service failure should not necessarily cause the backend process to be restarted.

---

# 21. Dependency Health

Operational diagnostics should distinguish:

```text id="t8s3py"
application
Hindsight
Groq
```

Example internal diagnostic state:

```json id="5g5x7k"
{
  "application": "healthy",
  "hindsight": "healthy",
  "groq": "degraded"
}
```

This information should not expose credentials or sensitive implementation details to unauthenticated public users.

---

# 22. Hindsight Availability

Hindsight is a load-bearing dependency.

When unavailable:

```text id="nhwqv0"
Historical memory
→ unavailable

Historical assessment
→ unavailable/degraded
```

The backend must not silently substitute:

```text id="zvgrm3"
history = []
```

This distinction is operationally critical.

---

# 23. Groq Availability

Groq is an interpretation/explanation dependency.

When unavailable:

```text id="1p9lwu"
Historical memory
→ available

Evidence engine
→ available

Assessment
→ available

LLM explanation
→ unavailable
```

The system should remain useful without the explanation layer.

---

# 24. Timeout Configuration

External requests must have explicit timeouts.

At minimum:

```text id="o1jv7d"
Hindsight request timeout
Groq request timeout
```

Never allow an external dependency to block a backend request indefinitely.

Timeout values should be configurable.

---

# 25. Retry Policy

Retries should be selective.

Appropriate candidates may include transient:

* network failures
* connection resets
* temporary service-unavailable responses

Avoid aggressive retries for:

* invalid requests
* authentication failures
* malformed responses
* deterministic validation errors

Retries must have a bounded maximum.

---

# 26. Retry Safety

A retry must not create duplicate reports.

For write operations:

```text id="2iqt0u"
client request
     ↓
idempotency mechanism
     ↓
safe retry
```

This is particularly important for report submission.

---

# 27. Rate Limiting

The public API should have request limits appropriate to the deployment environment.

At minimum consider limits for:

```text id="4t4a6m"
report submission
vehicle lookup
assessment retrieval
```

The exact limits should be established after deployment requirements are known.

Do not hardcode arbitrary limits into the frontend.

---

# 28. Request Size Limits

The backend should enforce request-size limits.

This protects against:

* accidentally huge reports
* memory exhaustion
* abusive payloads

The report text limit defined by the ingestion specification should be enforced independently.

---

# 29. Logging

Use structured logs.

A useful request log may contain:

```text id="m8oq2y"
timestamp
request_id
route
method
status
latency
environment
```

Dependency logs may include:

```text id="50qkq4"
dependency
operation
duration
success/failure
error category
```

---

# 30. Sensitive Logging Restrictions

Do not log:

* API keys
* authentication tokens
* raw credentials
* full sensitive user content
* unnecessary source identity information
* complete LLM prompts if they contain sensitive report content

Where report text is needed for debugging, use controlled redaction or synthetic test data.

---

# 31. Request IDs

Each backend request should have a request identifier.

Example:

```text id="x3e6hs"
request_id = req_01H...
```

The ID should appear in:

* backend logs
* error responses where appropriate
* operational diagnostics

This allows a failed request to be traced across services.

---

# 32. Error Classification

Operational errors should be classified.

Example categories:

```text id="q2cc4m"
VALIDATION_ERROR
MEMORY_UNAVAILABLE
MEMORY_TIMEOUT
LLM_UNAVAILABLE
LLM_TIMEOUT
LLM_INVALID_RESPONSE
DEPENDENCY_AUTH_ERROR
INTERNAL_ERROR
```

The frontend should receive safe, stable error categories rather than internal stack traces.

---

# 33. Exception Handling

The backend must not swallow exceptions silently.

Bad:

```python id="7z9j7n"
try:
    ...
except Exception:
    pass
```

Failures must either:

* be handled explicitly,
* be converted into a known application error,
* or propagate to centralized error handling and logging.

---

# 34. Graceful Shutdown

The backend should support graceful shutdown.

On shutdown:

```text id="9u5z9f"
Stop accepting new work
        ↓
Allow active requests to complete where possible
        ↓
Close external connections
        ↓
Exit
```

Deployment configuration should provide enough termination time for normal cleanup.

---

# 35. Deployment Strategy

The initial deployment may use a simple:

```text id="y7y4fo"
build
  ↓
deploy
  ↓
health check
  ↓
accept traffic
```

As operational requirements grow, use rolling or blue/green deployment mechanisms where appropriate.

Do not introduce complex deployment infrastructure before it is necessary.

---

# 36. Database / Persistent Application State

If the initial backend does not use a separate application database, do not introduce one solely for deployment completeness.

The system's historical vehicle memory is handled through the defined Hindsight integration.

If a relational database is introduced later for:

* authentication
* billing
* audit records
* application metadata

it must be documented as a separate persistence layer.

---

# 37. Hindsight Data Isolation

Hindsight configuration must clearly separate:

```text id="j3q2v7"
development memory
test memory
production memory
```

Vehicle IDs alone should not be relied upon to prevent environment mixing.

Use the appropriate namespace/tenant/configuration mechanism supported by the deployed Hindsight setup.

Provider-specific namespace behavior must be verified against the current Hindsight deployment documentation before production rollout.

---

# 38. Memory Backup Considerations

Because historical vehicle evidence is a core product asset, production memory requires a recovery strategy.

The operational plan should define:

* backup capability
* retention period
* restoration procedure
* recovery verification
* recovery ownership

The exact mechanism depends on the deployed Hindsight infrastructure.

Do not claim a backup guarantee until the selected Hindsight deployment provides and has been tested for that capability.

---

# 39. Recovery Testing

A recovery test should verify:

```text id="8q2whn"
Stored vehicle history
       ↓
Backup / recovery mechanism
       ↓
Restored memory
       ↓
Vehicle retrieval
       ↓
Evidence reconstruction
```

The restored history must produce the expected evidence state.

---

# 40. Recovery Objectives

Production operations should eventually define:

### RPO

Maximum acceptable amount of historical data that could be lost.

### RTO

Maximum acceptable time required to restore service.

Initial values should be selected based on the actual deployment requirements rather than invented for documentation purposes.

---

# 41. Data Retention

The product should define how long historical reports are retained.

Retention policy must consider:

* product requirements
* privacy requirements
* operational cost
* deletion requirements
* backup retention

Until a formal retention policy exists, the implementation should not silently delete historical evidence.

---

# 42. Data Deletion

If deletion functionality is introduced, deletion must account for all relevant representations of the report.

Potentially affected data includes:

```text id="m0l5ot"
original report
claim
vehicle memory
source memory
derived assessment
cached explanation
audit information
backup copies
```

Deletion semantics must be documented before implementing user-facing deletion.

---

# 43. Privacy Boundary

VeriCar should minimize stored personal information.

A report needs enough information to establish:

```text id="s8l7iq"
what was reported
when it was observed
who/what source type reported it
which vehicle it concerns
```

Avoid collecting unnecessary:

* names
* addresses
* phone numbers
* email addresses
* unrelated identity information

---

# 44. Vehicle Identifier Handling

Vehicle identifiers should be treated as potentially sensitive.

Do not unnecessarily expose full identifiers in:

* public URLs
* analytics events
* logs
* screenshots
* error reports

Where appropriate, use masked display:

```text id="p8j7xg"
••••••••4352
```

The exact masking policy should match the application's privacy requirements.

---

# 45. Authentication

Authentication is not required merely to demonstrate the evidence architecture.

If authentication is introduced, it should be implemented at the backend boundary.

The backend must not rely on frontend-only access controls.

Future authentication should define:

* identity
* sessions/tokens
* authorization
* vehicle access
* report ownership
* administrative access

---

# 46. Authorization

If multiple users are supported, a request for:

```http id="d8g5zv"
GET /api/vehicles/{vehicle_id}
```

must verify that the requesting user is authorized to access that vehicle's history.

Do not treat possession of a vehicle ID as sufficient authorization in a multi-user production environment.

---

# 47. Dependency Credential Failures

If Hindsight or Groq rejects credentials:

```text id="0l6vhr"
Do not retry indefinitely.
Log a safe dependency-authentication error.
Mark the dependency degraded.
Return a controlled application error.
```

The application should not expose provider credentials or raw provider error bodies to users.

---

# 48. Provider Rate Limits

External provider rate limits should be treated as operational conditions.

The system should:

1. detect rate-limit responses,
2. avoid uncontrolled retries,
3. record the dependency failure,
4. return a controlled response,
5. recover automatically when the dependency becomes available again.

Exact provider-specific limits must be verified from current provider documentation before production capacity planning.

---

# 49. Model Configuration

The LLM model identifier must be configuration-driven.

Example:

```text id="7y4t6g"
GROQ_MODEL=<configured-model>
```

Do not hardcode the model name throughout the application.

This allows controlled model upgrades.

---

# 50. Model Change Procedure

A model change should follow:

```text id="z4b5o9"
Update model configuration
       ↓
Run LLM grounding tests
       ↓
Run numerical integrity tests
       ↓
Run contradiction tests
       ↓
Run prompt-injection tests
       ↓
Review representative outputs
       ↓
Deploy
```

A new model must not be considered equivalent merely because it produces fluent text.

---

# 51. Hindsight Version Changes

Hindsight changes should also be treated as dependency changes.

Before upgrading:

```text id="2xv3j1"
Run persistence tests
Run retrieval tests
Run isolation tests
Run failure tests
Run representative vehicle scenarios
```

The project should record the deployed Hindsight version/configuration where the provider exposes such information.

---

# 52. Dependency Health Monitoring

Monitor at least:

```text id="p8d5p5"
Hindsight availability
Hindsight latency
Groq availability
Groq latency
API error rate
API latency
report-processing failures
```

The exact monitoring platform is deployment-specific.

---

# 53. Application Metrics

Useful application metrics include:

```text id="y4z7c1"
requests_total
request_errors_total
request_latency
report_submissions_total
report_submission_failures
memory_retrieval_failures
evidence_calculation_failures
llm_requests_total
llm_failures
llm_latency
```

Metrics should describe system behavior rather than create artificial product metrics.

Do not introduce vanity metrics such as:

```text id="7v1mnp"
AI intelligence score
trust score
AI accuracy
```

without a defensible measurement methodology.

---

# 54. Evidence Engine Monitoring

The evidence engine should expose operational information such as:

```text id="w3h6op"
calculation duration
number of evidence items processed
number of supporting sources
number of contradictory sources
```

These values are useful for debugging and performance monitoring.

They should not automatically become user-facing product metrics.

---

# 55. Alerting

Operational alerts should focus on actionable failures.

Examples:

```text id="z1i7cx"
High backend error rate
Hindsight unavailable
Groq unavailable
High report-processing failure rate
Unusual latency increase
Deployment health-check failure
```

Avoid alerting on every transient request failure.

---

# 56. Log Retention

Operational logs should have a defined retention policy.

The policy should balance:

* debugging requirements
* storage cost
* privacy
* security
* regulatory requirements where applicable

Do not retain sensitive report content in logs merely because logs have a long retention period.

---

# 57. Deployment Verification

Every production deployment should verify:

```text id="rx7bqf"
1. Application starts.
2. Health endpoint responds.
3. Frontend loads.
4. Backend API is reachable.
5. Hindsight connectivity works.
6. Groq connectivity works.
7. Test vehicle retrieval succeeds.
8. Test report submission succeeds.
9. Assessment calculation succeeds.
10. Explanation generation succeeds.
```

Production smoke tests should use designated synthetic test data where appropriate.

---

# 58. Smoke Test

A minimal post-deployment smoke test:

```text id="q0nj1r"
GET /health
       ↓
GET test vehicle
       ↓
POST test report
       ↓
GET test assessment
```

Expected:

```text id="b0w6tq"
all required services respond successfully
```

The smoke test must not mutate real production customer data.

---

# 59. Rollback

If a deployment causes a critical failure:

```text id="0xj3up"
Detect failure
     ↓
Stop rollout
     ↓
Rollback application
     ↓
Verify health
     ↓
Verify memory connectivity
     ↓
Verify representative assessment
```

Rollback should not erase or corrupt already persisted vehicle history.

---

# 60. Backward Compatibility

API changes should consider existing frontend clients.

Avoid silently changing:

```text id="w0y0n1"
field names
field types
enum values
error formats
assessment semantics
```

without coordinated frontend/backend deployment.

---

# 61. API Versioning

If breaking changes become necessary, use an explicit versioning strategy.

For example:

```text id="2s0h8y"
 /api/v1/...
 /api/v2/...
```

Do not introduce API versions merely for appearance.

The initial product may remain on an unversioned `/api` path until a real compatibility requirement exists.

---

# 62. Caching

Caching may be introduced for read-heavy operations where appropriate.

Potential candidates:

```text id="7stz5j"
vehicle history
assessment
source history
```

However, assessment caching must account for new reports.

After a new report:

```text id="5a7l2w"
old assessment cache
        ↓
invalidate
        ↓
recalculate
        ↓
new assessment
```

Stale assessments must not be presented as current.

---

# 63. Concurrent Report Submission

Concurrent submissions for the same vehicle must not cause:

* lost reports
* duplicate reports
* corrupted evidence state
* stale assessment persistence

The backend should define appropriate ordering and recalculation behavior.

---

# 64. Race Condition Scenario

Example:

```text id="v4k8n1"
Request A
Mechanic report

Request B
Inspector report
```

Both arrive nearly simultaneously.

Expected:

```text id="x8b3de"
Both reports persist.
Final vehicle state incorporates both.
```

The system must not calculate the final assessment from only one request because of a race.

---

# 65. Operational Boundaries

The following components have different failure characteristics:

```text id="2xw4cn"
Frontend
→ presentation

Backend
→ orchestration and deterministic logic

Hindsight
→ persistent historical memory

Evidence engine
→ deterministic evidence calculation

Groq
→ natural-language interpretation
```

Operational diagnostics should preserve these boundaries.

---

# 66. What the System Must Never Do

In production, VeriCar must never:

* fabricate historical reports
* convert memory failure into empty history
* expose API credentials
* treat LLM output as authoritative numerical state
* overwrite contradictory reports
* count repeated same-source reports as independent sources
* present evidence confidence as probability
* present source reliability as professional qualification
* present an evidence finding as a mechanical diagnosis
* silently discard failed memory writes
* silently swallow external-service failures
* expose internal stack traces to users

---

# 67. Operational Runbook: Hindsight Failure

If Hindsight becomes unavailable:

```text id="5k6b4s"
1. Confirm dependency health.
2. Check backend memory error logs.
3. Verify credentials/configuration.
4. Check network connectivity.
5. Check provider/service status where available.
6. Retry through controlled recovery.
7. Verify historical retrieval.
8. Run representative assessment test.
```

Do not tell users that the vehicle has no history unless an actual successful retrieval returned an empty history.

---

# 68. Operational Runbook: Groq Failure

If Groq becomes unavailable:

```text id="b3f9qz"
1. Confirm dependency health.
2. Check timeout/rate-limit errors.
3. Verify credentials.
4. Check configured model.
5. Confirm evidence engine remains operational.
6. Restore LLM connectivity.
7. Run explanation grounding test.
```

During the incident, evidence and deterministic assessment functionality should remain available where possible.

---

# 69. Operational Runbook: Backend Failure

If the backend becomes unavailable:

```text id="6k7m5n"
1. Check deployment health.
2. Check application logs.
3. Check resource utilization.
4. Check recent deployment.
5. Roll back if required.
6. Verify health endpoint.
7. Verify Hindsight connectivity.
8. Verify representative API request.
```

---

# 70. Operational Runbook: Bad Deployment

If a new release introduces incorrect behavior:

```text id="9q2r8m"
1. Stop rollout.
2. Identify affected version.
3. Roll back application code.
4. Verify API health.
5. Verify historical retrieval.
6. Verify evidence calculations.
7. Verify frontend.
8. Investigate before redeployment.
```

If a release changed persistent data structures, rollback must be evaluated carefully rather than performed blindly.

---

# 71. Production Checklist

Before initial production deployment:

### Application

* [ ] Production configuration is defined.
* [ ] Dependencies are pinned.
* [ ] Production build succeeds.
* [ ] Development debugging is disabled.

### Security

* [ ] Secrets are stored securely.
* [ ] Secrets are absent from source control.
* [ ] HTTPS is configured.
* [ ] CORS is restricted.
* [ ] Request limits are configured.
* [ ] Error responses do not expose internals.

### Hindsight

* [ ] Production memory is isolated.
* [ ] Credentials are configured.
* [ ] Persistence has been tested.
* [ ] Recovery strategy is documented.
* [ ] Backup capability has been verified if provided by the deployment.

### Groq

* [ ] Production credential is configured.
* [ ] Model is explicitly configured.
* [ ] Timeout is configured.
* [ ] Failure behavior is tested.
* [ ] Grounding tests pass.

### Backend

* [ ] Health endpoint works.
* [ ] Readiness behavior is defined.
* [ ] Structured logging works.
* [ ] Request IDs are available.
* [ ] Error classification is implemented.

### Frontend

* [ ] Production API URL is configured.
* [ ] No private secrets are bundled.
* [ ] Empty states work.
* [ ] Dependency failure states work.
* [ ] Responsive layout is verified.

---

# 72. Post-Deployment Verification

Immediately after deployment:

```text id="3u6r9v"
Health
  ↓
Frontend
  ↓
API
  ↓
Hindsight
  ↓
Groq
  ↓
Report ingestion
  ↓
Evidence calculation
  ↓
Assessment
  ↓
Explanation
```

A deployment should not be considered complete merely because the homepage loads.

---

# 73. Production Observability Checklist

The operational system should allow the team to answer:

```text id="0qj4qf"
Is the backend running?

Can users reach it?

Can reports be submitted?

Can historical memory be retrieved?

Is evidence calculation succeeding?

Is Groq available?

Are explanations being generated?

Are requests becoming slower?

Are failures increasing?

Did the latest deployment introduce the problem?
```

If these questions cannot be answered from available diagnostics, observability is incomplete.

---

# 74. Capacity Planning

Initial deployment should be sized according to measured workload rather than speculative scale.

Monitor:

* concurrent requests
* average and tail latency
* memory usage
* CPU usage
* Hindsight latency
* Groq latency
* report-processing throughput

Scale only when measurements indicate a requirement.

---

# 75. Horizontal Scaling Considerations

The backend should avoid relying on process-local mutable state for vehicle history.

This allows multiple backend instances:

```text id="f6czg4"
             ┌─ Backend A
Browser → LB ├─ Backend B
             └─ Backend C
                  |
                  v
             Hindsight
```

Historical state should remain in the designated persistent memory layer rather than an individual backend process.

---

# 76. Stateless Backend Principle

The backend should preferably be stateless with respect to persistent vehicle history.

Local process memory may contain:

* configuration
* short-lived request state
* temporary caches

but must not become the authoritative vehicle-history store.

---

# 77. Disaster Recovery

A production disaster-recovery plan should cover:

```text id="x5o4d1"
Backend infrastructure failure
Frontend hosting failure
Hindsight failure
Credential loss
Configuration loss
Deployment failure
```

Recovery procedures should be tested periodically once the system reaches production maturity.

---

# 78. Operational Documentation

The repository should eventually contain:

```text id="4e1h2x"
docs/
├── ...
├── 19-deployment-and-operations.md
└── runbooks/
    ├── hindsight-outage.md
    ├── llm-outage.md
    ├── deployment-rollback.md
    └── recovery.md
```

The runbooks may initially remain lightweight.

---

# 79. Provider-Specific Verification

Before production deployment, verify the current official documentation for:

### Hindsight

Verify:

* current deployment options
* authentication mechanism
* namespace/tenant isolation
* persistence guarantees
* backup/recovery options
* API limits
* current SDK/API behavior
* production security requirements

### Groq

Verify:

* current API authentication
* currently supported model identifiers
* rate limits
* request/token limits
* timeout behavior
* error/status semantics
* current model lifecycle/deprecation status

### Hosting provider

Verify:

* runtime support
* HTTPS configuration
* environment secrets
* health checks
* deployment behavior
* resource limits
* logs
* networking
* scaling
* rollback capabilities

These values should be recorded in the deployment configuration and operational notes at deployment time.

---

# 80. External Dependency Change Policy

External provider behavior must not be assumed to remain static.

When a provider changes:

```text id="j7x3wq"
Provider update
     ↓
Review official documentation
     ↓
Update configuration
     ↓
Run integration tests
     ↓
Run regression scenarios
     ↓
Deploy
```

Do not upgrade a dependency solely because a newer version exists.

---

# 81. Definition of Done

Doc 19 is implemented when:

### Deployment

* [ ] Development, test, and production environments are separated.
* [ ] Production deployment is reproducible.
* [ ] Dependencies are pinned.
* [ ] Frontend and backend deployment configuration is defined.

### Security

* [ ] Secrets are managed outside source control.
* [ ] Frontend contains no private credentials.
* [ ] HTTPS is enabled in production.
* [ ] CORS is explicitly configured.
* [ ] Request limits are defined.
* [ ] Sensitive information is excluded from logs.

### Reliability

* [ ] Health endpoint exists.
* [ ] Readiness behavior is defined where supported.
* [ ] Hindsight failure is explicitly represented.
* [ ] Groq failure is explicitly represented.
* [ ] External requests have bounded timeouts.
* [ ] Retry behavior is bounded and safe.
* [ ] Report writes are idempotent where required.
* [ ] Graceful shutdown is supported.

### Observability

* [ ] Structured logging exists.
* [ ] Request IDs exist.
* [ ] Dependency failures are classified.
* [ ] Application latency can be measured.
* [ ] Hindsight health can be diagnosed.
* [ ] Groq health can be diagnosed.
* [ ] Operational alerts are defined.

### Data

* [ ] Production memory is isolated.
* [ ] Vehicle history recovery requirements are documented.
* [ ] Retention behavior is defined.
* [ ] Sensitive data collection is minimized.
* [ ] Vehicle identifiers are handled appropriately.

### Operations

* [ ] Deployment smoke test exists.
* [ ] Rollback procedure exists.
* [ ] Hindsight outage runbook exists.
* [ ] Groq outage runbook exists.
* [ ] Backend failure runbook exists.
* [ ] Provider-specific production requirements have been verified against current official documentation.

---

# 82. Final Architecture Boundary

The completed operational architecture is:

```text id="9c5t3h"
                         INTERNET
                            |
                            v
                  ┌───────────────────┐
                  │      Frontend     │
                  │   HTML/CSS/JS     │
                  └─────────┬─────────┘
                            |
                         HTTPS/JSON
                            |
                            v
                  ┌───────────────────┐
                  │ Python Backend    │
                  │                   │
                  │ API               │
                  │ Validation        │
                  │ Orchestration     │
                  │ Evidence Engine   │
                  │ Memory Adapter    │
                  │ LLM Adapter       │
                  └──────┬──────┬─────┘
                         |      |
                         |      |
                         v      v
                  ┌─────────┐ ┌─────────┐
                  │Hindsight│ │  Groq   │
                  │ Memory  │ │   LLM   │
                  └─────────┘ └─────────┘
```

The responsibility of each layer remains explicit:

```text id="7j1f2n"
Frontend
→ presentation and interaction

Backend
→ validation, orchestration, deterministic logic

Hindsight
→ persistent historical memory

Evidence Engine
→ evidence weighting and confidence

Groq
→ semantic interpretation and explanation
```

No external service is allowed to silently become the system's source of truth.

---

# 83. Final Product Integrity Principle

The operational system must preserve the fundamental VeriCar property:

```text id="e9f0yb"
Historical evidence
        ↓
Persistent memory
        ↓
Evidence aggregation
        ↓
Assessment
        ↓
Explanation
```

Not:

```text id="y8z9q1"
Latest report
        ↓
LLM
        ↓
AI answer
```

The deployment architecture exists to preserve this distinction reliably in production.

---

# 84. Project Documentation Completion

The VeriCar technical specification set is now complete:

```text id="2a7c1m"
01  Project Concept
02  Product Requirements
03  System Architecture
04  Memory Model
05  Scoring and Evidence Model
06  Data Model
07  Hindsight Memory Design
08  Hindsight Memory Contract
09  Project Setup Specification
10  Backend Foundation Specification
11  Hindsight Integration Plan
12  Structured Report Ingestion
13  Evidence and Scoring Engine
14  LLM Reasoning and Explanation
15  Assessment API and Backend Orchestration
16  Frontend Specification
17  Integration and Testing
18  Test Data and Scenarios
19  Deployment and Operations
```

At this point, the repository should move from **specification** into **implementation**.

The first implementation milestone should be the backend foundation and report-ingestion path, followed by the Hindsight integration, deterministic evidence engine, assessment API, and frontend.
