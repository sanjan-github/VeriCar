from fastapi import FastAPI

from backend.app.config import settings


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Return basic application health information."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }
