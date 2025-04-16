import pytest
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

@pytest.fixture
def patch_fhir_requests(mocker):
    """
    Patch requests.get so that /metadata returns a fake CapabilityStatement, and allow
test code to inject resource fetch responses by overriding patch_fhir_requests.side_effect.
    """
    def default_side_effect(url, *args, **kwargs):
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
        raise NotImplementedError("No resource fetch response provided for test: " + url)
    patch = mocker.patch('requests.get', side_effect=default_side_effect)
    patch.side_effect = default_side_effect  # Allow override in test
    return patch