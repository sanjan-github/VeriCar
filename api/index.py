"""Vercel entrypoint for the canonical VeriCar FastAPI application.

The application itself remains in backend.app.main so local development and the Vercel deployment use the same FastAPI instance and route definitions.
"""

from backend.app.main import app

__all__ = ["app"]
