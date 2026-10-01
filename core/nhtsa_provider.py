from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Protocol

import httpx

from core.data_source import DataSource, ProviderResult
from core.models import Car


NHTSA_RECALL_SOURCE = DataSource(
    source_id="nhtsa_recalls",
    name="NHTSA Recalls API",
    kind="government",
    url="https://api.nhtsa.gov/recalls/",
    description="U.S. National Highway Traffic Safety Administration recall information API.",
)

NHTSA_VPIC_SOURCE = DataSource(
    source_id="nhtsa_vpic",
    name="NHTSA vPIC",
    kind="government",
    url="https://vpic.nhtsa.dot.gov/api/",
    description="U.S. National Highway Traffic Safety Administration Vehicle Product Information Catalog API.",
)


class HttpClient(Protocol):
    def get(self, url: str, *, params: dict[str, str], timeout: float) -> Any:
        ...


@dataclass(frozen=True)
class NHTSAVinProvider:
    """Decode VIN data through the official NHTSA vPIC API.

    The provider returns raw structured fields from the government endpoint.
    It does not turn VIN decoding into a reliability verdict or invent missing
    vehicle-history facts.
    """

    base_url: str = "https://vpic.nhtsa.dot.gov/api/vehicles/decodevinvaluesextended"
    timeout_seconds: float = 10.0
    retries: int = 2
    client: HttpClient | None = None
    source: DataSource = NHTSA_VPIC_SOURCE

    def get_vehicle(self, car: Car) -> ProviderResult:
        vin = (car.vin or "").strip().upper()
        if not vin:
            return ProviderResult(
                status="NOT_FOUND",
                source=self.source,
                message="No VIN was supplied for NHTSA lookup.",
            )

        if len(vin) != 17:
            return ProviderResult(
                status="ERROR",
                source=self.source,
                message="VIN must contain exactly 17 characters for this lookup.",
            )

        url = f"{self.base_url}/{vin}"
        client = self.client or httpx.Client()

        try:
            response = None
            last_error: Exception | None = None
            for attempt in range(self.retries + 1):
                try:
                    response = client.get(
                        url,
                        params={"format": "json"},
                        timeout=self.timeout_seconds,
                    )
                    response.raise_for_status()
                    break
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    last_error = exc
                    if attempt >= self.retries:
                        return ProviderResult(
                            status="UNAVAILABLE",
                            source=self.source,
                            message=f"NHTSA request unavailable after retries: {exc}",
                        )
                    time.sleep(0.2 * (2**attempt))

            if response is None:
                return ProviderResult(
                    status="UNAVAILABLE",
                    source=self.source,
                    message=f"NHTSA request unavailable: {last_error}",
                )

            payload = response.json()
            results = payload.get("Results") if isinstance(payload, dict) else None
            if not isinstance(results, list) or not results:
                return ProviderResult(
                    status="NOT_FOUND",
                    source=self.source,
                    message="NHTSA returned no VIN result.",
                )

            result = results[0]
            if not isinstance(result, dict):
                return ProviderResult(
                    status="ERROR",
                    source=self.source,
                    message="NHTSA returned an invalid VIN result.",
                )

            error_code = str(result.get("ErrorCode") or "").strip()
            error_text = str(result.get("ErrorText") or "").strip()
            if error_code and error_code not in {"0", "10"}:
                return ProviderResult(
                    status="NOT_FOUND",
                    source=self.source,
                    message=error_text or f"NHTSA reported ErrorCode {error_code}.",
                )

            data = {
                key: value
                for key, value in result.items()
                if value not in (None, "")
            }
            if not data:
                return ProviderResult(
                    status="NOT_FOUND",
                    source=self.source,
                    message="NHTSA returned an empty VIN result.",
                )

            return ProviderResult(
                status="FOUND",
                source=self.source,
                data=data,
                source_reliability="high",
                evidence_confidence="high",
                evidence_scope="vehicle",
            )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            return ProviderResult(
                status="ERROR",
                source=self.source,
                message=f"NHTSA response processing failed: {exc}",
            )
        finally:
            if self.client is None:
                client.close()


@dataclass(frozen=True)
class NHTSARecallProvider:
    """Retrieve model/year recall information from the NHTSA public API.

    Recall results are model/year evidence, not proof that a particular VIN
    received or did not receive the remedy.
    """

    base_url: str = "https://api.nhtsa.gov/recalls/recallsByVehicle"
    timeout_seconds: float = 10.0
    retries: int = 2
    client: HttpClient | None = None
    source: DataSource = NHTSA_RECALL_SOURCE

    def get_recalls(self, car: Car) -> ProviderResult:
        make = (car.brand or "").strip()
        model = (car.model or "").strip()
        if not make or not model or not car.manufacture_year:
            return ProviderResult(
                status="ERROR",
                source=self.source,
                message="Make, model, and model year are required for recall lookup.",
                source_reliability="high",
                evidence_scope="model",
            )

        client = self.client or httpx.Client()
        params = {
            "make": make,
            "model": model,
            "modelYear": str(car.manufacture_year),
        }
        try:
            response = None
            last_error: Exception | None = None
            for attempt in range(self.retries + 1):
                try:
                    response = client.get(
                        self.base_url,
                        params=params,
                        timeout=self.timeout_seconds,
                    )
                    response.raise_for_status()
                    break
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    last_error = exc
                    if attempt >= self.retries:
                        return ProviderResult(
                            status="UNAVAILABLE",
                            source=self.source,
                            message=f"NHTSA recall request unavailable after retries: {exc}",
                            source_reliability="high",
                            evidence_scope="model",
                        )
                    time.sleep(0.2 * (2**attempt))

            if response is None:
                return ProviderResult(
                    status="UNAVAILABLE",
                    source=self.source,
                    message=f"NHTSA recall request unavailable: {last_error}",
                    source_reliability="high",
                    evidence_scope="model",
                )

            payload = response.json()
            results = payload.get("results") if isinstance(payload, dict) else None
            if results is None and isinstance(payload, dict):
                results = payload.get("Results")
            if not isinstance(results, list):
                return ProviderResult(
                    status="ERROR",
                    source=self.source,
                    message="NHTSA returned an invalid recall response.",
                    source_reliability="high",
                    evidence_scope="model",
                )

            if not results:
                return ProviderResult(
                    status="NOT_FOUND",
                    source=self.source,
                    message="NHTSA returned no matching recall information for this make/model/year query.",
                    source_reliability="high",
                    evidence_scope="model",
                )

            normalized = [item for item in results if isinstance(item, dict)]
            if not normalized:
                return ProviderResult(
                    status="NOT_FOUND",
                    source=self.source,
                    message="NHTSA returned no usable recall records.",
                    source_reliability="high",
                    evidence_scope="model",
                )

            return ProviderResult(
                status="FOUND",
                source=self.source,
                data={
                    "make": make,
                    "model": model,
                    "model_year": car.manufacture_year,
                    "recalls": normalized,
                },
                source_reliability="high",
                evidence_confidence="high",
                evidence_scope="model",
            )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            return ProviderResult(
                status="ERROR",
                source=self.source,
                message=f"NHTSA recall response processing failed: {exc}",
                source_reliability="high",
                evidence_scope="model",
            )
        finally:
            if self.client is None:
                client.close()
