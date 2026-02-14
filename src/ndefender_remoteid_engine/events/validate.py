from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from typing import Any, Iterable

from jsonschema import Draft202012Validator


@dataclass(frozen=True)
class ValidationError:
    message: str
    path: str


def _load_schema() -> dict[str, Any]:
    with resources.files(__package__).joinpath("schema.json").open("r", encoding="utf-8") as fh:
        return json.load(fh)


_SCHEMA = _load_schema()
_VALIDATOR = Draft202012Validator(_SCHEMA)


def iter_errors(event: dict[str, Any]) -> Iterable[ValidationError]:
    for error in _VALIDATOR.iter_errors(event):
        path = "/".join(str(item) for item in error.path)
        yield ValidationError(message=error.message, path=path)


def validate_event(event: dict[str, Any]) -> None:
    errors = list(iter_errors(event))
    if errors:
        details = "; ".join(
            f"{err.message} at {err.path or '$'}" for err in errors
        )
        raise ValueError(f"event validation failed: {details}")
