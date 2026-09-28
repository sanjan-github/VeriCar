from hindsight_client import Hindsight

from backend.app.config import settings
from backend.app.repositories.hindsight_repository import HindsightRepository


def create_hindsight_repository() -> HindsightRepository:
    client = Hindsight(
        base_url=settings.hindsight_base_url,
        api_key=settings.hindsight_api_key or None,
        timeout=settings.hindsight_timeout,
    )
    return HindsightRepository(client)
