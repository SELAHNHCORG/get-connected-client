"""Models for the ``/needs`` endpoints.

Field names are copied verbatim from ``doc/api.yml``; the API sends numeric
ids as strings and pydantic coerces them.
"""

from __future__ import annotations

from .base import GalaxyModel
from .common import AgencyMini, GroupMini, InitiativeMini, Shift, Tag


class Need(GalaxyModel):
    """needObject -- an opportunity an agency has posted."""

    id: int | None = None
    domain_id: int | None = None
    agency: AgencyMini | None = None
    initiative: InitiativeMini | None = None
    groups: list[GroupMini] | None = None
    need_title: str | None = None
    need_body: str | None = None
    need_address: str | None = None
    need_address2: str | None = None
    need_city: str | None = None
    need_state: str | None = None
    need_postal: str | None = None
    need_type: str | None = None
    need_contact: str | None = None
    need_response_notify: str | None = None
    need_date: str | None = None
    need_date_type: str | None = None
    need_impact_area: str | None = None
    need_volunteers_needed: str | None = None
    need_public: str | None = None
    need_allow_groups: str | None = None
    need_hours: str | None = None
    need_comments: str | None = None
    need_latitude: str | None = None
    need_longitude: str | None = None
    need_date_close: str | None = None
    family_friendly: str | None = None
    outdoors: str | None = None
    outdoors_plan: str | None = None
    accessible: str | None = None
    tags: list[Tag] | None = None
    shifts: list[Shift] | None = None
    need_status: str | None = None
    created_at: str | None = None
    background_check_required: str | None = None
    updated_at: str | None = None
