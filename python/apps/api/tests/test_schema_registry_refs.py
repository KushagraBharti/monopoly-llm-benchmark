import json

from jsonschema import Draft202012Validator

from monopoly_api.paths import resolve_repo_root
from monopoly_api.schema_registry import get_schema, get_schema_registry


def test_decision_schema_ref_resolution() -> None:
    schema = get_schema("decision.schema.json")
    validator = Draft202012Validator(schema, registry=get_schema_registry())
    example_path = resolve_repo_root() / "contracts" / "examples" / "decision.example.json"
    payload = json.loads(example_path.read_text(encoding="utf-8"))
    errors = list(validator.iter_errors(payload))
    assert errors == []
