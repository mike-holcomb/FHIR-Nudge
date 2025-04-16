import pytest
from fhir_nudge.client import FhirNudgeClient
import requests

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code
    def json(self):
        return self._json
    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_read_resource_success(mocker):
    client = FhirNudgeClient("http://localhost:8888")
    mocker.patch(
        "requests.get",
        return_value=MockResponse({"resourceType": "Patient", "id": "123"}, 200)
    )
    result = client.read_resource("Patient", "123")
    assert result["resourceType"] == "Patient"
    assert result["id"] == "123"


def test_read_resource_http_error(mocker):
    client = FhirNudgeClient("http://localhost:8888")
    mocker.patch(
        "requests.get",
        return_value=MockResponse({"error": "not found"}, 404)
    )
    with pytest.raises(requests.HTTPError):
        client.read_resource("Patient", "doesnotexist")
