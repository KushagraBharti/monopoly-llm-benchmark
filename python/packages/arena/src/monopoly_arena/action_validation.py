from __future__ import annotations

from functools import lru_cache
from typing import Any

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from jsonschema.exceptions import ValidationError  # type: ignore[import-untyped]
from jsonschema.validators import validator_for  # type: ignore[import-untyped]

from .schema_registry import get_schema, get_schema_registry


@lru_cache(maxsize=1)
def _load_action_schema() -> dict[str, Any]:
    return get_schema("action.schema.json")


@lru_cache(maxsize=1)
def _action_validator() -> Draft202012Validator:
    schema = _load_action_schema()
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)
    return validator_cls(schema, registry=get_schema_registry())


def _format_error(error: ValidationError) -> str:
    if error.path:
        path = "$"
        for part in error.path:
            if isinstance(part, int):
                path += f"[{part}]"
            else:
                path += f".{part}"
    else:
        path = "$"
    return f"{path}: {error.message}"


def validate_action_payload(action: dict[str, Any]) -> tuple[bool, list[str]]:
    validator = _action_validator()
    errors = [_format_error(err) for err in validator.iter_errors(action)]
    if errors:
        return False, errors
    return True, []
