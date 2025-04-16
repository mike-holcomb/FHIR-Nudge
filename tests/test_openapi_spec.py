from openapi_spec_validator import validate
import yaml
import os

def test_openapi_spec_is_valid():
    spec_path = os.path.join(os.path.dirname(__file__), '..', 'openapi.yaml')
    with open(spec_path, 'r') as f:
        spec_dict = yaml.safe_load(f)
    validate(spec_dict)