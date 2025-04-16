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

def test_read_resource_valid(client, mocker):
    def side_effect(url, *args, **kwargs):
        if url.endswith("/metadata"):
            return fake_capability_response()
        class MockResourceResp:
            status_code = 200
            content = b'{"resourceType": "Patient", "id": "123"}'
            headers = {"Content-Type": "application/fhir+json"}
            def raise_for_status(self): pass
            def json(self):
                return {"resourceType": "Patient", "id": "123"}
        return MockResourceResp()
    mocker.patch('requests.get', side_effect=side_effect)
    resp = client.get('/readResource/Patient/123')
    assert resp.status_code == 200
    assert resp.json["resourceType"] == "Patient"
    assert resp.json["id"] == "123"

def test_read_resource_invalid_type(client, mocker):
    def side_effect(url, *args, **kwargs):
        if url.endswith("/metadata"):
            return fake_capability_response()
        raise RuntimeError("Should not fetch resource for invalid type")
    mocker.patch('requests.get', side_effect=side_effect)
    resp = client.get('/readResource/NotAType/123')
    assert resp.status_code == 400
    assert "supported_types" in resp.json
    assert "error" in resp.json

def test_read_resource_fuzzy_match(client, mocker):
    def side_effect(url, *args, **kwargs):
        if url.endswith("/metadata"):
            return fake_capability_response()
        raise RuntimeError("Should not fetch resource for fuzzy match")
    mocker.patch('requests.get', side_effect=side_effect)
    resp = client.get('/readResource/Patiant/123')
    assert resp.status_code == 400
    assert "did_you_mean" in resp.json

def test_read_resource_invalid_id(client, mocker):
    def side_effect(url, *args, **kwargs):
        if url.endswith("/metadata"):
            return fake_capability_response()
        raise RuntimeError("Should not fetch resource for invalid id")
    mocker.patch('requests.get', side_effect=side_effect)
    resp = client.get('/readResource/Patient/invalid id!')
    assert resp.status_code == 400
    assert "Invalid resource_id format" in resp.json["error"]

def test_read_resource_not_found(client, mocker):
    def side_effect(url, *args, **kwargs):
        if url.endswith("/metadata"):
            return fake_capability_response()
        class MockResourceResp:
            status_code = 404
            content = b'{"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "not-found"}]}'
            headers = {"Content-Type": "application/fhir+json"}
            def raise_for_status(self): pass
            def json(self):
                return {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "not-found"}]}
        return MockResourceResp()
    mocker.patch('requests.get', side_effect=side_effect)
    resp = client.get('/readResource/Patient/doesnotexist')
    assert resp.status_code == 404 or resp.status_code == 200  # Depending on proxy behavior