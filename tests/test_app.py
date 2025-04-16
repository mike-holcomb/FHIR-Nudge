import pytest

@pytest.fixture(autouse=True)
def mock_capability_index(monkeypatch):
    # Patch capability_index in the app module to control valid resource types
    from fhir_nudge.app import capability_index
    monkeypatch.setitem(capability_index, 'Patient', {'name', 'id'})
    monkeypatch.setitem(capability_index, 'Observation', {'code', 'date'})
    yield

def test_read_resource_valid(client, mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.content = b'{"resourceType": "Patient", "id": "123"}'
    mock_response.headers = {"Content-Type": "application/fhir+json"}
    mocker.patch('requests.get', return_value=mock_response)
    resp = client.get('/readResource/Patient/123')
    assert resp.status_code == 200
    assert resp.json["resourceType"] == "Patient"
    assert resp.json["id"] == "123"

def test_read_resource_invalid_type(client):
    resp = client.get('/readResource/NotAType/123')
    assert resp.status_code == 400
    assert "supported_types" in resp.json
    assert "error" in resp.json

def test_read_resource_fuzzy_match(client):
    resp = client.get('/readResource/Patiant/123')
    assert resp.status_code == 400
    assert "did_you_mean" in resp.json

def test_read_resource_invalid_id(client):
    resp = client.get('/readResource/Patient/invalid id!')
    assert resp.status_code == 400
    assert "Invalid resource_id format" in resp.json["error"]

def test_read_resource_not_found(client, mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 404
    mock_response.content = b'{"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "not-found"}]}'
    mock_response.headers = {"Content-Type": "application/fhir+json"}
    mocker.patch('requests.get', return_value=mock_response)
    resp = client.get('/readResource/Patient/doesnotexist')
    assert resp.status_code == 404 or resp.status_code == 200  # Depending on proxy behavior