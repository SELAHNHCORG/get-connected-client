"""Pydantic models for the Galaxy Digital "Get Connected" API."""

from __future__ import annotations

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
from .hours import Hour
from .users import (
    RegistrationAnswer,
    User,
    UserOneclick,
    UserOptouts,
    UserQualification,
    UserResponse,
)

__all__ = [
    "AgencyMini",
    "BenchmarkMini",
    "Category",
    "Cause",
    "Cluster",
    "Extra",
    "GalaxyModel",
    "GroupMini",
    "Hour",
    "Impact",
    "InitiativeMini",
    "Interest",
    "NeedMini",
    "Question",
    "RegistrationAnswer",
    "Shift",
    "Tag",
    "TeamMini",
    "TrackMini",
    "User",
    "UserMini",
    "UserOneclick",
    "UserOptouts",
    "UserQualification",
    "UserResponse",
]
