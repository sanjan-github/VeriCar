from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
from logging import getLogger
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.models.report import (
    Claim,
    ReportSubmission,
    build_claim,
    generate_report_id,
)
from backend.app.models.memory import VehicleReport
from backend.app.services.hindsight_factory import create_hindsight_repository
from backend.app.services.memory_service import MemoryService
from backend.app.services.assessment_service import AssessmentService
from backend.app.services.groq_explanation_service import GroqExplanationService
from backend.app.services.pdf_report_service import PdfReportService
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


def get_pdf_report_service(
    db: Database = Depends(get_database),
) -> PdfReportService:
    return PdfReportService(db)


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


@app.get("/readiness")
async def readiness(
    db: Database = Depends(get_database),
    memory_service: MemoryService = Depends(get_memory_service),
) -> JSONResponse:
    """Return dependency readiness for the application."""
    checks: dict[str, str] = {}
    is_ready = True

    # 1. Required: Durable SQLite persistence
    try:
        with db._connect() as conn:
            conn.execute("SELECT 1").fetchone()
        checks["database"] = "available"
    except Exception:
        checks["database"] = "unavailable"
        is_ready = False

    # 2. Optional: Hindsight memory service
    if not settings.hindsight_base_url:
        checks["hindsight"] = "unconfigured"
    else:
        try:
            await memory_service.check_version()
            checks["hindsight"] = "available"
        except Exception:
            checks["hindsight"] = "unavailable"

    # 3. Optional: Groq explanation service
    if settings.groq_api_key:
        checks["groq"] = "configured"
    else:
        checks["groq"] = "unconfigured"

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "unready",
            "service": settings.app_name,
            "environment": settings.app_env,
            "checks": checks,
        },
    )


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
    message = "Report saved locally, but external memory processing did not complete. Retry to reconcile memory storage."
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "failed",
            "error": "failed",
            "message": message,
            "report_id": report_id,
            "stages": {
                "vehicle_memory": "failed",
                "source_memory": "pending",
                "resolution": "pending",
            },
            "detail": {
                "status": "failed",
                "error": "failed",
                "message": message,
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


def _stored_vehicle_report(row) -> tuple[VehicleReport, Claim]:
    """Recreate the exact accepted API report for safe retry after a restart."""
    claim = Claim(
        claim_id=row["claim_id"],
        report_id=row["report_id"],
        text=row["report_text"],
        issue_candidate=row["issue_candidate"],
        polarity=row["polarity"],
    )
    observed_at = datetime.fromisoformat(row["observed_at"]).replace(tzinfo=timezone.utc)
    submitted_at = datetime.fromisoformat(row["submitted_at"].replace("Z", "+00:00"))
    if submitted_at.tzinfo is None:
        submitted_at = submitted_at.replace(tzinfo=timezone.utc)
    return (
        VehicleReport(
            report_id=row["report_id"],
            vin=row["vin"],
            source_id=row["source_id"],
            source_type=row["source_type"],
            text=row["report_text"],
            observed_at=observed_at,
            vehicle_id=row["vehicle_id"],
            submitted_at=submitted_at,
            issue_candidate=row["issue_candidate"],
            polarity=row["polarity"],
        ),
        claim,
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
    claim = build_claim(report_id, request.text)
    submitted_at = datetime.now(timezone.utc)
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
                reclaimed = db.reclaim_stale_idempotency_record(
                    idempotency_key=idempotency_key,
                    request_fingerprint=request_fingerprint,
                    expected_processing_started_at=existing["processing_started_at"],
                    processing_started_at=datetime.now(timezone.utc).isoformat(),
                )
                if not reclaimed:
                    existing = db.get_idempotency_record(idempotency_key=idempotency_key)
                    if existing is None or existing["status"] == "PROCESSING":
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="A request with this idempotency key is currently being processed.",
                        )
                else:
                    existing = db.get_idempotency_record(idempotency_key=idempotency_key)
        else:
            inserted = db.create_api_report_with_idempotency(
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                report_id=report_id,
                vehicle_id=request.vehicle_id,
                vin=request.vin,
                source_id=request.source_id,
                source_type=request.source_type,
                observed_at=request.observed_at.isoformat(),
                report_text=request.text,
                claim_id=claim.claim_id,
                issue_candidate=claim.issue_candidate,
                polarity=claim.polarity,
                submitted_at=submitted_at.isoformat(),
                processing_started_at=datetime.now(timezone.utc).isoformat(),
            )
            if not inserted:
                existing = db.get_idempotency_record(idempotency_key=idempotency_key)
                if existing is None:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Report persistence could not be initialized.",
                    )
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
        inserted = db.create_api_report_with_idempotency(
            idempotency_key=None,
            request_fingerprint=request_fingerprint,
            report_id=report_id,
            vehicle_id=request.vehicle_id,
            vin=request.vin,
            source_id=request.source_id,
            source_type=request.source_type,
            observed_at=request.observed_at.isoformat(),
            report_text=request.text,
            claim_id=claim.claim_id,
            issue_candidate=claim.issue_candidate,
            polarity=claim.polarity,
            submitted_at=submitted_at.isoformat(),
            processing_started_at=datetime.now(timezone.utc).isoformat(),
        )
        if not inserted:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Report persistence could not be initialized.",
            )

    if existing is not None and idempotency_key is not None and existing["status"] in ("PARTIAL", "FAILED"):
        claimed = db.claim_idempotency_retry(
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            expected_status=existing["status"],
            processing_started_at=datetime.now(timezone.utc).isoformat(),
        )
        if not claimed:
            latest = db.get_idempotency_record(idempotency_key=idempotency_key)
            if latest is not None and latest["status"] == "COMPLETED" and latest["response_payload"]:
                return JSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content=json.loads(latest["response_payload"]),
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A request with this idempotency key is currently being processed.",
            )
        existing = db.get_idempotency_record(idempotency_key=idempotency_key)

    vehicle_done = bool(existing and existing["vehicle_memory_status"] == "STORED")
    source_done = bool(existing and existing["source_memory_status"] == "STORED")
    resolution_done = bool(existing and existing["resolution_status"] == "STORED")

    stored_report = db.get_api_report(report_id)
    if stored_report is None:
        restored = db.create_api_report_for_existing_idempotency(
            request_fingerprint=request_fingerprint,
            report_id=report_id,
            vehicle_id=request.vehicle_id,
            vin=request.vin,
            source_id=request.source_id,
            source_type=request.source_type,
            observed_at=request.observed_at.isoformat(),
            report_text=request.text,
            claim_id=claim.claim_id,
            issue_candidate=claim.issue_candidate,
            polarity=claim.polarity,
            submitted_at=submitted_at.isoformat(),
        )
        stored_report = db.get_api_report(report_id)
        if not restored and stored_report is None:
            logger.error("Report persistence state is incomplete report_id=%s", report_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Report persistence could not be recovered.",
            )
    vehicle_report, claim = _stored_vehicle_report(stored_report)
    submitted_at = vehicle_report.submitted_at
    if submitted_at is None:
        logger.error("Stored API report is missing submitted_at report_id=%s", report_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stored report persistence is incomplete.",
        )

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
                error_message="Report saved locally, but external memory processing did not complete. Retry to reconcile memory storage.",
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
            "vehicle_id": vehicle_report.vehicle_id,
            "vin": vehicle_report.vin,
            "source_id": vehicle_report.source_id,
            "source_type": vehicle_report.source_type,
            "observed_at": vehicle_report.observed_at.date().isoformat(),
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


@app.get("/api/vehicles/{vehicle_id}")
async def get_vehicle_history(
    vehicle_id: str,
    db: Database = Depends(get_database),
) -> dict:
    """Return the durable vehicle record and chronological accepted report history."""
    vehicle = db.get_car(vehicle_id)
    reports = db.list_api_reports(vehicle_id)

    if vehicle is None and not reports:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "VEHICLE_NOT_FOUND",
                    "message": "Vehicle history was not found.",
                }
            },
        )

    vehicle_payload = dict(vehicle) if vehicle is not None else None
    report_payload = [
        {
            "report_id": row["report_id"],
            "vehicle_id": row["vehicle_id"],
            "vin": row["vin"],
            "source_id": row["source_id"],
            "source_type": row["source_type"],
            "observed_at": row["observed_at"],
            "submitted_at": row["submitted_at"],
            "text": row["report_text"],
            "claim": {
                "claim_id": row["claim_id"],
                "issue_candidate": row["issue_candidate"],
                "polarity": row["polarity"],
            },
        }
        for row in reports
    ]

    return {
        "vehicle_id": vehicle_id,
        "vehicle": vehicle_payload,
        "reports": report_payload,
        "report_count": len(report_payload),
        "history_status": "available" if report_payload else "empty",
    }


@app.get("/api/vehicles/{vehicle_id}/assessment")
async def get_vehicle_assessment(
    vehicle_id: str,
    issue: str = "transmission_shift_behavior",
    memory_service: MemoryService = Depends(get_memory_service),
    assessment_service: AssessmentService = Depends(get_assessment_service),
    db: Database = Depends(get_database),
) -> dict:
    """Return the current deterministic assessment for one vehicle finding."""
    vehicle = db.get_car(vehicle_id)
    reports = db.list_api_reports(vehicle_id)

    if vehicle is None and not reports:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "VEHICLE_NOT_FOUND",
                    "message": "Vehicle history was not found.",
                }
            },
        )

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
    db: Database = Depends(get_database),
) -> dict:
    """Return a deterministic assessment plus an optional LLM explanation."""
    vehicle = db.get_car(vehicle_id)
    reports = db.list_api_reports(vehicle_id)

    if vehicle is None and not reports:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "VEHICLE_NOT_FOUND",
                    "message": "Vehicle history was not found.",
                }
            },
        )

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


@app.get("/api/vehicles/{vehicle_id}/assessment/report.pdf")
async def download_vehicle_assessment_pdf(
    vehicle_id: str,
    db: Database = Depends(get_database),
    pdf_service: PdfReportService = Depends(get_pdf_report_service),
) -> Response:
    """Return the deterministic assessment PDF for a durably stored vehicle."""
    vehicle = db.get_car(vehicle_id)
    reports = db.list_api_reports(vehicle_id)

    if vehicle is None and not reports:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "VEHICLE_NOT_FOUND",
                    "message": "Vehicle history was not found.",
                }
            },
        )

    condition = db.get_condition(vehicle_id)
    if condition is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "CONDITION_NOT_AVAILABLE",
                    "message": "A saved condition record is required to generate the inspection report.",
                }
            },
        )

    try:
        pdf = pdf_service.build_vehicle_report(vehicle_id=vehicle_id)
    except LookupError as exc:
        logger.info(
            "PDF report unavailable vehicle_id=%s reason=%s",
            vehicle_id,
            str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "REPORT_NOT_READY",
                    "message": str(exc),
                }
            },
        ) from exc
    except ValueError as exc:
        logger.error(
            "PDF report generation failed vehicle_id=%s error_type=%s",
            vehicle_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "PDF_GENERATION_FAILED",
                    "message": "The inspection report could not be generated.",
                }
            },
        ) from exc
    except Exception as exc:
        logger.error(
            "PDF report generation failed vehicle_id=%s error_type=%s",
            vehicle_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "PDF_GENERATION_FAILED",
                    "message": "The inspection report could not be generated.",
                }
            },
        ) from exc

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="vericar-assessment-{vehicle_id}.pdf"'
            )
        },
    )
