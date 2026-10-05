from __future__ import annotations

from datetime import date
from io import BytesIO

from core.assessment_pipeline import run_assessment
from core.condition import ConditionRecord
from core.database import Database
from core.models import Car
from core.pdf_report import build_assessment_pdf


class PdfReportService:
    """Build the same deterministic PDF report used by the Streamlit workflow."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def build_vehicle_report(
        self,
        *,
        vehicle_id: str,
        today: date | None = None,
    ) -> bytes:
        row = self._db.get_car(vehicle_id)
        if row is None:
            raise LookupError(f"Vehicle {vehicle_id!r} was not found.")

        car = Car(
            car_id=row["car_id"],
            brand=row["brand"],
            model=row["model"],
            manufacture_year=row["manufacture_year"],
            variant=row["variant"],
            fuel_type=row["fuel_type"],
            transmission=row["transmission"],
            manufacture_month=row["manufacture_month"],
            registration_date=self._parse_date(row["registration_date"]),
            purchase_date=self._parse_date(row["purchase_date"]),
            vin=row["vin"],
            registration_state=row["registration_state"],
            previous_owners=row["previous_owners"],
            odometer_km=row["odometer_km"],
            asking_price_inr=row["asking_price_inr"],
        )
        condition = self._db.get_condition(vehicle_id)
        if condition is None:
            raise LookupError(
                f"Vehicle {vehicle_id!r} does not have a saved condition record."
            )

        result = run_assessment(
            car,
            condition,
            self._db,
            today=today,
            generate_explanation=False,
            history_items=None,
        )
        if result.assessment is None or result.profile_resolution.profile is None:
            raise LookupError(
                f"Vehicle {vehicle_id!r} does not have enough local data "
                "for a completed assessment report."
            )

        return build_assessment_pdf(car, condition, result)

    @staticmethod
    def _parse_date(value: str | None):
        return date.fromisoformat(value) if value else None
