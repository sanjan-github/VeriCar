from contextlib import asynccontextmanager
from datetime import datetime, timezone
from logging import getLogger

from fastapi import Depends, FastAPI, HTTPException, Request, status

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


logger = getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    repository = create_hindsight_repository()
    memory_service = MemoryService(repository)
    app.state.memory_service = memory_service

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


def get_assessment_service() -> AssessmentService:
    return AssessmentService()


@app.get("/health")
def health() -> dict[str, str]:
    """Return basic application health information."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


@app.post("/api/reports", status_code=status.HTTP_201_CREATED)
async def create_report(
    request: ReportSubmission,
    memory_service: MemoryService = Depends(get_memory_service),
) -> dict:
    """Validate and persist one vehicle history report."""
    report_id = generate_report_id()
    submitted_at = datetime.now(timezone.utc)
    claim = build_claim(report_id, request.text)
    vehicle_report = to_vehicle_report(report_id, request, submitted_at, claim)

    try:
        await memory_service.retain_report(vehicle_report)
    except Exception as exc:
        logger.exception("Failed to persist report %s to memory", report_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "partial_failure",
                "message": "Report validation succeeded, but memory persistence failed.",
                "report_id": report_id,
            },
        ) from exc

    return {
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
    }


@app.get("/api/vehicles/{vehicle_id}/assessment")
async def get_vehicle_assessment(
    vehicle_id: str,
    issue: str = "transmission_shift_behavior",
    memory_service: MemoryService = Depends(get_memory_service),
    assessment_service: AssessmentService = Depends(get_assessment_service),
) -> dict:
    """Return the current deterministic assessment for one vehicle finding."""
    try:
        assessment, memory_status = await assessment_service.assess_vehicle(
            vin=vehicle_id,
            issue_key=issue,
            memory_service=memory_service,
        )
    except Exception as exc:
        logger.exception("Failed to retrieve assessment for vehicle %s", vehicle_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "MEMORY_UNAVAILABLE",
                    "message": "Historical memory is temporarily unavailable.",
                }
            },
        ) from exc

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
