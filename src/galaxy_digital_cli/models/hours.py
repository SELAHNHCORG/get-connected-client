"""Models for volunteer hour records (``hourObject``)."""

from __future__ import annotations

from .base import GalaxyModel
from .common import GroupMini, NeedMini, UserMini


class Hour(GalaxyModel):
    """hourObject -- one submitted block of volunteer time."""

    id: int | None = None
    domain_id: int | None = None
    user: UserMini | None = None
    groups: list[GroupMini] | None = None
    need: NeedMini | None = None
    hour_description: str | None = None
    hour_date_start: str | None = None
    hour_date_end: str | None = None
    hour_hours: str | None = None
    hour_miles: str | None = None
    hour_location: str | None = None
    hour_contact_name: str | None = None
    hour_contact_details: str | None = None
    hour_relationship: str | None = None
    hour_parent: str | None = None
    hour_source: str | None = None
    hour_status: str | None = None
    hour_type: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
