"""Models for the ``/groups`` endpoints.

Field names are copied verbatim from ``doc/api.yml``; the API sends numeric
ids as strings and pydantic coerces them.
"""

from __future__ import annotations

from .base import GalaxyModel
from .common import AgencyMini, NeedMini, Question


class GroupUser(GalaxyModel):
    """GroupUserMiniObject -- one user attached to a user group."""

    id: int | None = None
    domain_id: int | None = None
    user_fname: str | None = None
    user_lname: str | None = None
    user_email: str | None = None
    leader: str | None = None


class Group(GalaxyModel):
    """groupObject -- a user group.

    Called "team" in some Get Connected UI copy, but this is a distinct
    resource from ``teamObject``/:class:`~get_connected_client.models.teams.Team`.
    """

    id: int | None = None
    domain_id: int | None = None
    ug_status: str | None = None
    ug_title: str | None = None
    ug_description: str | None = None
    ug_description_private: str | None = None
    ug_domains: str | None = None
    ug_color: str | None = None
    ug_text_color: str | None = None
    ug_icon: str | None = None
    ug_suppress_resume: str | None = None
    ug_allow_member_remove: str | None = None
    ug_submitted_hours: str | None = None
    ug_block_id: str | None = None
    ug_limit: str | None = None
    ug_goal: str | None = None
    ug_approval: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    needs: list[NeedMini] | None = None
    users: list[GroupUser] | None = None
    agencies: list[AgencyMini] | None = None
    questions_reflection: list[Question] | None = None
    questions_join: list[Question] | None = None
