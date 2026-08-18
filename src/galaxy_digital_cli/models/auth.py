"""Models for the credential-exchange endpoints.

``/users/authenticate`` answers with an array of
:class:`~galaxy_digital_cli.models.users.UserOneclick` rows directly, so it
needs no model of its own here -- only ``/users/login``'s response shape,
``loginObject``, does.
"""

from __future__ import annotations

from .base import GalaxyModel
from .users import User


class LoginResult(GalaxyModel):
    """loginObject -- the outcome of ``POST /users/login``.

    ``user`` is typed as the full
    :class:`~galaxy_digital_cli.models.users.User` model even though the
    spec's nested object documents only five of its fields -- every ``User``
    field is optional, so the smaller payload parses cleanly and callers get
    the same shape as ``client.users.get``.
    """

    user: User | None = None
    token: str | None = None
    expires: str | None = None
