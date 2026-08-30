"""The credential-exchange namespace: ``/users/login`` and
``/users/authenticate`` -- the pair
:class:`~get_connected_cli.resources.users.Users` deliberately leaves out.
"""

from __future__ import annotations

from typing import Any

from ..exceptions import MissingAPIKeyError
from ..models.auth import LoginResult
from ..models.users import UserOneclick
from .base import Resource


class Auth(Resource[LoginResult]):
    """Credential exchange, covering the two paths ``Users`` excludes.

    2 of 2 paths, 2 of 2 operations, full coverage of the pair. Combined
    with :class:`~get_connected_cli.resources.users.Users`'s 21 of 23, the
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
        """Exchange credentials (and the site *key*) for a session token.

        The spec marks ``key`` required, and the API means it -- the body is
        validated before authentication, so a missing key is a 422 rather
        than a 401. ``None`` (the default) therefore falls back to the
        client's ``api_key``, which is what that key exists for.

        Prefer :meth:`~get_connected_cli.client.GalaxyClient.login`: it does
        the same exchange and then *adopts* the token, so subsequent
        requests authenticate. This method only returns it.

        :return: a :class:`~get_connected_cli.models.auth.LoginResult` when
            the API answers with a ``data`` object; otherwise the raw
            response payload, mirroring
            :meth:`~get_connected_cli.resources.base.CreateMixin.create`.
        :raises MissingAPIKeyError: no ``key`` was given and the client has
            no ``api_key`` to fall back on.
        """
        resolved_key = key or self._client.api_key
        if not resolved_key:
            raise MissingAPIKeyError(
                "login needs the site key: pass key= or set GALAXY_API_KEY"
            )
        payload = self._client.request(
            "POST",
            self._url("login"),
            json={
                "user_email": user_email,
                "user_password": user_password,
                "key": resolved_key,
            },
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict):
            return self._parse(data)
        return payload

    def authenticate(self, user_email: str, user_password: str) -> list[UserOneclick]:
        """Verify credentials and mint a one-click login link.

        The spec has ``data`` answer with an *array* of
        :class:`~get_connected_cli.models.users.UserOneclick` rows rather
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
