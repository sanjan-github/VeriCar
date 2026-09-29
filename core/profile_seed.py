from __future__ import annotations

import json
from pathlib import Path

from core.database import Database
from core.expected_profile import ExpectedProfile


DEFAULT_PROFILES_PATH = Path("data/expected_profiles.json")


def load_expected_profiles(path: str | Path = DEFAULT_PROFILES_PATH) -> list[ExpectedProfile]:
    """Load version-controlled reference profiles from JSON."""
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, list):
        raise ValueError("Expected profile data must be a JSON list")

    profiles = [ExpectedProfile.from_record(item) for item in payload]
    if not profiles:
        raise ValueError("Expected profile data must not be empty")
    return profiles


def seed_expected_profiles(
    db: Database, path: str | Path = DEFAULT_PROFILES_PATH
) -> int:
    """Upsert all reference profiles into SQLite and return the count."""
    profiles = load_expected_profiles(path)
    for profile in profiles:
        db.save_expected_profile(profile)
    return len(profiles)
