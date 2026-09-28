# VeriCar — Hindsight Integration Plan

## 1. Purpose

Integrate the real Hindsight memory system into VeriCar.

The goal of this stage is to prove one complete memory loop:

    write memory
        ↓
    persist memory
        ↓
    retrieve memory later
        ↓
    use retrieved memory in VeriCar

At the end of this stage, Hindsight must be a functioning part of the backend rather than a documented dependency.

Do not implement:

- evidence scoring
- confidence calculation
- Groq reasoning
- frontend
- complex report processing

Those belong to later stages.

---

## 2. Hindsight's Role

Hindsight is the persistent memory layer.

VeriCar uses it for two logical memory scopes:

    Vehicle Memory
        |
        +-- historical reports
        +-- observations
        +-- issues
        +-- corroboration
        +-- contradictions
        +-- temporal context

    Source Memory
        |
        +-- historical reports
        +-- corroboration history
        +-- contradiction history
        +-- unresolved reports
        +-- reporting behavior

The project proposal explicitly describes this two-namespace architecture. 

---

## 3. Integration Architecture

The backend should communicate with Hindsight through one internal service:

    API Route
        |
        v
    MemoryService
        |
        v
    Hindsight
        |
        v
    Historical Memory

The rest of the application must not call Hindsight directly.

For example:

    report route
        |
        v
    memory_service.py
        |
        v
    Hindsight client/API

This isolates Hindsight-specific implementation details.

---

## 4. Verify the Actual Hindsight API First

Before writing the Hindsight client code, verify the official Hindsight documentation.

Confirm:

- authentication mechanism
- Python SDK availability
- package name
- client initialization
- memory write operation
- memory retrieval operation
- memory identity / namespace mechanism
- metadata support
- filtering support
- response format
- error behavior
- local versus cloud configuration

Do not invent method names.

Do not assume that a logical namespace such as:

    vehicle:VEH-001

is necessarily the literal Hindsight API syntax.

The application design uses logical scopes; the implementation must map them to the actual Hindsight interface.

---

## 5. Configuration

Extend:

    backend/app/config.py

with the Hindsight configuration required by the verified API.

Conceptually:

    HINDSIGHT_API_KEY=
    HINDSIGHT_BASE_URL=

The exact variables depend on the actual Hindsight deployment/API.

Update:

    .env.example

with placeholders only.

Never commit:

    .env

or real credentials.

---

## 6. Hindsight Client

Create a small Hindsight integration layer.

Conceptually:

    backend/app/services/
        memory_service.py

The service should encapsulate:

    Hindsight client initialization
    memory writes
    memory retrieval
    error translation

The rest of VeriCar should not need to know:

- SDK method names
- HTTP paths
- authentication headers
- Hindsight-specific response structures

---

## 7. MemoryService Interface

The application-level interface should be approximately:

    class MemoryService:

        remember_vehicle_event(...)

        remember_source_event(...)

        retrieve_vehicle_history(...)

        retrieve_source_history(...)

These are application interfaces.

They are NOT claims about the Hindsight SDK.

The actual implementation must use the verified Hindsight API.

---

## 8. First Integration Test

Before connecting real VeriCar reports, perform the smallest possible Hindsight test.

Write:

    "Vehicle VEH-TEST-001 was inspected on 2026-09-28.
     The inspector reported a hard 2->3 transmission shift."

Associate the memory with:

    vehicle = VEH-TEST-001
    source = SRC-TEST-001
    report = RPT-TEST-001

Then retrieve the vehicle history.

Expected result:

The previously written memory is returned.

This is the first proof that Hindsight is functioning.

---

## 9. Persistence Test

The important test is not:

    write
    ↓
    immediately read

The important test is:

    process A
        ↓
    write memory

    process ends

    process B
        ↓
    retrieve memory

The memory should still be available.

This demonstrates persistent memory rather than an in-process cache.

---

## 10. Vehicle Memory

Implement the first real memory scope:

    VEHICLE MEMORY

Logical identity:

    vehicle:{vehicle_id}

Example:

    vehicle:VEH-001

A vehicle memory event should contain enough information to reconstruct its context.

Conceptual payload:

    {
      "vehicle_id": "VEH-001",
      "report_id": "RPT-001",
      "source_id": "SRC-001",
      "source_type": "inspector",
      "reported_at": "2026-09-28",
      "issue_candidate": "transmission_shift_behavior",
      "observation": "Hard 2->3 shift observed during inspection."
    }

The exact Hindsight representation depends on the verified API.

---

## 11. Source Memory

Implement the second logical memory scope:

    SOURCE MEMORY

Logical identity:

    source:{source_id}

Example:

    source:SRC-001

Conceptual payload:

    {
      "source_id": "SRC-001",
      "source_type": "inspector",
      "report_id": "RPT-001",
      "vehicle_id": "VEH-001",
      "reported_at": "2026-09-28",
      "issue_candidate": "transmission_shift_behavior",
      "observation": "Hard 2->3 shift observed during inspection."
    }

This allows the same source's reporting history to accumulate across different vehicles.

---

## 12. Why Source Memory Is Important

Vehicle memory answers:

    What has happened to this vehicle?

Source memory answers:

    What has this source historically reported?

These are different questions.

For example:

    VEH-001
        |
        +-- inspector A
        +-- mechanic B
        +-- owner C

while:

    mechanic B
        |
        +-- VEH-001
        +-- VEH-017
        +-- VEH-031
        +-- VEH-042

The second history is required to estimate the source's historical reporting reliability.

---

## 13. Metadata

Where supported by Hindsight, memory records should include metadata such as:

    vehicle_id
    source_id
    report_id
    source_type
    issue_candidate
    reported_at

The metadata should make memories traceable.

Every important memory should be connectable to:

    Vehicle
        ↓
    Report
        ↓
    Source

---

## 14. Original Report Preservation

Hindsight is not the authoritative storage location for the original report.

The structured application data must preserve the original report.

Hindsight stores useful historical memory derived from that report.

Therefore:

    Original Report
          |
          +------> Structured application data
          |
          +------> Hindsight historical memory

This prevents loss of the original evidence.

---

## 15. Vehicle Retrieval

Implement:

    retrieve_vehicle_history(vehicle_id, query)

The query should support relevant historical context.

Example:

    vehicle_id:
        VEH-001

    query:
        transmission shift behavior,
        hesitation,
        hard shifting

Expected conceptual results:

    RPT-001
    Inspector:
    Hard 2->3 shift observed.

    RPT-002
    Mechanic:
    Transmission hesitation.

    RPT-003
    Owner:
    Transmission operating normally.

The retrieval must not intentionally exclude contradictory memories.

---

## 16. Source Retrieval

Implement:

    retrieve_source_history(source_id, query)

Example:

    source_id:
        SRC-003

    query:
        reporting history and corroboration

Expected conceptual context:

    Previous reports:
        18 resolved
        14 corroborated
        2 contradicted
        2 unresolved

If the source has few reports, the system should preserve that fact rather than manufacturing confidence.

---

## 17. Semantic Retrieval

Vehicle retrieval should eventually support semantic relevance.

For example, a query about:

    "transmission hesitation"

should be capable of finding historical observations such as:

    "hard 2->3 shift"

    "rough shifting into third"

    "delayed transmission engagement"

Exact implementation depends on Hindsight's actual retrieval behavior and API.

Do not add a separate semantic-search infrastructure unless Hindsight's capabilities require it.

---

## 18. Contradiction Retrieval

Test that conflicting memories remain retrievable.

Write:

    Owner:
    "Transmission works perfectly."

Then:

    Inspector:
    "Hard 2->3 shift observed."

Then retrieve:

    "transmission"

The result should contain both historical observations.

The system must not overwrite:

    "works perfectly"

with:

    "hard 2->3 shift"

Historical claims remain historical claims.

---

## 19. Same-Source Repetition

Test repeated reports from the same source.

Example:

    SRC-001
        |
        +-- VEH-001
        +-- VEH-002
        +-- VEH-003

The memories should remain individually traceable.

Repeated reports from one source must not automatically be treated as independent corroboration.

That independence calculation belongs to the evidence engine.

---

## 20. Cross-Vehicle Source Memory

This is an important test.

Create:

    SRC-TEST-001

Then write reports concerning:

    VEH-001
    VEH-002
    VEH-003

Retrieve:

    source:SRC-TEST-001

The result should demonstrate that source memory spans multiple vehicles.

This is what allows future source reliability to be based on historical reporting behavior rather than a single report.

---

## 21. Failure Handling

If Hindsight is unavailable:

    MemoryService
        |
        v
    Hindsight error
        |
        v
    controlled application error/state

Do not:

    catch error
    ↓
    return empty history

That would falsely tell the user:

    "No history exists."

when the real state is:

    "History could not be retrieved."

---

## 22. Memory Failure States

The service should distinguish:

    AVAILABLE

    EMPTY

    UNAVAILABLE

Meaning:

AVAILABLE:
    Hindsight responded and relevant memories exist.

EMPTY:
    Hindsight responded successfully but no relevant memories exist.

UNAVAILABLE:
    Hindsight could not be queried reliably.

These states will later be exposed to the API and frontend.

---

## 23. Logging

Log integration events such as:

    Hindsight memory write started
    Hindsight memory write succeeded
    Hindsight memory write failed
    Hindsight retrieval started
    Hindsight retrieval succeeded
    Hindsight retrieval failed

Do not log:

    API keys
    authentication tokens
    unnecessary sensitive data

---

## 24. Tests

Create Hindsight-specific tests.

Conceptually:

    backend/tests/
        test_memory.py

Tests should eventually cover:

    [ ] client initialization

    [ ] vehicle memory write

    [ ] source memory write

    [ ] vehicle memory retrieval

    [ ] source memory retrieval

    [ ] persistent retrieval

    [ ] contradictory memories

    [ ] repeated source reports

    [ ] cross-vehicle source history

    [ ] empty history

    [ ] Hindsight failure

---

## 25. Integration Test Sequence

The minimum successful sequence is:

    1. Start backend

    2. Connect to Hindsight

    3. Write test vehicle memory

    4. Retrieve test vehicle memory

    5. Verify report_id

    6. Verify vehicle_id

    7. Write test source memory

    8. Retrieve source memory

    9. Verify source_id

    10. Restart backend

    11. Retrieve the same memory again

    12. Confirm persistence

---

## 26. End-to-End Memory Test

After basic tests pass, perform this scenario:

Step 1:

    VEH-TEST-001
    No history

Step 2:

    Owner report:
    "Vehicle runs normally."

Step 3:

    Inspector report:
    "Hard 2->3 shift observed."

Step 4:

    Retrieve vehicle memory.

Expected:

    Owner observation
    +
    Inspector observation

Step 5:

    Retrieve source memory for the inspector.

Expected:

    Inspector's historical report is available.

This demonstrates that memory exists across multiple interactions.

---

## 27. What This Stage Proves

At the end of Hindsight Integration we should be able to demonstrate:

    Report
       |
       v
    Hindsight
       |
       v
    Memory persists
       |
       v
    Later request
       |
       v
    Memory retrieved
       |
       v
    Historical context available

This is the minimum technical proof that Hindsight is genuinely load-bearing.

---

## 28. Definition of Done

Hindsight Integration is complete when:

[ ] Actual Hindsight API has been verified

[ ] Hindsight credentials are configured safely

[ ] MemoryService exists

[ ] Vehicle memory can be written

[ ] Source memory can be written

[ ] Vehicle memory can be retrieved

[ ] Source memory can be retrieved

[ ] Memory survives backend restart

[ ] Contradictory memories remain retrievable

[ ] Same-source reports remain distinguishable

[ ] Source history spans multiple vehicles

[ ] Empty history is distinguishable from failure

[ ] Hindsight errors are not swallowed

[ ] Hindsight tests pass

[ ] No scoring logic exists yet

[ ] No Groq reasoning exists yet

[ ] No frontend dependency exists yet

---

## 29. Next Stage

After Hindsight Integration is verified, move to:

    12 — Structured Report Ingestion

That stage will connect a real VeriCar report to the memory system:

    Report
       |
       v
    Validation
       |
       v
    Structured Report
       |
       v
    Claim
       |
       v
    Vehicle Memory
       |
       v
    Source Memory

Only after that should we build the evidence and scoring engine.