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
        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS report_idempotency (
                    idempotency_key TEXT UNIQUE,
                    request_fingerprint TEXT NOT NULL,
                    report_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    vehicle_memory_status TEXT NOT NULL DEFAULT 'PENDING',
                    source_memory_status TEXT NOT NULL DEFAULT 'PENDING',
                    resolution_status TEXT NOT NULL DEFAULT 'PENDING',
                    response_payload TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("limit must be a positive integer.")
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

    def get_idempotency_record(
        self,
        *,
        idempotency_key: str | None = None,
        report_id: str | None = None,
    ) -> sqlite3.Row | None:
        if idempotency_key is None and report_id is None:
            raise ValueError("Either idempotency_key or report_id must be provided.")
        with self._connect() as connection:
            if idempotency_key is not None:
                row = connection.execute(
                    "SELECT * FROM report_idempotency WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()
                if row is not None:
                    return row
            if report_id is not None:
                return connection.execute(
                    "SELECT * FROM report_idempotency WHERE report_id = ?",
                    (report_id,),
                ).fetchone()
            return None

    def create_idempotency_record(
        self,
        *,
        idempotency_key: str | None,
        request_fingerprint: str,
        report_id: str,
        status: str = "PROCESSING",
    ) -> bool:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO report_idempotency (
                        idempotency_key, request_fingerprint, report_id, status,
                        vehicle_memory_status, source_memory_status, resolution_status
                    ) VALUES (?, ?, ?, ?, 'PENDING', 'PENDING', 'PENDING')
                    """,
                    (idempotency_key, request_fingerprint, report_id, status),
                )
                return True
        except sqlite3.IntegrityError:
            return False

    def update_idempotency_record(
        self,
        report_id: str,
        *,
        status: str | None = None,
        vehicle_memory_status: str | None = None,
        source_memory_status: str | None = None,
        resolution_status: str | None = None,
        response_payload: str | None = None,
        error_message: str | None = None,
    ) -> None:
        fields = []
        params = []
        if status is not None:
            fields.append("status = ?")
            params.append(status)
        if vehicle_memory_status is not None:
            fields.append("vehicle_memory_status = ?")
            params.append(vehicle_memory_status)
        if source_memory_status is not None:
            fields.append("source_memory_status = ?")
            params.append(source_memory_status)
        if resolution_status is not None:
            fields.append("resolution_status = ?")
            params.append(resolution_status)
        if response_payload is not None:
            fields.append("response_payload = ?")
            params.append(response_payload)
        if error_message is not None:
            fields.append("error_message = ?")
            params.append(error_message)

        if not fields:
            return

        fields.append("updated_at = CURRENT_TIMESTAMP")
        query = f"UPDATE report_idempotency SET {', '.join(fields)} WHERE report_id = ?"
        params.append(report_id)

        with self._connect() as connection:
            connection.execute(query, params)

