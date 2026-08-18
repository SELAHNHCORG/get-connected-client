"""Pydantic models for the Galaxy Digital "Get Connected" API."""

from __future__ import annotations

from .agencies import Agency
from .base import GalaxyModel
from .common import (
    AgencyMini,
    BenchmarkMini,
    Category,
    Cause,
    Cluster,
    Extra,
    GroupMini,
    Impact,
    InitiativeMini,
    Interest,
    NeedMini,
    Question,
    Shift,
    Tag,
    TeamMini,
    TrackMini,
    UserMini,
)
from .events import Event
from .groups import Group, GroupUser
from .hours import Hour
from .needs import Need
from .responses import Response, ResponseAnswer
from .teams import Team, TeamMember
from .users import (
    RegistrationAnswer,
    User,
    UserOneclick,
    UserOptouts,
    UserQualification,
    UserResponse,
)

__all__ = [
    "Agency",
    "AgencyMini",
    "BenchmarkMini",
    "Category",
    "Cause",
    "Cluster",
    "Event",
    "Extra",
    "GalaxyModel",
    "Group",
    "GroupMini",
    "GroupUser",
    "Hour",
    "Impact",
    "InitiativeMini",
    "Interest",
    "Need",
    "NeedMini",
    "Question",
    "RegistrationAnswer",
    "Response",
    "ResponseAnswer",
    "Shift",
    "Tag",
    "Team",
    "TeamMember",
    "TeamMini",
    "TrackMini",
    "User",
    "UserMini",
    "UserOneclick",
    "UserOptouts",
    "UserQualification",
    "UserResponse",
]
