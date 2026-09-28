from contextlib import asynccontextmanager
from logging import getLogger

from fastapi import FastAPI

from backend.app.config import settings
from backend.app.services.hindsight_factory import create_hindsight_repository
from backend.app.services.memory_service import MemoryService


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


@app.get("/health")
def health() -> dict[str, str]:
    """Return basic application health information."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }
