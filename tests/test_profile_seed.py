from core.database import Database
from core.profile_seed import load_expected_profiles, seed_expected_profiles


def test_seed_file_contains_reference_profiles():
    profiles = load_expected_profiles()
    assert len(profiles) == 8
    assert all(profile.source == "synthetic_seed" for profile in profiles)


def test_seed_profiles_are_persisted(tmp_path):
    db = Database(tmp_path / "test.db")
    count = seed_expected_profiles(db)
    assert count == 8
    assert db.get_expected_profile("tata|nexon|2022|xz+|petrol|manual") is not None
    assert db.get_expected_profile("toyota|innova crysta|2019|gx|diesel|manual") is not None


def test_seed_is_idempotent(tmp_path):
    db = Database(tmp_path / "test.db")
    assert seed_expected_profiles(db) == 8
    assert seed_expected_profiles(db) == 8
    profile = db.get_expected_profile("honda|city|2021|unknown|petrol|cvt")
    assert profile is not None
