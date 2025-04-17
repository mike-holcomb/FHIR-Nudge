import pytest
from flask import Flask
from fhir_nudge.app import _empty_search_bundle_response

@pytest.fixture
def dummy_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def dummy_supported_param_schema(monkeypatch):
    schema = [
        {"name": "name", "type": "string", "documentation": "Patient name"},
        {"name": "gender", "type": "string", "documentation": "Gender of the patient"},
    ]
    monkeypatch.setattr("fhir_nudge.app.get_capability_index", lambda: {"Patient": schema})
    return schema

def test_empty_search_bundle_response_basic(dummy_app, dummy_supported_param_schema):
    with dummy_app.app_context():
        query_params = {"name": "John Smith", "gender": "male"}
        resp, status = _empty_search_bundle_response("Patient", query_params)
        data = resp.get_json()
        assert status == 200
        assert data["resourceType"] == "Bundle"
        assert data["entry"] == []
        assert "No Patient resources matched your search criteria." in data["friendly_message"]
        assert "Double-check the search parameters you used" in data["next_steps"]
        assert "name: John Smith" in data["next_steps"]
        assert "gender: male" in data["next_steps"]
        assert "| name | type | documentation" in data["next_steps"]
        assert "Patient name" in data["next_steps"]

def test_empty_search_bundle_response_no_params(dummy_app, dummy_supported_param_schema):
    with dummy_app.app_context():
        query_params = {}
        resp, status = _empty_search_bundle_response("Patient", query_params)
        data = resp.get_json()
        assert status == 200
        assert data["resourceType"] == "Bundle"
        assert data["entry"] == []
        assert "No Patient resources matched your search criteria." in data["friendly_message"]
        assert "Double-check the search parameters you used" in data["next_steps"]
        assert "Supported search parameters for 'Patient'" in data["next_steps"]
