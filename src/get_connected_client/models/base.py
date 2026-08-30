"""Base model preserving unknown fields (the API schema is loose)."""

from __future__ import annotations

import types
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, model_validator


def _int_only(annotation: Any) -> bool:
    """True when a field annotation accepts ``int`` but not ``str``.

    Such fields need protection from the live API's habit of sending ``""``
    (or other junk) where the spec declares an integer.
    """
    if annotation is int:
        return True
    if get_origin(annotation) not in (types.UnionType, Union):
        return False
    args = get_args(annotation)
    return int in args and str not in args


class GalaxyModel(BaseModel):
    """Base for all Galaxy Digital API models.

    The Get Connected API returns loose data - ids are sometimes strings,
    responses may include fields not documented in the OpenAPI spec, and
    integer fields occasionally arrive as ``""`` or non-numeric strings.
    This base preserves unknown fields so round-tripping through
    ``model_dump()`` does not silently drop data, and degrades unparseable
    numerics to ``None`` instead of refusing the whole record.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def _tolerate_loose_numerics(cls, data: Any) -> Any:
        """Null out strings the API sends where the spec promises integers.

        Seen live: ``shifts[].slots`` arrives as ``""``. A viewer model must
        not reject an entire record over one unparseable numeric, so for
        int-typed fields a string is coerced (``"3"`` -> 3, ``"3.0"`` -> 3)
        and anything unparseable becomes ``None``.
        """
        if not isinstance(data, dict):
            return data
        cleaned: dict[str, Any] | None = None
        for name, field in cls.model_fields.items():
            value = data.get(name)
            if not isinstance(value, str) or not _int_only(field.annotation):
                continue
            text = value.strip()
            coerced: int | None
            try:
                coerced = int(text)
            except ValueError:
                try:
                    coerced = int(float(text))
                except (ValueError, OverflowError):
                    coerced = None
            if cleaned is None:
                cleaned = dict(data)
            cleaned[name] = coerced
        return cleaned if cleaned is not None else data
