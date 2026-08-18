"""Models for the ``/needs/{id}/responses`` endpoint.

Field names are copied verbatim from ``doc/api.yml``; the API sends numeric
ids as strings and pydantic coerces them.
"""

from __future__ import annotations

from .base import GalaxyModel
from .common import AgencyMini, InitiativeMini, NeedMini, Shift, TeamMini, UserMini


class ResponseAnswer(GalaxyModel):
    """ResponseAnswerObject -- one answer on a response's question set."""

    type: str | None = None
    key: str | None = None
    area: str | None = None
    question: str | None = None
    answer: str | None = None


class Response(GalaxyModel):
    """responseObject -- a volunteer's response to a need."""

    id: int | None = None
    domain_id: int | None = None
    agency: AgencyMini | None = None
    shift: Shift | None = None
    need: NeedMini | None = None
    user: UserMini | None = None
    initiative: InitiativeMini | None = None
    team: TeamMini | None = None
    response_phone: str | None = None
    response_address: str | None = None
    response_note: str | None = None
    response_date_added: str | None = None
    response_date_updated: str | None = None
    response_source: str | None = None
    response_status: str | None = None
    response_comments: str | None = None
    answers: list[ResponseAnswer] | None = None
