from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
from logging import getLogger
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.models.report import (
    ReportSubmission,
    build_claim,
    generate_report_id,
    to_vehicle_report,
)
from backend.app.services.hindsight_factory import create_hindsight_repository
from backend.app.services.memory_service import MemoryService
from backend.app.services.assessment_service import AssessmentService
from backend.app.services.groq_explanation_service import GroqExplanationService
from core.database import Database, DEFAULT_DB_PATH


logger = getLogger(__name__)
IDEMPOTENCY_LEASE_SECONDS = 30.0
IDEMPOTENCY_POLL_SECONDS = 5.0
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    repository = create_hindsight_repository()
    memory_service = MemoryService(repository)
    app.state.memory_service = memory_service
    db_path = getattr(settings, "db_path", DEFAULT_DB_PATH)
    app.state.database = Database(db_path)

    if settings.hindsight_startup_check:
        try:
            version = await memory_service.check_version()
            logger.info("Hindsight server version: %s", version)
        except Exception as exc:
            await memory_service.close()
            raise RuntimeError(
                "Hindsight startup check failed. Verify HINDSIGHT_BASE_URL, "
                "credentials, and server compatibility."
            ) from exc

    try:
        yield
    finally:
        await memory_service.close()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)


def get_memory_service(request: Request) -> MemoryService:
    return request.app.state.memory_service


def get_database(request: Request) -> Database:
    if hasattr(request.app.state, "database") and request.app.state.database is not None:
        return request.app.state.database
    db_path = getattr(settings, "db_path", DEFAULT_DB_PATH)
    return Database(db_path)


def get_assessment_service() -> AssessmentService:
    return AssessmentService()


def get_groq_explanation_service() -> GroqExplanationService:
    return GroqExplanationService()


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount(
    "/assets",
    StaticFiles(directory=FRONTEND_DIR),
    name="frontend-assets",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Return basic application health information."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


def _idempotency_is_stale(row) -> bool:
    if row["status"] != "PROCESSING":
        return False
    started_at = row["processing_started_at"]
    if not started_at:
        return True
    try:
        started = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
    except ValueError:
        return True
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - started >= timedelta(seconds=IDEMPOTENCY_LEASE_SECONDS)


def _failed_response(report_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "failed",
            "error": "failed",
            "message": "Report persistence failed before any memory was recorded.",
            "report_id": report_id,
            "stages": {
                "vehicle_memory": "failed",
                "source_memory": "pending",
                "resolution": "pending",
            },
            "detail": {
                "status": "failed",
                "error": "failed",
                "message": "Report persistence failed before any memory was recorded.",
                "report_id": report_id,
                "stages": {
                    "vehicle_memory": "failed",
                    "source_memory": "pending",
                    "resolution": "pending",
                },
            },
        },
    )


def _partial_response(
    report_id: str, message: str, stages: dict[str, str]
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "partial",
            "error": "partial",
            "message": message,
            "report_id": report_id,
            "stages": stages,
            "detail": {
                "status": "partial",
                "error": "partial",
                "message": message,
                "report_id": report_id,
                "stages": stages,
            },
        },
    )


@app.post("/api/reports", status_code=status.HTTP_201_CREATED)
async def create_report(
    request: ReportSubmission,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    memory_service: MemoryService = Depends(get_memory_service),
    db: Database = Depends(get_database),
) -> JSONResponse:
    """Validate and persist one vehicle history report."""
    if idempotency_key is not None and not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Idempotency-Key must not be blank.",
        )

    payload_json = request.model_dump_json()
    request_fingerprint = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    report_id = generate_report_id(
        idempotency_key=idempotency_key,
        request_fingerprint=(payload_json if idempotency_key else None),
    )

    existing = None
    if idempotency_key is not None:
        existing = db.get_idempotency_record(idempotency_key=idempotency_key)
        if existing is not None:
            if existing["request_fingerprint"] != request_fingerprint:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key conflicts with a different request payload.",
                )

            if existing["status"] == "COMPLETED" and existing["response_payload"]:
                return JSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content=json.loads(existing["response_payload"]),
                )

            if existing["status"] == "PROCESSING" and not _idempotency_is_stale(existing):
                start_time = asyncio.get_event_loop().time()
                while asyncio.get_event_loop().time() - start_time < IDEMPOTENCY_POLL_SECONDS:
                    await asyncio.sleep(0.05)
                    poll_row = db.get_idempotency_record(idempotency_key=idempotency_key)
                    if poll_row and poll_row["status"] != "PROCESSING":
                        existing = poll_row
                        break
                else:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="A request with this idempotency key is currently being processed.",
                    )

                if existing["status"] == "COMPLETED" and existing["response_payload"]:
                    return JSONResponse(
                        status_code=status.HTTP_201_CREATED,
                        content=json.loads(existing["response_payload"]),
                    )
            if existing["status"] == "PROCESSING" and _idempotency_is_stale(existing):
                db.reclaim_stale_idempotency_record(
                    idempotency_key=idempotency_key,
                    request_fingerprint=request_fingerprint,
                    processing_started_at=datetime.now(timezone.utc).isoformat(),
                )
                existing = db.get_idempotency_record(idempotency_key=idempotency_key)
        else:
            inserted = db.create_idempotency_record(
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                report_id=report_id,
                status="PROCESSING",
                processing_started_at=datetime.now(timezone.utc).isoformat(),
            )
            if not inserted:
                existing = db.get_idempotency_record(idempotency_key=idempotency_key)
                if existing is not None:
                    if existing["request_fingerprint"] != request_fingerprint:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Idempotency key conflicts with a different request payload.",
                        )
                    if existing["status"] == "COMPLETED" and existing["response_payload"]:
                        return JSONResponse(
                            status_code=status.HTTP_201_CREATED,
                            content=json.loads(existing["response_payload"]),
                        )
                    start_time = asyncio.get_event_loop().time()
                    while asyncio.get_event_loop().time() - start_time < IDEMPOTENCY_POLL_SECONDS:
                        await asyncio.sleep(0.05)
                        poll_row = db.get_idempotency_record(idempotency_key=idempotency_key)
                        if poll_row and poll_row["status"] != "PROCESSING":
                            existing = poll_row
                            break
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="A request with this idempotency key is currently being processed.",
                        )

                    if existing["status"] == "COMPLETED" and existing["response_payload"]:
                        return JSONResponse(
                            status_code=status.HTTP_201_CREATED,
                            content=json.loads(existing["response_payload"]),
                        )
    else:
        db.create_idempotency_record(
            idempotency_key=None,
            request_fingerprint=request_fingerprint,
            report_id=report_id,
            status="PROCESSING",
            processing_started_at=datetime.now(timezone.utc).isoformat(),
        )

    if existing is not None and existing["status"] in ("PARTIAL", "FAILED"):
        db.update_idempotency_record(
            report_id=report_id,
            status="PROCESSING",
            processing_started_at=datetime.now(timezone.utc).isoformat(),
        )

    vehicle_done = bool(existing and existing["vehicle_memory_status"] == "STORED")
    source_done = bool(existing and existing["source_memory_status"] == "STORED")
    resolution_done = bool(existing and existing["resolution_status"] == "STORED")

    submitted_at = datetime.now(timezone.utc)
    claim = build_claim(report_id, request.text)
    vehicle_report = to_vehicle_report(report_id, request, submitted_at, claim)

    # Stage 1: Retain vehicle memory
    if not vehicle_done:
        try:
            if hasattr(memory_service, "retain_vehicle_report"):
                await memory_service.retain_vehicle_report(vehicle_report)
                vehicle_done = True
                db.update_idempotency_record(
                    report_id=report_id,
                    vehicle_memory_status="STORED",
                )
            else:
                await memory_service.retain_report(vehicle_report)
                vehicle_done = True
                source_done = True
                db.update_idempotency_record(
                    report_id=report_id,
                    vehicle_memory_status="STORED",
                    source_memory_status="STORED",
                )
        except Exception as exc:
            logger.error("Report persistence failed stage=vehicle error_type=%s", type(exc).__name__)
            db.update_idempotency_record(
                report_id=report_id,
                status="FAILED",
                vehicle_memory_status="FAILED",
                error_message="Report persistence failed before any memory was recorded.",
            )
            return _failed_response(report_id)

    # Stage 2: Retain source memory
    if not source_done:
        try:
            if hasattr(memory_service, "retain_source_report"):
                await memory_service.retain_source_report(vehicle_report)
            source_done = True
            db.update_idempotency_record(
                report_id=report_id,
                source_memory_status="STORED",
            )
        except Exception as exc:
            logger.error("Report persistence failed stage=source error_type=%s", type(exc).__name__)
            db.update_idempotency_record(
                report_id=report_id,
                status="PARTIAL",
                source_memory_status="FAILED",
                error_message="Vehicle memory stored, but source persistence failed.",
            )
            return _partial_response(
                report_id,
                message="Vehicle memory stored, but source persistence failed.",
                stages={
                    "vehicle_memory": "stored",
                    "source_memory": "failed",
                    "resolution": "pending",
                },
            )

    # Stage 3: Resolve source outcomes
    if not resolution_done:
        try:
            await memory_service.resolve_source_outcomes(vehicle_report)
            resolution_done = True
            db.update_idempotency_record(
                report_id=report_id,
                resolution_status="STORED",
            )
        except Exception as exc:
            logger.error("Report persistence failed stage=resolution error_type=%s", type(exc).__name__)
            db.update_idempotency_record(
                report_id=report_id,
                status="PARTIAL",
                resolution_status="FAILED",
                error_message="Report memory stored, but source outcome resolution failed.",
            )
            return _partial_response(
                report_id,
                message="Report memory stored, but source outcome resolution failed.",
                stages={
                    "vehicle_memory": "stored",
                    "source_memory": "stored",
                    "resolution": "failed",
                },
            )

    response_payload = {
        "report": {
            "report_id": report_id,
            "vehicle_id": request.vehicle_id,
            "vin": request.vin,
            "source_id": request.source_id,
            "source_type": request.source_type,
            "observed_at": request.observed_at.isoformat(),
            "submitted_at": submitted_at.isoformat(),
            "status": "active",
        },
        "claim": claim.model_dump(),
        "memory": {
            "vehicle_memory": "stored",
            "source_memory": "stored",
        },
        "status": "complete",
    }

    db.update_idempotency_record(
        report_id=report_id,
        status="COMPLETED",
        vehicle_memory_status="STORED",
        source_memory_status="STORED",
        resolution_status="STORED",
        response_payload=json.dumps(response_payload),
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=response_payload,
    )


def _assessment_payload(vehicle_id: str, assessment, memory_status: str) -> dict:
    return {
        "vehicle_id": vehicle_id,
        "memory_status": memory_status,
        "findings": [
            {
                "issue": assessment.issue_key,
                "status": assessment.state,
                "evidence_confidence": assessment.confidence,
                "supporting_sources": assessment.independent_supporting_sources,
                "contradicting_sources": assessment.independent_contradicting_sources,
                "support_weight": assessment.support_weight,
                "contradiction_weight": assessment.contradiction_weight,
                "supporting_evidence": [item.__dict__ for item in assessment.supporting_evidence],
                "contradicting_evidence": [item.__dict__ for item in assessment.contradicting_evidence],
                "unresolved_evidence": [item.__dict__ for item in assessment.unresolved_evidence],
            }
        ],
    }


async def _get_assessment(
    *,
    vehicle_id: str,
    issue: str,
    memory_service: MemoryService,
    assessment_service: AssessmentService,
):
    try:
        return await assessment_service.assess_vehicle(
            vehicle_id=vehicle_id,
            issue_key=issue,
            memory_service=memory_service,
        )
    except Exception as exc:
        logger.error("Assessment retrieval failed stage=memory error_type=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "MEMORY_UNAVAILABLE",
                    "message": "Historical memory is temporarily unavailable.",
                }
            },
        ) from exc


@app.get("/api/vehicles/{vehicle_id}/assessment")
async def get_vehicle_assessment(
    vehicle_id: str,
    issue: str = "transmission_shift_behavior",
    memory_service: MemoryService = Depends(get_memory_service),
    assessment_service: AssessmentService = Depends(get_assessment_service),
) -> dict:
    """Return the current deterministic assessment for one vehicle finding."""
    assessment, memory_status = await _get_assessment(
        vehicle_id=vehicle_id,
        issue=issue,
        memory_service=memory_service,
        assessment_service=assessment_service,
    )
    return _assessment_payload(vehicle_id, assessment, memory_status)


@app.get("/api/vehicles/{vehicle_id}/assessment/explanation")
async def get_vehicle_assessment_explanation(
    vehicle_id: str,
    issue: str = "transmission_shift_behavior",
    memory_service: MemoryService = Depends(get_memory_service),
    assessment_service: AssessmentService = Depends(get_assessment_service),
    explanation_service: GroqExplanationService = Depends(get_groq_explanation_service),
) -> dict:
    """Return a deterministic assessment plus an optional LLM explanation."""
    assessment, memory_status = await _get_assessment(
        vehicle_id=vehicle_id,
        issue=issue,
        memory_service=memory_service,
        assessment_service=assessment_service,
    )

    if memory_status == "empty":
        return {
            **_assessment_payload(vehicle_id, assessment, memory_status),
            "explanation_status": "unavailable",
            "explanation": None,
        }

    try:
        explanation = await explanation_service.explain(assessment)
    except Exception as exc:
        logger.error("Assessment explanation failed stage=groq error_type=%s", type(exc).__name__)
        return {
            **_assessment_payload(vehicle_id, assessment, memory_status),
            "explanation_status": "unavailable",
            "explanation": None,
        }

    return {
        **_assessment_payload(vehicle_id, assessment, memory_status),
        "explanation_status": "available",
        "explanation": explanation.model_dump(),
    }
