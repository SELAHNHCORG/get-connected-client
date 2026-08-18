"""Small shared models used across Galaxy Digital API resources.

Each class corresponds to a schema in ``components.schemas`` of the
vendored OpenAPI spec (``doc/api.yml``). Field names match the spec
verbatim. The API represents numeric ids as strings; pydantic coerces
those to ``int`` on validation.
"""

from __future__ import annotations

from .base import GalaxyModel


class Tag(GalaxyModel):
    """tagObject."""

    id: int | None = None
    name: str | None = None


class Cause(GalaxyModel):
    """causeObject."""

    id: int | None = None
    name: str | None = None


class Cluster(GalaxyModel):
    """clusterObject."""

    id: int | None = None
    name: str | None = None


class Interest(GalaxyModel):
    """interestObject."""

    id: int | None = None
    name: str | None = None


class Impact(GalaxyModel):
    """impactObject."""

    id: int | None = None
    impact_name: str | None = None


class Category(GalaxyModel):
    """categoryObject."""

    id: int | None = None
    name: str | None = None


class Extra(GalaxyModel):
    """extraObject."""

    key: str | None = None
    value: str | None = None


class Question(GalaxyModel):
    """questionObject."""

    id: int | None = None
    q_type: str | None = None
    q_label: str | None = None
    q_options: list[str] | None = None
    q_area: str | None = None
    q_area_id: int | None = None
    q_status: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class Shift(GalaxyModel):
    """shiftObject."""

    id: int | None = None
    start: str | None = None
    end: str | None = None
    duration: str | None = None
    slots: int | None = None


class TrackMini(GalaxyModel):
    """trackMiniObject."""

    id: int | None = None
    name: str | None = None
    created_at: str | None = None


class BenchmarkMini(GalaxyModel):
    """benchmarkMiniObject.

    ``update_at`` is spelled that way in the spec -- the API's own typo, kept
    verbatim so payloads round-trip.
    """

    id: int | None = None
    benchmark_status: str | None = None
    benchmark_title: str | None = None
    benchmark_icon: str | None = None
    benchmark_hours: str | None = None
    benchmark_date_start: str | None = None
    benchmark_date_end: str | None = None
    created_at: str | None = None
    update_at: str | None = None


class UserMini(GalaxyModel):
    """userMiniObject."""

    id: int | None = None
    domain_id: int | None = None
    user_fname: str | None = None
    user_lname: str | None = None
    user_email: str | None = None


class AgencyMini(GalaxyModel):
    """agencyMiniObject."""

    id: int | None = None
    domain_id: int | None = None
    agency_name: str | None = None


class NeedMini(GalaxyModel):
    """needMiniObject."""

    id: int | None = None
    domain_id: int | None = None
    need_title: str | None = None


class GroupMini(GalaxyModel):
    """groupMiniObject."""

    id: int | None = None
    domain_id: int | None = None
    group_title: str | None = None


class InitiativeMini(GalaxyModel):
    """initiativeMiniObject."""

    id: int | None = None
    domain_id: int | None = None
    init_title: str | None = None


class TeamMini(GalaxyModel):
    """teamMiniObject."""

    id: int | None = None
    domain_id: int | None = None
    team_name: str | None = None
