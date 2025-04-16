import pytest
from fhir_nudge.schemas import AIXErrorResponse
from fhir_nudge import error_renderer

# --- Code-based error rendering tests ---

def test_code_based_not_found_renders_correctly():
    error_data = {
        "resource_type": "Patient",
        "resource_id": "123",
        "status_code": 404,
        "issues": [],
    }
    aix_error = error_renderer.render_error("not_found", error_data)
    assert isinstance(aix_error, AIXErrorResponse)
    assert aix_error.error == "Not found"
    assert "No Patient resource was found with ID '123'" in aix_error.friendly_message
    assert aix_error.status_code == 404
    assert aix_error.resource_type == "Patient"
    assert aix_error.resource_id == "123"
    assert aix_error.next_steps == "Try searching for the Patient using /searchResource."

def test_code_based_not_found_with_different_resource():
    error_data = {
        "resource_type": "Observation",
        "resource_id": "obs-456",
        "status_code": 404,
        "issues": [],
    }
    aix_error = error_renderer.render_error("not_found", error_data)
    assert "No Observation resource was found with ID 'obs-456'" in aix_error.friendly_message
    assert aix_error.next_steps == "Try searching for the Observation using /searchResource."

def test_code_based_invalid_id_renders_expected_format():
    error_data = {
        "resource_type": "Patient",
        "resource_id": "badid",
        "expected_id_format": "alphanumeric, 6-12 characters",
        "status_code": 400,
        "issues": [],
    }
    aix_error = error_renderer.render_error("invalid_id", error_data)
    assert "The ID 'badid' is not valid for resource type 'Patient'" in aix_error.friendly_message
    assert "Expected format: alphanumeric, 6-12 characters" in aix_error.next_steps
    assert aix_error.status_code == 400
    assert aix_error.resource_type == "Patient"
    assert aix_error.resource_id == "badid"

def test_code_based_generic_error_fallback():
    error_data = {
        "resource_type": "Patient",
        "resource_id": "999",
        "status_code": 500,
        "issues": [],
    }
    aix_error = error_renderer.render_error("unknown_error", error_data)
    assert aix_error.friendly_message == "An error occurred."
    assert aix_error.next_steps is None

def test_missing_required_fields_raises_value_error():
    error_data = {
        "resource_type": "Patient",
        # missing 'resource_id' and 'status_code'
        "issues": [],
    }
    result = error_renderer.render_error("not_found", error_data)
    # Should not raise, but should warn in diagnostics
    issues = result.issues
    diag_msgs = " ".join([iss.diagnostics or "" for iss in issues])
    assert "Missing fields" in diag_msgs or "missing" in diag_msgs

def test_render_error_logs_warning_on_fallback(caplog):
    error_data = {
        "resource_type": "Patient",
        "resource_id": "999",
        "status_code": 500,
        "issues": [],
    }
    with caplog.at_level("WARNING"):
        aix_error = error_renderer.render_error("not_a_real_error_type", error_data)
    assert aix_error.friendly_message == "An error occurred."
    assert "render_error: Unknown error_type 'not_a_real_error_type'" in caplog.text
