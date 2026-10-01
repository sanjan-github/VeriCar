import httpx

from core.models import Car
from core.nhtsa_provider import NHTSAComplaintProvider, NHTSARecallProvider, NHTSAVinProvider


VIN = "1HGCM82633A004352"


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, responses=None, errors=None):
        self.responses = list(responses or [])
        self.errors = list(errors or [])
        self.calls = []

    def get(self, url, *, params, timeout):
        self.calls.append((url, params, timeout))
        if self.errors:
            raise self.errors.pop(0)
        return self.responses.pop(0)


def _car():
    return Car(
        car_id="CAR-1",
        brand="Honda",
        model="Accord",
        manufacture_year=2003,
        vin=VIN,
    )


def test_nhtsa_returns_decoded_fields_with_government_provenance():
    client = FakeClient(
        responses=[
            FakeResponse(
                {
                    "Results": [
                        {
                            "VIN": VIN,
                            "Make": "HONDA",
                            "Model": "Accord",
                            "ModelYear": "2003",
                            "ErrorCode": "0",
                            "ErrorText": "",
                        }
                    ]
                }
            )
        ]
    )
    result = NHTSAVinProvider(client=client).get_vehicle(_car())

    assert result.status == "FOUND"
    assert result.source.source_id == "nhtsa_vpic"
    assert result.source.kind == "government"
    assert result.data["VIN"] == VIN
    assert result.data["Make"] == "HONDA"
    assert client.calls[0][1] == {"format": "json"}


def test_nhtsa_returns_not_found_when_api_returns_no_results():
    client = FakeClient(
        responses=[FakeResponse({"Results": []})]
    )

    result = NHTSAVinProvider(client=client).get_vehicle(_car())

    assert result.status == "NOT_FOUND"
    assert result.data is None


def test_nhtsa_retries_network_failure_then_succeeds():
    client = FakeClient(
        errors=[httpx.ConnectError("offline")],
        responses=[
            FakeResponse(
                {"Results": [{"VIN": VIN, "Make": "HONDA", "ErrorCode": "0"}]}
            )
        ],
    )

    result = NHTSAVinProvider(client=client, retries=1).get_vehicle(_car())

    assert result.status == "FOUND"
    assert len(client.calls) == 2


def test_nhtsa_reports_unavailable_after_network_retries():
    client = FakeClient(
        errors=[
            httpx.ConnectError("offline"),
            httpx.ConnectError("still offline"),
        ]
    )

    result = NHTSAVinProvider(client=client, retries=1).get_vehicle(_car())

    assert result.status == "UNAVAILABLE"
    assert len(client.calls) == 2


def test_nhtsa_rejects_invalid_vin_without_network_call():
    client = FakeClient()
    car = Car(
        car_id="CAR-2",
        brand="Honda",
        model="Accord",
        manufacture_year=2003,
        vin="SHORT",
    )

    result = NHTSAVinProvider(client=client).get_vehicle(car)

    assert result.status == "ERROR"
    assert result.data is None
    assert client.calls == []


def test_nhtsa_does_not_query_without_vin():
    client = FakeClient()
    car = Car(
        car_id="CAR-3",
        brand="Honda",
        model="Accord",
        manufacture_year=2003,
    )

    result = NHTSAVinProvider(client=client).get_vehicle(car)

    assert result.status == "NOT_FOUND"
    assert client.calls == []


def test_nhtsa_recall_provider_returns_model_scoped_evidence():
    client = FakeClient(
        responses=[
            FakeResponse(
                {
                    "Count": 1,
                    "results": [
                        {
                            "NHTSACampaignNumber": "24V000000",
                            "Component": "SERVICE BRAKES",
                            "Summary": "Example recall",
                            "Remedy": "Example remedy",
                        }
                    ],
                }
            )
        ]
    )

    result = NHTSARecallProvider(client=client).get_recalls(_car())

    assert result.status == "FOUND"
    assert result.source.source_id == "nhtsa_recalls"
    assert result.source_reliability == "high"
    assert result.evidence_confidence == "high"
    assert result.evidence_scope == "model"
    assert result.data["model"] == "Accord"
    assert len(result.data["recalls"]) == 1
    assert client.calls[0][1] == {
        "make": "Honda",
        "model": "Accord",
        "modelYear": "2003",
    }


def test_nhtsa_recall_provider_distinguishes_no_data_from_unavailable():
    client = FakeClient(responses=[FakeResponse({"Count": 0, "results": []})])

    result = NHTSARecallProvider(client=client).get_recalls(_car())

    assert result.status == "NOT_FOUND"
    assert result.evidence_scope == "model"

    unavailable_client = FakeClient(errors=[httpx.ConnectError("offline")])
    result = NHTSARecallProvider(
        client=unavailable_client,
        retries=0,
    ).get_recalls(_car())

    assert result.status == "UNAVAILABLE"
    assert result.data is None


def test_nhtsa_recall_provider_requires_vehicle_identity():
    client = FakeClient()
    car = Car(car_id="CAR-4", brand="", model="", manufacture_year=2003)

    result = NHTSARecallProvider(client=client).get_recalls(car)

    assert result.status == "ERROR"
    assert result.evidence_scope == "model"
    assert client.calls == []


def test_nhtsa_complaint_provider_returns_model_scoped_evidence():
    client = FakeClient(
        responses=[
            FakeResponse(
                {
                    "Count": 1,
                    "results": [
                        {
                            "odiNumber": 123456,
                            "components": "BRAKES",
                            "summary": "Example complaint",
                        }
                    ],
                }
            )
        ]
    )

    result = NHTSAComplaintProvider(client=client).get_complaints(_car())

    assert result.status == "FOUND"
    assert result.source.source_id == "nhtsa_complaints"
    assert result.source_reliability == "high"
    assert result.evidence_confidence == "medium"
    assert result.evidence_scope == "model"
    assert result.data["model"] == "Accord"
    assert len(result.data["complaints"]) == 1
    assert client.calls[0][1] == {
        "make": "Honda",
        "model": "Accord",
        "modelYear": "2003",
    }


def test_nhtsa_complaint_provider_distinguishes_no_data_from_unavailable():
    client = FakeClient(responses=[FakeResponse({"Count": 0, "results": []})])

    result = NHTSAComplaintProvider(client=client).get_complaints(_car())

    assert result.status == "NOT_FOUND"
    assert result.evidence_scope == "model"

    unavailable_client = FakeClient(errors=[httpx.ConnectError("offline")])
    result = NHTSAComplaintProvider(
        client=unavailable_client,
        retries=0,
    ).get_complaints(_car())

    assert result.status == "UNAVAILABLE"
    assert result.data is None
