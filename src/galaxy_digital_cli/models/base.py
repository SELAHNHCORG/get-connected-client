"""Base model preserving unknown fields (the API schema is loose)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class GalaxyModel(BaseModel):
    """Base for all Galaxy Digital API models.

    The Get Connected API returns loose data - ids are sometimes strings,
    and responses may include fields not documented in the OpenAPI spec.
    This base coerces id-like fields via each model's field types and
    preserves any unknown fields so round-tripping through
    ``model_dump()`` does not silently drop data.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)
