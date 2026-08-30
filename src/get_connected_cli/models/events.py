"""Models for the ``/events`` endpoints.

Field names are copied verbatim from ``doc/api.yml``; the API sends numeric
ids as strings and pydantic coerces them.
"""

from __future__ import annotations

from .base import GalaxyModel
from .common import Tag


class Event(GalaxyModel):
    """eventObject -- an agency event.

    ``update_at`` is spelled that way in the spec -- the API's own typo (see
    also ``benchmarkMiniObject``), kept verbatim so payloads round-trip.
    """

    id: int | None = None
    domain_id: int | None = None
    event_area: str | None = None
    event_area_id: int | None = None
    event_title: str | None = None
    event_description: str | None = None
    event_location: str | None = None
    event_address: str | None = None
    event_address2: str | None = None
    event_city: str | None = None
    event_state: str | None = None
    event_postal: str | None = None
    event_email: str | None = None
    event_rsvp: str | None = None
    event_date_start: str | None = None
    event_date_end: str | None = None
    event_all_day: str | None = None
    event_comments: str | None = None
    tags: list[Tag] | None = None
    created_at: str | None = None
    update_at: str | None = None
