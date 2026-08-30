"""Models for the ``/teams`` endpoints.

Field names are copied verbatim from ``doc/api.yml``; the API sends numeric
ids as strings and pydantic coerces them.
"""

from __future__ import annotations

from .base import GalaxyModel
from .common import AgencyMini, NeedMini, UserMini


class TeamMember(GalaxyModel):
    """teamMembersObject -- one member of a team."""

    id: int | None = None
    domain_id: int | None = None
    user_fname: str | None = None
    user_lname: str | None = None
    user_email: str | None = None
    leader: str | None = None


class Team(GalaxyModel):
    """teamObject -- a group of volunteers responding together to one need."""

    id: int | None = None
    domain_id: int | None = None
    team_status: str | None = None
    team_title: str | None = None
    team_description: str | None = None
    creator: UserMini | None = None
    agency: AgencyMini | None = None
    need: NeedMini | None = None
    members: list[TeamMember] | None = None
