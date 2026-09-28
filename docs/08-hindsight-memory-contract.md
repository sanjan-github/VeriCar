# VeriCar — Hindsight Memory Contract

## 1. Purpose

This document defines the interface between the VeriCar backend and Hindsight.

The contract specifies:

- what VeriCar writes to memory
- when memory is written
- what memory is retrieved
- when retrieval occurs
- how retrieved memory enters evidence analysis
- what information remains authoritative
- how memory failures are handled

The exact Hindsight SDK/API syntax will be implemented according to the official Hindsight API documentation.

---

## 2. Core Rule

Hindsight = persistent historical memory

Application database = structured source of truth

Evidence engine = deterministic reasoning

Groq = explanation and semantic interpretation

No single layer should silently take over the responsibilities of another.

---

## 3. Memory Scopes

VeriCar uses two logical memory scopes.

Vehicle Memory:
    vehicle:{vehicle_id}

Source Memory:
    source:{source_id}

These are logical scopes for the application design.

Their actual implementation must use the supported Hindsight mechanism.

---

## 4. Vehicle Memory Write Contract

Whenever a valid report is accepted, VeriCar should create a vehicle-memory event.

Conceptual payload:

{
  "vehicle_id": "VEH-001",
  "report_id": "RPT-004",
  "source_id": "SRC-027",
  "source_type": "mechanic",
  "reported_at": "2026-04-19",
  "issue_candidate": "transmission_shift_behavior",
  "observation": "Transmission hesitation confirmed during test drive."
}

The memory should preserve the meaning of the observation while retaining identifiers that allow the system to trace it back to the original report.

---

## 5. Source Memory Write Contract

The same accepted report should create a source-memory event.

Conceptual payload:

{
  "source_id": "SRC-027",
  "source_type": "mechanic",
  "report_id": "RPT-004",
  "vehicle_id": "VEH-001",
  "reported_at": "2026-04-19",
  "issue_candidate": "transmission_shift_behavior",
  "observation": "Transmission hesitation confirmed during test drive."
}

This allows the system to build a longitudinal history of the source's reporting behavior.

---

## 6. What Gets Written

For V1, memory writes should contain:

- vehicle_id
- source_id
- report_id
- source_type
- report date
- issue candidate
- observation

Where supported, additional metadata may include:

- make
- model
- year
- claim polarity
- relationship status

Do not write derived confidence values as the primary historical memory.

---

## 7. Write Timing

The write sequence is:

POST /api/reports
        |
        v
Validate report
        |
        +---- invalid ----> Reject
        |
        v
Persist report
        |
        v
Interpret report
        |
        v
Write vehicle memory
        |
        v
Write source memory
        |
        v
Retrieve relevant history
        |
        v
Recalculate assessment

Rejected reports must not become evidence in persistent memory.

---

## 8. Vehicle Retrieval Contract

Before evaluating a new report, retrieve relevant historical memories for the vehicle.

Conceptually:

{
  "vehicle_id": "VEH-001",
  "query": "transmission shift behavior, hesitation, hard shifting"
}

The retrieval should seek semantically relevant historical observations.

Potential results:

RPT-002
Inspector:
Hard 2->3 shift observed.

RPT-003
Mechanic:
Transmission hesitation.

RPT-001
Owner:
Transmission operating normally.

---

## 9. Source Retrieval Contract

Retrieve relevant historical information about the source.

Conceptually:

{
  "source_id": "SRC-027",
  "query": "historical reporting behavior and corroboration"
}

Potential result:

SRC-027

18 resolved reports
14 corroborated
2 contradicted
2 unresolved

The backend can then use the underlying historical events to calculate effective source reliability.

---

## 10. Retrieval Must Include Contradictions

The retrieval layer must not intentionally return only evidence supporting the latest report.

For example, if the current report says:

"Transmission works perfectly."

The retrieval should still surface:

Owner:
Transmission works perfectly.

Inspector:
Hard 2->3 shift.

Mechanic:
Transmission hesitation.

The evidence engine must receive both supporting and contradicting information.

---

## 11. Retrieval → Evidence Conversion

Hindsight returns historical context.

The backend converts that context into structured evidence.

Example Hindsight memory:

"Independent inspector reported a hard 2->3
shift on 2026-03-04."

The backend resolves it to:

{
  "report_id": "RPT-002",
  "source_id": "SRC-002",
  "source_type": "inspector",
  "issue": "transmission_shift_behavior",
  "relationship": "supporting",
  "independent": true
}

The evidence engine then operates on the structured representation.

---

## 12. Hindsight Does Not Calculate Confidence

Hindsight provides historical context.

The deterministic backend calculates:

- source reliability
- support weight
- contradiction weight
- independence
- evidence confidence
- assessment status
- observation span

Therefore:

Hindsight
    |
    v
Historical evidence
    |
    v
Backend evidence model
    |
    v
Confidence calculation

Not:

Hindsight
    |
    v
"86% confidence"

---

## 13. Hindsight Does Not Create Facts

A retrieved memory such as:

"Mechanic reported transmission hesitation."

means:

A mechanic reported transmission hesitation.

It does not mean:

The transmission definitely has a mechanical defect.

The claim/evidence/finding distinction remains intact.

---

## 14. Traceability Contract

Every current finding should be traceable through:

Finding
   |
   v
Evidence
   |
   v
Report
   |
   v
Source

Memory should provide the reverse historical path:

Memory
   |
   v
Report ID
   |
   v
Original Report

Therefore:

No important historical statement should exist without an identifier connecting it to the underlying report.

---

## 15. Derived State

These values remain application-derived:

- historical_reliability
- effective_reliability
- support_weight
- contradiction_weight
- evidence_confidence
- assessment_status
- observation_span

They can change when new evidence arrives.

Historical memories should not be rewritten merely because these values change.

---

## 16. Current Assessment Flow

The complete V1 flow is:

New Report
    |
    v
Validate
    |
    v
Persist Report
    |
    v
Interpret Claim
    |
    v
Write Vehicle Memory
    |
    v
Write Source Memory
    |
    v
Retrieve Vehicle History
    |
    v
Retrieve Source History
    |
    v
Resolve Historical Reports
    |
    v
Build Evidence
    |
    v
Calculate Source Reliability
    |
    v
Calculate Evidence Confidence
    |
    v
Determine Assessment
    |
    v
Ask Groq for Explanation
    |
    v
Return Structured Result

---

## 17. Groq Contract

Groq receives structured evidence and relevant historical context.

Example:

{
  "vehicle": {
    "vehicle_id": "VEH-001"
  },
  "finding": {
    "issue": "transmission_shift_behavior"
  },
  "evidence": [
    {
      "source_type": "owner",
      "relationship": "contradicting",
      "date": "2026-01-10"
    },
    {
      "source_type": "inspector",
      "relationship": "supporting",
      "date": "2026-03-04"
    },
    {
      "source_type": "mechanic",
      "relationship": "supporting",
      "date": "2026-04-19"
    }
  ],
  "evidence_confidence": 82.4
}

Groq may explain this.

Groq must not invent:

- reports
- dates
- sources
- confidence values
- corroboration
- contradictions
- historical events

---

## 18. Memory Failure Contract

There are three different states.

### State A — Empty History

Hindsight request succeeded.

No relevant memories exist.

Return:

history_status = "empty"

### State B — Memory Available

Hindsight request succeeded.

Relevant memories were retrieved.

Return:

history_status = "available"

### State C — Memory Unavailable

Hindsight request failed.

Return:

history_status = "unavailable"

The system must never convert State C into State A.

---

## 19. Example API-Level Response

The backend can expose a structured result such as:

{
  "vehicle_id": "VEH-001",
  "history_status": "available",
  "finding": {
    "issue": "transmission_shift_behavior",
    "status": "strong_evidence",
    "evidence_confidence": 82.4
  },
  "evidence": {
    "supporting_reports": 3,
    "contradicting_reports": 1,
    "independent_supporting_sources": 3
  },
  "explanation": "The assessment increased because..."
}

The frontend should not need to understand Hindsight internals.

---

## 20. V1 Memory Contract Rules

The implementation must satisfy:

[ ] Every valid report can create vehicle memory

[ ] Every valid report can create source memory

[ ] Memory contains report/source/vehicle traceability

[ ] Vehicle history can be retrieved

[ ] Source history can be retrieved

[ ] Retrieval supports semantic relevance

[ ] Contradictory evidence can be retrieved

[ ] Retrieved memories can be resolved to reports

[ ] Evidence engine consumes structured evidence

[ ] Scoring remains deterministic

[ ] Groq cannot modify evidence facts

[ ] Historical memories are not overwritten by current scores

[ ] Empty memory is different from memory failure

[ ] Memory failure cannot produce a false clean-history result

---

## 21. Hindsight Integration Boundary

The backend should isolate Hindsight behind a small internal interface.

Conceptually:

class MemoryService:
    def remember_vehicle_event(...):
        ...

    def remember_source_event(...):
        ...

    def retrieve_vehicle_history(...):
        ...

    def retrieve_source_history(...):
        ...

These are application-level interfaces, not claims about the actual Hindsight SDK.

The implementation underneath them will use the verified Hindsight API.

This keeps the rest of VeriCar independent from Hindsight-specific SDK details.

---

## 22. Final Architecture

                    VERICAR BACKEND
                         |
          +--------------+--------------+
          |                             |
          v                             v
   Structured Data                 MemoryService
          |                             |
          |                             v
          |                         Hindsight
          |                             |
          |                    Historical Context
          |                             |
          +--------------+--------------+
                         |
                         v
                  Evidence Engine
                         |
                         v
                  Scoring Engine
                         |
                         v
                       Groq
                         |
                         v
                   API Response
                         |
                         v
                     Frontend

The critical loop is:

PERSIST
   ↓
RETRIEVE
   ↓
COMPARE
   ↓
CORROBORATE / CONTRADICT
   ↓
CALCULATE
   ↓
EXPLAIN
   ↓
PERSIST NEW CONTEXT

This is the actual memory-driven behavior VeriCar must demonstrate.

---

## 23. Implementation Note

Before coding the MemoryService, verify the official Hindsight API for:

- authentication
- memory write operation
- memory retrieval/search operation
- namespace or memory identity mechanism
- metadata support
- filtering
- response structure
- error handling
- local/deployed configuration

Do not invent Hindsight API calls based on this design document.

The design above defines what VeriCar needs from Hindsight.

The verified Hindsight API documentation determines how those operations are implemented.