"""Sync HTTP client for the Galaxy Digital Get Connected API."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:  # pragma: no cover - typing.Self is 3.11+, we support 3.10
    from typing_extensions import Self

from .config import US1, env_read_only, resolve_url
from .exceptions import (
    GalaxyConnectionError,
    GalaxyHTTPError,
    MissingAPIKeyError,
    NotFoundError,
    ReadOnlyError,
)
from .models.auth import LoginResult

_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
#: Methods whose repetition is harmless, so they may be retried after a 5xx or
#: a transport failure. POST/PATCH are absent on purpose: the server may have
#: committed the write before the failure, and a retry would duplicate it.
_IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})
MAX_PER_PAGE = 150
#: Ceiling on a server-supplied ``Retry-After`` pause, in seconds.
_MAX_RETRY_AFTER = 60.0


def _backoff(response: httpx.Response, attempt: int) -> float:
    """Seconds to wait before retrying *response*.

    A 429 carrying a parseable ``Retry-After`` wins -- the server told us
    when it will listen again -- clamped to :data:`_MAX_RETRY_AFTER` so a
    wild header cannot hang the process. Everything else backs off
    exponentially: 0.5s, 1s, 2s, ...
    """
    if response.status_code == 429:
        raw = response.headers.get("Retry-After", "")
        try:
            return max(0.0, min(float(raw.strip()), _MAX_RETRY_AFTER))
        except (AttributeError, ValueError):
            # Absent, an HTTP-date, or otherwise unparseable: fall through.
            pass
    return 0.5 * 2**attempt


def _bearer(value: str) -> str:
    """The ``Authorization`` header value for *value*.

    The API's scheme is ``Bearer``, so the credential is prefixed unless the
    caller already did it -- somebody who exported the whole header value
    (``GALAXY_API_TOKEN="Bearer eyJ..."``) should not end up sending
    ``Bearer Bearer eyJ...``.
    """
    return value if value.startswith("Bearer ") else f"Bearer {value}"


def _row_id(row: Any) -> int | None:
    """The integer ``id`` of a payload row, or None if it has no usable one."""
    if not isinstance(row, dict) or row.get("id") is None:
        return None
    try:
        return int(row["id"])
    except (TypeError, ValueError):
        return None


def _unwrap(payload: Any) -> Any:
    """Strip the ``{"data": ...}`` envelope the API wraps every payload in."""
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


class GalaxyClient:
    """Entry point to the API.

    All requests funnel through :meth:`request`, which enforces read-only
    mode before anything reaches the network.

    Two credentials, two jobs. The **site API key** (``api_key``, a UUID) is
    *not* an access credential: the API rejects it as an ``Authorization``
    value, raw or ``Bearer``-prefixed. Its only job is to identify the site
    in the body of :meth:`login`. What authenticates ordinary requests is
    the **session token** (``token``) that :meth:`login` returns -- a
    long-lived JWT (roughly a year) sent as ``Authorization: Bearer
    <token>``.

    A client built with only an ``api_key`` is therefore useful for exactly
    one thing: calling :meth:`login` to obtain a token. It is still allowed
    (and sends the key Bearer-prefixed, so nothing breaks for callers who
    have not migrated), but the server will answer 401 for anything else.

    ``retries`` counts *retries*, not attempts: ``retries=3`` means up to four
    requests (the original plus three), with exponential backoff of 0.5s, 1s
    and 2s between them -- roughly 3.5s of sleeping in the worst case. Only
    idempotent methods are retried on 5xx or transport failures; a 429 is
    retried for every method, since a rejected request was never processed.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = US1,
        *,
        token: str | None = None,
        read_only: bool = False,
        timeout: float = 30.0,
        retries: int = 3,
    ):
        """Construct a client.

        :param api_key: the site key, falling back to ``GALAXY_API_KEY``.
            Used as the ``key`` field of the :meth:`login` body.
        :param token: the session token, falling back to
            ``GALAXY_API_TOKEN``. This is what authenticates requests.
        :param retries: how many times to retry a retryable failure, so
            ``retries=3`` allows up to four attempts and ~3.5s of backoff.
        :raises MissingAPIKeyError: neither credential is available.
        """
        self.api_key = api_key or os.environ.get("GALAXY_API_KEY") or ""
        self.token = token or os.environ.get("GALAXY_API_TOKEN") or ""
        if not (self.api_key or self.token):
            raise MissingAPIKeyError(
                "No credentials: set GALAXY_API_TOKEN (from `galaxy auth login`) "
                "or GALAXY_API_KEY (the site key, which only logs in), or pass "
                "token=/api_key="
            )
        self.base_url = resolve_url(base_url)
        self._read_only = read_only
        self.timeout = timeout
        self.retries = retries
        self._http: httpx.Client | None = None
        # Resource namespaces. Imported here, not at module scope: they import
        # this module for MAX_PER_PAGE, so a top-level import would cycle.
        from .resources.agencies import Agencies
        from .resources.auth import Auth
        from .resources.benchmarks import Benchmarks
        from .resources.events import Events
        from .resources.groups import Groups
        from .resources.hours import Hours
        from .resources.misc import Clusters, Lookups
        from .resources.needs import Needs
        from .resources.qualifications import Qualifications
        from .resources.responses import Responses
        from .resources.teams import Teams
        from .resources.users import Users

        self.users = Users(self)
        self.agencies = Agencies(self)
        self.needs = Needs(self)
        self.events = Events(self)
        self.hours = Hours(self)
        self.responses = Responses(self)
        self.teams = Teams(self)
        self.groups = Groups(self)
        self.qualifications = Qualifications(self)
        self.benchmarks = Benchmarks(self)
        self.clusters = Clusters(self)
        self.lookups = Lookups(self)
        self.auth = Auth(self)

    @property
    def read_only(self) -> bool:
        """True when writes are forbidden, by constructor flag or the
        ``GALAXY_READ_ONLY`` env var.

        The two sources are OR'd, never overridden: ``GALAXY_READ_ONLY=0``
        does not *unblock* a client constructed with ``read_only=True``.
        """
        return bool(self._read_only or env_read_only())

    def _guard(self, request: httpx.Request) -> None:
        """httpx event hook: last-ditch block of writes in read-only mode.

        :meth:`request` already refuses writes before touching the network;
        this catches anything that reaches ``self.http`` by another route --
        direct use of the ``http`` property, and redirect hops, should
        ``follow_redirects`` ever be enabled (it defaults off). httpx invokes
        request hooks before handing the request to the transport, so no
        bytes leave the process.

        Side-effecting GETs -- the ``treat_as_write=True`` endpoints such as
        ``/users/{id}/welcomeEmail`` -- are enforced in :meth:`request` only,
        never here: the hook sees a bare :class:`httpx.Request` and cannot
        tell such a GET from an ordinary read.
        """
        if request.method.upper() in _WRITE_METHODS and self.read_only:
            raise ReadOnlyError(
                f"{request.method.upper()} {request.url} blocked: read-only mode is on"
            )

    @property
    def http(self) -> httpx.Client:
        """The underlying :class:`httpx.Client`, a supported escape hatch.

        Use it for anything :meth:`request` does not model (streaming, odd
        content types, raw responses). It carries the same auth headers and
        base URL, and writes issued through it are *still* refused in
        read-only mode by the :meth:`_guard` request hook -- but it does not
        retry, unwrap envelopes, or map statuses onto exceptions.

        Built lazily and cached, which is also how a fresh token takes
        effect: :meth:`login` drops the cached transport so the next access
        rebuilds it around the new credential.
        """
        if self._http is None:
            self._http = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Authorization": _bearer(self.token or self.api_key),
                    "Accept": "application/json",
                },
                event_hooks={"request": [self._guard]},
            )
        return self._http

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        treat_as_write: bool = False,
    ) -> Any:
        """Perform a single request, the sole gateway to the network.

        Blocks writes in read-only mode *before* any I/O, retries with
        exponential backoff (honoring ``Retry-After`` on a 429), and maps
        error statuses onto the
        :class:`~galaxy_digital_cli.exceptions.GalaxyHTTPError` hierarchy.

        A 429 is retried for every method -- the request was rejected, not
        processed. A 5xx or a transport failure is retried only for
        idempotent methods; a POST or PATCH raises on the first failure
        rather than risk duplicating a write the server may have committed.
        ``treat_as_write`` also disables those retries: the whole point of
        the flag is that the request is not really idempotent, so repeating
        it could send a second email (or mint a second artifact).

        :param treat_as_write: enforce the read-only guard for endpoints
            whose GET has side effects (e.g. /users/{id}/welcomeEmail), and
            suppress retries for them.
        :raises ReadOnlyError: a write was attempted in read-only mode.
        :raises GalaxyConnectionError: the request never completed.
        :raises GalaxyHTTPError: the API answered 4xx/5xx.
        """
        method = method.upper()
        if (method in _WRITE_METHODS or treat_as_write) and self.read_only:
            raise ReadOnlyError(f"{method} {path} blocked: read-only mode is on")
        # A treat_as_write GET is a write wearing a GET's clothes: replaying it
        # after a 5xx could send a second email, so it forfeits retries. A 429
        # is still retried below -- that request was rejected, never processed.
        retriable_failure = method in _IDEMPOTENT_METHODS and not treat_as_write
        attempt = 0
        while True:
            try:
                response = self.http.request(method, path, params=params, json=json)
            except httpx.TransportError as error:
                if retriable_failure and attempt < self.retries:
                    time.sleep(0.5 * 2**attempt)
                    attempt += 1
                    continue
                raise GalaxyConnectionError(
                    f"{method} {path} failed: {error}"
                ) from error
            status = response.status_code
            retryable = status == 429 or (status >= 500 and retriable_failure)
            if retryable and attempt < self.retries:
                time.sleep(_backoff(response, attempt))
                attempt += 1
                continue
            break
        if response.status_code >= 400:
            raise GalaxyHTTPError.for_status(response.status_code, response.text[:500])
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return None

    def login(
        self, user_email: str, user_password: str, key: str | None = None
    ) -> LoginResult | dict[str, Any] | None:
        """Exchange credentials for a session token and start using it.

        ``key`` defaults to :attr:`api_key` -- the site key's whole purpose.
        On success the returned token becomes this client's credential:
        :attr:`token` is replaced and the cached transport is dropped, so
        the next request is built with ``Authorization: Bearer <token>``.

        This is a POST, so it goes through :meth:`request` like any other
        write and is refused in read-only mode.

        :raises MissingAPIKeyError: no ``key`` was given and the client has
            no ``api_key`` to fall back on.
        """
        if not (key or self.api_key):
            raise MissingAPIKeyError(
                "login needs the site key: pass key= or set GALAXY_API_KEY"
            )
        result = self.auth.login(user_email, user_password, key=key or self.api_key)
        if isinstance(result, LoginResult) and result.token:
            self.token = result.token
            # Drop the cached transport: the next access to `http` rebuilds
            # it -- guard hook and all -- around the new credential.
            self.close()
        return result

    def get_data(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET ``path`` and return the unwrapped payload."""
        return _unwrap(self.request("GET", path, params=params))

    def paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        per_page: int = MAX_PER_PAGE,
    ) -> Iterator[dict[str, Any]]:
        """Iterate all rows of a list endpoint via per_page/since_id paging.

        The API answers 404 for "no results", so that ends iteration.
        """
        base = {k: v for k, v in (params or {}).items() if v is not None}
        # Clamp to the API maximum: asking for more than the server will ever
        # return would make every full page look short and stop us early. The
        # lower bound keeps a 0 or negative per_page from stalling us on an
        # endless run of "full" empty pages.
        size = max(1, min(int(base.pop("per_page", per_page)), MAX_PER_PAGE))
        base["per_page"] = size
        since_id = base.pop("since_id", None)
        if since_id is not None:
            since_id = int(since_id)
        while True:
            query = dict(base)
            if since_id is not None:
                query["since_id"] = since_id
            try:
                rows = _unwrap(self.request("GET", path, params=query))
            except NotFoundError:
                return
            if not rows:
                return
            if not isinstance(rows, list):
                rows = [rows]
            fetched = len(rows)
            ids = [i for i in (_row_id(r) for r in rows) if i is not None]
            nxt = max(ids) if ids else None
            if since_id is not None and nxt is not None and nxt <= since_id:
                # Every row is at or behind the cursor we asked past, so the
                # server ignored since_id and replayed a page we already
                # yielded. Stop before emitting duplicates -- continuing would
                # loop forever against the API.
                return
            if since_id is not None:
                # A page that partially overlaps the previous one (rows added
                # or removed underneath us) would otherwise re-yield rows we
                # already emitted.
                cursor = since_id
                rows = [r for r in rows if (rid := _row_id(r)) is None or rid > cursor]
            yield from rows
            # Shortness is judged on what the server sent, not on what
            # survived the overlap filter.
            if fetched < size:
                return
            if nxt is None:
                # A full page with no usable cursor: we cannot advance.
                return
            since_id = nxt
