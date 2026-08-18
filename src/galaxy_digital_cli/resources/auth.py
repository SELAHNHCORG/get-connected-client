"""The credential-exchange namespace: ``/users/login`` and
``/users/authenticate`` -- the pair
:class:`~galaxy_digital_cli.resources.users.Users` deliberately leaves out.
"""

from __future__ import annotations

from typing import Any

from ..models.auth import LoginResult
from ..models.users import UserOneclick
from .base import Resource


class Auth(Resource[LoginResult]):
    """Credential exchange, covering the two paths ``Users`` excludes.

    2 of 2 paths, 2 of 2 operations, full coverage of the pair. Combined
    with :class:`~galaxy_digital_cli.resources.users.Users`'s 21 of 23, the
    API is now covered end to end -- 66 of 66 paths across the whole client.

    Both :meth:`login` and :meth:`authenticate` are POSTs and so pass
    through the client's ordinary read-only choke point:
    ``client.request`` refuses every write when the client is in read-only
    mode, and login/authenticate are no exception -- a login mints a bearer
    token, which is a side effect worth gating even though it changes
    nothing about a stored record. ``--read-only`` therefore blocks both
    commands on the CLI just as it blocks ``create``/``update``/``delete``
    elsewhere.
    """

    path = "/users"
    model = LoginResult

    def login(
        self, user_email: str, user_password: str, key: str | None = None
    ) -> LoginResult | dict[str, Any] | None:
        """Exchange credentials (and API *key*) for a session token.

        The spec marks ``key`` required; pass ``None`` (the default) to
        send an empty string, which most deployments accept.

        :return: a :class:`~galaxy_digital_cli.models.auth.LoginResult` when
            the API answers with a ``data`` object; otherwise the raw
            response payload, mirroring
            :meth:`~galaxy_digital_cli.resources.base.CreateMixin.create`.
        """
        payload = self._client.request(
            "POST",
            self._url("login"),
            json={
                "user_email": user_email,
                "user_password": user_password,
                "key": key or "",
            },
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict):
            return self._parse(data)
        return payload

    def authenticate(self, user_email: str, user_password: str) -> list[UserOneclick]:
        """Verify credentials and mint a one-click login link.

        The spec has ``data`` answer with an *array* of
        :class:`~galaxy_digital_cli.models.users.UserOneclick` rows rather
        than a bare object -- confirmed against ``doc/api.yml``'s
        ``authenticateResponse``.
        """
        payload = self._client.request(
            "POST",
            self._url("authenticate"),
            json={"user_email": user_email, "user_password": user_password},
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        rows = data if isinstance(data, list) else ([data] if data else [])
        return [self._parse(r, UserOneclick) for r in rows if isinstance(r, dict)]
