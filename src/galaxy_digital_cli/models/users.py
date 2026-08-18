"""Models for the ``/users`` endpoints.

Field names are copied verbatim from ``doc/api.yml``; the API sends numeric
ids as strings and pydantic coerces them.
"""

from __future__ import annotations

from .base import GalaxyModel


class User(GalaxyModel):
    """userObject -- a site user (volunteer, manager or admin)."""

    id: int | None = None
    domain_id: int | None = None
    domain_sitename: str | None = None
    user_reference_id: str | None = None
    user_fname: str | None = None
    user_mname: str | None = None
    user_lname: str | None = None
    user_email: str | None = None
    user_phone: str | None = None
    user_phone_cell: str | None = None
    user_username: str | None = None
    user_address: str | None = None
    user_address2: str | None = None
    user_city: str | None = None
    user_state: str | None = None
    user_postal: str | None = None
    user_county: str | None = None
    user_country: str | None = None
    user_age_range: str | None = None
    user_disaster: str | None = None
    user_birthday: str | None = None
    user_company: str | None = None
    user_company_title: str | None = None
    user_department: str | None = None
    user_ethnicity: str | None = None
    user_gender: str | None = None
    user_grad_semester: str | None = None
    user_grad_year: str | None = None
    user_notes: str | None = None
    user_comments: str | None = None
    user_status: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class UserOneclick(GalaxyModel):
    """userOneclickObject -- a short-lived passwordless login link."""

    link: str | None = None
    expires: str | None = None
    now: str | None = None


class UserOptouts(GalaxyModel):
    """userOptoutsObject -- the message areas a user has opted out of."""

    id: int | None = None
    email: str | None = None
    optout_areas: list[str] | None = None
    date_added: str | None = None


class UserQualification(GalaxyModel):
    """userQualificationsObject -- one qualification held by a user."""

    id: int | None = None
    domain_id: int | None = None
    qualification_id: int | None = None
    qualification_title: str | None = None
    status: str | None = None
    expires: str | None = None


class UserResponse(GalaxyModel):
    """userResponseObject -- a user's signup for a need."""

    id: int | None = None
    need_id: int | None = None
    date_start: str | None = None
    duration: str | None = None
    status: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class RegistrationAnswer(GalaxyModel):
    """RegistrationResponseAnswerObject -- one answer to a registration question."""

    type: str | None = None
    key: str | None = None
    area: str | None = None
    question_id: int | None = None
    question: str | None = None
    answer: str | None = None
