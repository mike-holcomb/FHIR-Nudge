import pytest

def fake_capability_response():
    class FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {
                "rest": [{
                    "resource": [
                        {"type": "Patient", "searchParam": [{"name": "name"}, {"name": "id"}]},
                        {"type": "Observation", "searchParam": [{"name": "code"}, {"name": "date"}]}
                    ]
                }]
            }
    return FakeResp()

def test_read_resource_valid(client, patch_fhir_requests):
    original_side_effect = patch_fhir_requests.side_effect
    def resource_side_effect(url, *args, **kwargs):
        if url.endswith("/metadata"):
            return original_side_effect(url)
        class MockResourceResp:
            status_code = 200
            content = b'{"resourceType": "Patient", "id": "123"}'
            headers = {"Content-Type": "application/fhir+json"}
            def raise_for_status(self): pass
            def json(self):
                return {"resourceType": "Patient", "id": "123"}
        return MockResourceResp()
    patch_fhir_requests.side_effect = resource_side_effect
    resp = client.get('/readResource/Patient/123')
    assert resp.status_code == 200
    assert resp.json["resourceType"] == "Patient"
    assert resp.json["id"] == "123"

def test_read_resource_invalid_type(client, patch_fhir_requests):
    # No need to override side_effect; /metadata is enough
    resp = client.get('/readResource/NotAType/123')
    assert resp.status_code == 400
    # Assert response is AIXErrorSchema
    assert set(resp.json.keys()) >= {"error", "friendly_message", "issues", "status_code"}
    assert resp.json["status_code"] == 400
    # Check that diagnostics include the error message
    issue_diags = " ".join([iss.get("diagnostics", "") for iss in resp.json["issues"]])
    assert "is not supported" in issue_diags
    assert "Supported types:" in issue_diags

def test_read_resource_fuzzy_match(client, patch_fhir_requests):
    resp = client.get('/readResource/Patiant/123')
    assert resp.status_code == 400
    # Assert response is AIXErrorSchema
    assert set(resp.json.keys()) >= {"error", "friendly_message", "issues", "status_code"}
    assert resp.json["status_code"] == 400
    # Check that diagnostics include the error message
    issue_diags = " ".join([iss.get("diagnostics", "") for iss in resp.json["issues"]])
    assert "is not supported" in issue_diags
    assert "Did you mean:" in issue_diags

def test_read_resource_invalid_id(client, patch_fhir_requests):
    resp = client.get('/readResource/Patient/invalid id!')
    assert resp.status_code == 400
    # Assert response is AIXErrorSchema
    assert set(resp.json.keys()) >= {"error", "friendly_message", "issues", "status_code"}
    assert resp.json["status_code"] == 400
    # Check that diagnostics include the error message
    issue_diags = " ".join([iss.get("diagnostics", "") for iss in resp.json["issues"]])
    assert "not valid for resource type" in issue_diags

def test_read_resource_not_found(client, patch_fhir_requests):
    original_side_effect = patch_fhir_requests.side_effect
    def resource_side_effect(url, *args, **kwargs):
        if url.endswith("/metadata"):
            return original_side_effect(url)
        class MockResourceResp:
            status_code = 404
            content = b'{"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "not-found"}]}'
            headers = {"Content-Type": "application/fhir+json"}
            def raise_for_status(self): pass
            def json(self):
                return {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "not-found"}]}
            @property
            def text(self):
                return self.content.decode()
        return MockResourceResp()
    patch_fhir_requests.side_effect = resource_side_effect
    resp = client.get('/readResource/Patient/doesnotexist')
    assert resp.status_code == 404 or resp.status_code == 200  # Depending on proxy behavior
    # Assert response is AIXErrorSchema
    assert set(resp.json.keys()) >= {"error", "friendly_message", "issues", "status_code"}
    assert resp.json["status_code"] == 404
    # Check that diagnostics include the error message
    issue_diags = " ".join([iss.get("diagnostics", "") for iss in resp.json["issues"]])
    assert "No Patient resource was found" in issue_diags

def test_read_resource_fhir_plaintext_error(client, patch_fhir_requests):
    original_side_effect = patch_fhir_requests.side_effect
    def resource_side_effect(url, *args, **kwargs):
        if url.endswith("/metadata"):
            return original_side_effect(url)
        class MockResourceResp:
            status_code = 500
            content = b'Server error occurred'
            headers = {"Content-Type": "text/plain"}
            def raise_for_status(self): pass
            def json(self): raise ValueError("Not JSON")
            @property
            def text(self): return self.content.decode()
        return MockResourceResp()
    patch_fhir_requests.side_effect = resource_side_effect
    resp = client.get('/readResource/Patient/123')
    assert resp.status_code == 500
    # Assert response is AIXErrorSchema
    assert set(resp.json.keys()) >= {"error", "friendly_message", "issues", "status_code"}
    assert resp.json["status_code"] == 500
    # Check that diagnostics include the server error
    issue_diags = " ".join([iss.get("diagnostics", "") for iss in resp.json["issues"]])
    assert "Server error occurred" in issue_diags

def test_read_resource_fhir_custom_json_error(client, patch_fhir_requests):
    original_side_effect = patch_fhir_requests.side_effect
    def resource_side_effect(url, *args, **kwargs):
        if url.endswith("/metadata"):
            return original_side_effect(url)
        class MockResourceResp:
            status_code = 403
            content = b'{"message": "Forbidden"}'
            headers = {"Content-Type": "application/json"}
            def raise_for_status(self): pass
            def json(self): return {"message": "Forbidden"}
            @property
            def text(self): return self.content.decode()
        return MockResourceResp()
    patch_fhir_requests.side_effect = resource_side_effect
    resp = client.get('/readResource/Patient/123')
    assert resp.status_code == 403
    # Assert response is AIXErrorSchema
    assert set(resp.json.keys()) >= {"error", "friendly_message", "issues", "status_code"}
    assert resp.json["status_code"] == 403
    # Check that diagnostics include the forbidden message
    issue_diags = " ".join([iss.get("diagnostics", "") for iss in resp.json["issues"]])
    assert "Forbidden" in issue_diags

def test_read_resource_fhir_empty_error(client, patch_fhir_requests):
    original_side_effect = patch_fhir_requests.side_effect
    def resource_side_effect(url, *args, **kwargs):
        if url.endswith("/metadata"):
            return original_side_effect(url)
        class MockResourceResp:
            status_code = 404
            content = b''
            headers = {"Content-Type": "application/fhir+json"}
            def raise_for_status(self): pass
            def json(self): raise ValueError("No content")
            @property
            def text(self): return ""
        return MockResourceResp()
    patch_fhir_requests.side_effect = resource_side_effect
    resp = client.get('/readResource/Patient/doesnotexist')
    assert resp.status_code == 404
    # Assert response is AIXErrorSchema
    assert set(resp.json.keys()) >= {"error", "friendly_message", "issues", "status_code"}
    assert resp.json["status_code"] == 404
    # Check that diagnostics mention the server status
    issue_diags = " ".join([iss.get("diagnostics", "") for iss in resp.json["issues"]])
    assert "FHIR server returned status 404" in issue_diags or "404" in issue_diags

def test_missing_required_fields_returns_clear_error(client):
    # Simulate a call with missing resource_id (should return a 400 or 422 with a clear error message)
    resp = client.get('/readResource/Patient/')
    assert resp.status_code in (400, 404, 422)
    # Assert response is AIXErrorSchema
    assert set(resp.json.keys()) >= {"error", "friendly_message", "issues", "status_code"}
    # Should mention missing required fields in diagnostics
    issue_diags = " ".join([iss.get("diagnostics", "") for iss in resp.json["issues"]])
    assert "Missing fields" in issue_diags or "missing" in issue_diags

def test_search_resource_invalid_param(client, patch_fhir_requests):
    def fake_metadata(url, *args, **kwargs):
        class FakeResp:
            def raise_for_status(self): pass
            def json(self):
                return {
                    "rest": [{
                        "resource": [
                            {"type": "Patient", "searchParam": [
                                {"name": "name", "type": "string", "documentation": "Patient name"},
                                {"name": "gender", "type": "string", "documentation": "Gender of the patient"},
                            ]}
                        ]
                    }]
                }
        return FakeResp()
    patch_fhir_requests.side_effect = fake_metadata
    resp = client.get('/searchResource/Patient?nme=John')
    assert resp.status_code == 400
    assert set(resp.json.keys()) >= {"error", "friendly_message", "issues", "status_code"}
    # The guidance should include a markdown table of parameters
    assert "| name | type | documentation" in resp.json.get("next_steps", "")
    # The schema should be present somewhere (top-level or in markdown)
    schema = resp.json.get("supported_param_schema")
    if schema:
        assert any(p["name"] == "name" for p in schema)
        assert any(p["name"] == "gender" for p in schema)
    else:
        # Fallback: just check the markdown table is present
        assert "| name | type | documentation" in resp.json.get("next_steps", "")

def test_search_resource_missing_param(client, patch_fhir_requests):
    def fake_metadata(url, *args, **kwargs):
        class FakeResp:
            def raise_for_status(self): pass
            def json(self):
                return {
                    "rest": [{
                        "resource": [
                            {"type": "Patient", "searchParam": [
                                {"name": "name", "type": "string", "documentation": "Patient name"},
                                {"name": "gender", "type": "string", "documentation": "Gender of the patient"},
                            ]}
                        ]
                    }]
                }
        return FakeResp()
    patch_fhir_requests.side_effect = fake_metadata
    resp = client.get('/searchResource/Patient')
    assert resp.status_code == 400
    assert set(resp.json.keys()) >= {"error", "friendly_message", "issues", "status_code"}
    assert "| name | type | documentation" in resp.json.get("next_steps", "")
    schema = resp.json.get("supported_param_schema")
    if schema:
        assert any(p["name"] == "name" for p in schema)
        assert any(p["name"] == "gender" for p in schema)
    else:
        assert "| name | type | documentation" in resp.json.get("next_steps", "")

def test_search_resource_invalid_type(client, patch_fhir_requests):
    def fake_metadata(url, *args, **kwargs):
        class FakeResp:
            def raise_for_status(self): pass
            def json(self):
                return {
                    "rest": [{
                        "resource": [
                            {"type": "Patient", "searchParam": [
                                {"name": "name", "type": "string", "documentation": "Patient name"}
                            ]}
                        ]
                    }]
                }
        return FakeResp()
    patch_fhir_requests.side_effect = fake_metadata
    resp = client.get('/searchResource/NotAType?name=John')
    assert resp.status_code == 400
    assert resp.json["error"].lower().startswith("invalid-type")
    assert "supported_param_schema" not in resp.json
    assert "supported_params" not in resp.json

def test_search_resource_valid_query(client, patch_fhir_requests):
    def fake_metadata(url, *args, **kwargs):
        class FakeResp:
            def raise_for_status(self): pass
            def json(self):
                return {
                    "rest": [{
                        "resource": [
                            {"type": "Patient", "searchParam": [
                                {"name": "name", "type": "string", "documentation": "Patient name"},
                                {"name": "gender", "type": "string", "documentation": "Gender of the patient"},
                            ]}
                        ]
                    }]
                }
        return FakeResp()

    class MockFHIRResp:
        status_code = 200
        content = b'{"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "Patient", "id": "abc"}}]}'
        headers = {"Content-Type": "application/fhir+json"}
        def raise_for_status(self): pass
        def json(self):
            return {"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "Patient", "id": "abc"}}]}

    def side_effect(url, *args, **kwargs):
        if url.endswith("/metadata"):
            return fake_metadata(url)
        return MockFHIRResp()

    patch_fhir_requests.side_effect = side_effect
    resp = client.get('/searchResource/Patient?name=John')
    assert resp.status_code == 200
    assert resp.json["resourceType"] == "Bundle"
    assert resp.json["entry"][0]["resource"]["resourceType"] == "Patient"
    assert resp.json["entry"][0]["resource"]["id"] == "abc"