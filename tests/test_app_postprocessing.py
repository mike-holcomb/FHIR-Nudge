import pytest
from fhir_nudge.app import _enrich_search_resource_error

class DummyFHIRResponse:
    def __init__(self, status_code, json_data, text=None):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text or str(json_data)
    def json(self):
        return self._json_data

@pytest.fixture
def dummy_supported_param_schema(monkeypatch):
    schema = [
        {"name": "name", "type": "string", "documentation": "Patient name"},
        {"name": "gender", "type": "string", "documentation": "Gender of the patient"},
    ]
    monkeypatch.setattr("fhir_nudge.app.get_capability_index", lambda: {"Patient": schema})
    return schema

def test_invalid_param_value_enrichment(app, dummy_supported_param_schema):
    with app.app_context():
        resp = DummyFHIRResponse(
            400,
            {
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "error",
                        "code": "invalid",
                        "diagnostics": "Invalid value 'abc' for parameter 'gender'. Allowed: male, female, other, unknown.",
                        "details": {"text": "Parameter 'gender' must be one of: male, female, other, unknown."}
                    }
                ]
            }
        )
        flask_resp, status = _enrich_search_resource_error("Patient", resp)
        data = flask_resp.get_json()
        assert status == 400
        assert any("gender" in issue["diagnostics"] for issue in data["issues"])
        assert "supported_param_schema" in data
        assert any(p["name"] == "gender" for p in data["supported_param_schema"])

def test_unsupported_param_enrichment(app, dummy_supported_param_schema):
    with app.app_context():
        resp = DummyFHIRResponse(
            400,
            {
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "error",
                        "code": "not-supported",
                        "diagnostics": "Unsupported parameter 'foo'."
                    }
                ]
            }
        )
        flask_resp, status = _enrich_search_resource_error("Patient", resp)
        data = flask_resp.get_json()
        assert status == 400
        assert any("foo" in issue["diagnostics"] for issue in data["issues"])
        assert "supported_param_schema" in data
        assert "unsupported_params" in data and "foo" in data["unsupported_params"]

def test_malformed_request_enrichment(app, dummy_supported_param_schema):
    with app.app_context():
        resp = DummyFHIRResponse(
            400,
            {
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "error",
                        "code": "structure",
                        "diagnostics": "Malformed request: missing '=' in query string."
                    }
                ]
            }
        )
        flask_resp, status = _enrich_search_resource_error("Patient", resp)
        data = flask_resp.get_json()
        assert status == 400
        assert any("Malformed request" in issue["diagnostics"] or "missing '='" in issue["diagnostics"] for issue in data["issues"])
        assert "supported_param_schema" in data

def test_multiple_issues_enrichment(app, dummy_supported_param_schema):
    with app.app_context():
        resp = DummyFHIRResponse(
            400,
            {
                "resourceType": "OperationOutcome",
                "issue": [
                    {"severity": "error", "code": "invalid", "diagnostics": "Invalid value for 'gender'."},
                    {"severity": "error", "code": "not-supported", "diagnostics": "Unsupported parameter 'foo'."}
                ]
            }
        )
        flask_resp, status = _enrich_search_resource_error("Patient", resp)
        data = flask_resp.get_json()
        assert status == 400
        assert len(data["issues"]) == 2
        assert "supported_param_schema" in data

def test_405_422_enrichment(app, dummy_supported_param_schema):
    with app.app_context():
        # 405 Method Not Allowed
        resp_405 = DummyFHIRResponse(
            405,
            {
                "resourceType": "OperationOutcome",
                "issue": [
                    {"severity": "error", "code": "processing", "diagnostics": "Method not allowed."}
                ]
            }
        )
        flask_resp, status = _enrich_search_resource_error("Patient", resp_405)
        data = flask_resp.get_json()
        assert status == 405
        assert any("not allowed" in issue["diagnostics"] for issue in data["issues"])
        # 422 Unprocessable Entity
        resp_422 = DummyFHIRResponse(
            422,
            {
                "resourceType": "OperationOutcome",
                "issue": [
                    {"severity": "error", "code": "processing", "diagnostics": "Unprocessable entity."}
                ]
            }
        )
        flask_resp, status = _enrich_search_resource_error("Patient", resp_422)
        data = flask_resp.get_json()
        assert status == 422
        assert any("Unprocessable" in issue["diagnostics"] for issue in data["issues"])

def test_fallback_generic_error(app, dummy_supported_param_schema):
    with app.app_context():
        resp = DummyFHIRResponse(418, {"unexpected": "format"}, text="I'm a teapot!")
        flask_resp, status = _enrich_search_resource_error("Patient", resp)
        data = flask_resp.get_json()
        assert status == 418
        assert data["issues"][0]["code"] == "unknown"
        assert "FHIR server returned status" in data["issues"][0]["diagnostics"]
