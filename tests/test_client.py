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


def test_search_resource_success(mocker):
    client = FhirNudgeClient("http://localhost:8888")
    mock_bundle = {
        "resourceType": "Bundle",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "abc"}},
            {"resource": {"resourceType": "Patient", "id": "def"}},
        ]
    }
    mocker.patch(
        "requests.get",
        return_value=MockResponse(mock_bundle, 200)
    )
    params = {"name": "Smith"}
    result = client.search_resource("Patient", params)
    assert result["resourceType"] == "Bundle"
    assert len(result["entry"]) == 2
    assert result["entry"][0]["resource"]["id"] == "abc"


def test_search_resource_http_error(mocker):
    client = FhirNudgeClient("http://localhost:8888")
    mock_error = {"error": "Invalid param", "status_code": 400}
    mocker.patch(
        "requests.get",
        return_value=MockResponse(mock_error, 400)
    )
    with pytest.raises(requests.HTTPError):
        client.search_resource("Patient", {"nme": "John"})
