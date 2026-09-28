from __future__ import annotations

import sqlite3
from pathlib import Path

from core.models import Car


DEFAULT_DB_PATH = Path("data/vericar.db")


class Database:
    """Small SQLite persistence layer for structured vehicle data."""

    def __init__(self, path: str | Path = DEFAULT_DB_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

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
