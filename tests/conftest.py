import pytest
import sys

@pytest.fixture(autouse=True)
def patch_requests_get_for_capability(mocker):
    # Patch requests.get BEFORE any test, for lazy loading
    import types
    def fake_get(url, *args, **kwargs):
        if url.endswith("/metadata"):
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
        raise RuntimeError("Unexpected URL in test: " + url)
    mocker.patch("requests.get", side_effect=fake_get)
    yield

from fhir_nudge.app import app as flask_app

@pytest.fixture
def app():
    flask_app.config.update({
        "TESTING": True,
    })
    yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()