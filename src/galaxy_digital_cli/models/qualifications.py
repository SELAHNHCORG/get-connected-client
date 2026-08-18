"""Models for the ``/qualifications`` endpoints.

Field names are copied verbatim from ``doc/api.yml``; the API sends numeric
ids as strings and pydantic coerces them.
"""

from __future__ import annotations

from .base import GalaxyModel


class Qualification(GalaxyModel):
    """qualificationObject -- a credential a volunteer can hold or be asked for."""

    id: int | None = None
    domain_id: int | None = None
    qualification_title: str | None = None
    qualification_cat_id: int | None = None
    qualification_question: str | None = None
    qualification_type: str | None = None
    qualification_options: list[str] | None = None
    qualification_link_url: str | None = None
    qualification_link_text: str | None = None
    qualification_level: str | None = None
    qualification_duration: str | None = None
    qualification_approval: str | None = None
    qualification_status: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class QualificationUser(GalaxyModel):
    """qualificationUsersObject -- one user's standing on a qualification."""

    id: int | None = None
    domain_id: int | None = None
    user_fname: str | None = None
    user_lname: str | None = None
    user_email: str | None = None
    status: str | None = None
    expires: str | None = None
