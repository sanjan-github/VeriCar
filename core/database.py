from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from core.condition import ConditionRecord
from core.models import Car


DEFAULT_DB_PATH = Path("data/vericar.db")


class Database:
    """SQLite persistence for structured vehicle and condition data."""

    def __init__(self, path: str | Path = DEFAULT_DB_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cars (
                    car_id TEXT PRIMARY KEY,
                    brand TEXT NOT NULL,
                    model TEXT NOT NULL,
                    manufacture_year INTEGER NOT NULL,
                    variant TEXT,
                    fuel_type TEXT,
                    transmission TEXT,
                    manufacture_month INTEGER,
                    registration_date TEXT,
                    purchase_date TEXT,
                    vin TEXT,
                    registration_state TEXT,
                    previous_owners INTEGER,
                    odometer_km INTEGER,
                    asking_price_inr INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS vehicle_conditions (
                    car_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(car_id) REFERENCES cars(car_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS expected_profiles (
                    profile_key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS vehicle_memory_reports (
                    report_id TEXT PRIMARY KEY,
                    car_id TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT,
                    synced_at TEXT,
                    FOREIGN KEY(car_id) REFERENCES cars(car_id)
                )
                """
            )

    def save_car(self, car: Car) -> None:
        record = car.to_record()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO cars (
                    car_id, brand, model, manufacture_year, variant, fuel_type,
                    transmission, manufacture_month, registration_date,
                    purchase_date, vin, registration_state, previous_owners,
                    odometer_km, asking_price_inr
                ) VALUES (
                    :car_id, :brand, :model, :manufacture_year, :variant, :fuel_type,
                    :transmission, :manufacture_month, :registration_date,
                    :purchase_date, :vin, :registration_state, :previous_owners,
                    :odometer_km, :asking_price_inr
                )
                ON CONFLICT(car_id) DO UPDATE SET
                    brand=excluded.brand,
                    model=excluded.model,
                    manufacture_year=excluded.manufacture_year,
                    variant=excluded.variant,
                    fuel_type=excluded.fuel_type,
                    transmission=excluded.transmission,
                    manufacture_month=excluded.manufacture_month,
                    registration_date=excluded.registration_date,
                    purchase_date=excluded.purchase_date,
                    vin=excluded.vin,
                    registration_state=excluded.registration_state,
                    previous_owners=excluded.previous_owners,
                    odometer_km=excluded.odometer_km,
                    asking_price_inr=excluded.asking_price_inr,
                    updated_at=CURRENT_TIMESTAMP
                """,
                record,
            )

    def get_car(self, car_id: str):
        with self._connect() as connection:
            return connection.execute(
                "SELECT * FROM cars WHERE car_id = ?", (car_id,)
            ).fetchone()

    def list_cars(self, limit: int = 20):
        with self._connect() as connection:
            return list(
                connection.execute(
                    "SELECT * FROM cars ORDER BY updated_at DESC LIMIT ?", (limit,)
                ).fetchall()
            )

    def save_condition(self, condition: ConditionRecord) -> None:
        payload = json.dumps(condition.to_record(), ensure_ascii=False)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO vehicle_conditions (car_id, payload)
                VALUES (?, ?)
                ON CONFLICT(car_id) DO UPDATE SET
                    payload=excluded.payload,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (condition.car_id, payload),
            )

    def record_memory_report(
        self, *, report_id: str, car_id: str, observed_at: str,
        status: str, error: str | None = None, synced_at: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO vehicle_memory_reports (report_id, car_id, observed_at, status, error, synced_at) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(report_id) DO UPDATE SET status=excluded.status, error=excluded.error, synced_at=excluded.synced_at",
                (report_id, car_id, observed_at, status, error, synced_at),
            )

    def get_memory_report(self, report_id: str):
        with self._connect() as connection:
            return connection.execute(
                "SELECT * FROM vehicle_memory_reports WHERE report_id = ?",
                (report_id,),
            ).fetchone()

    def get_condition(self, car_id: str) -> ConditionRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM vehicle_conditions WHERE car_id = ?",
                (car_id,),
            ).fetchone()
        if row is None:
            return None
        return ConditionRecord.from_record(json.loads(row["payload"]))

    def save_expected_profile(self, profile) -> None:
        payload = json.dumps(profile.to_record(), ensure_ascii=False)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO expected_profiles (profile_key, payload)
                VALUES (?, ?)
                ON CONFLICT(profile_key) DO UPDATE SET
                    payload=excluded.payload,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (profile.profile_key, payload),
            )

    def get_expected_profile(self, profile_key: str):
        from core.expected_profile import ExpectedProfile

        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM expected_profiles WHERE profile_key = ?",
                (profile_key,),
            ).fetchone()
        if row is None:
            return None
        return ExpectedProfile.from_record(json.loads(row["payload"]))
