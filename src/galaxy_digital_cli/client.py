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
    GalaxyHTTPError,
    MissingAPIKeyError,
    NotFoundError,
    ReadOnlyError,
)

_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
MAX_PER_PAGE = 150


def _unwrap(payload: Any) -> Any:
    """Strip the ``{"data": ...}`` envelope the API wraps every payload in."""
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


class GalaxyClient:
    """Entry point to the API.

    All requests funnel through :meth:`request`, which enforces read-only
    mode before anything reaches the network.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = US1,
        *,
        read_only: bool = False,
        timeout: float = 30.0,
        retries: int = 3,
    ):
        self.api_key = api_key or os.environ.get("GALAXY_API_KEY") or ""
        if not self.api_key:
            raise MissingAPIKeyError("No API key: pass api_key= or set GALAXY_API_KEY")
        self.base_url = resolve_url(base_url)
        self.read_only = read_only
        self.timeout = timeout
        self.retries = retries
        self._http: httpx.Client | None = None
        # Resource namespaces are attached here in later tasks, e.g.:
        # from .resources.users import Users
        # self.users = Users(self)

    @property
    def blocked(self) -> bool:
        """True when writes are forbidden, by constructor flag or env var.

        ``GALAXY_READ_ONLY`` being explicitly falsy never *unblocks* a client
        constructed with ``read_only=True`` -- the two are OR'd, never
        overridden.
        """
        return bool(self.read_only or env_read_only())

    def _guard(self, request: httpx.Request) -> None:
        """httpx event hook: last-ditch block of writes in read-only mode.

        :meth:`request` already refuses writes before touching the network;
        this catches anything that reaches ``self.http`` by another route
        (direct use of the ``http`` property, redirects). httpx invokes
        request hooks before handing the request to the transport, so no
        bytes leave the process.
        """
        if request.method.upper() in _WRITE_METHODS and self.blocked:
            raise ReadOnlyError(
                f"{request.method.upper()} {request.url} blocked: read-only mode is on"
            )

    @property
    def http(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Authorization": self.api_key,
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
    ) -> Any:
        """Perform a single request, the sole gateway to the network.

        Blocks writes in read-only mode *before* any I/O, retries 429/5xx
        with exponential backoff, and maps error statuses onto the
        :class:`~galaxy_digital_cli.exceptions.GalaxyHTTPError` hierarchy.
        """
        method = method.upper()
        if method in _WRITE_METHODS and self.blocked:
            raise ReadOnlyError(f"{method} {path} blocked: read-only mode is on")
        attempt = 0
        while True:
            response = self.http.request(method, path, params=params, json=json)
            retryable = response.status_code == 429 or response.status_code >= 500
            if retryable and attempt < self.retries:
                time.sleep(0.5 * 2**attempt)
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
        # return would make every full page look short and stop us early.
        size = min(int(base.pop("per_page", per_page)), MAX_PER_PAGE)
        base["per_page"] = size
        since_id = base.pop("since_id", None)
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
            ids = [
                int(r["id"])
                for r in rows
                if isinstance(r, dict) and r.get("id") is not None
            ]
            nxt = max(ids) if ids else None
            if since_id is not None and nxt is not None and nxt <= int(since_id):
                # Every row is at or behind the cursor we asked past, so the
                # server ignored since_id and replayed a page we already
                # yielded. Stop before emitting duplicates -- continuing would
                # loop forever against the API.
                return
            yield from rows
            if len(rows) < size:
                return
            if nxt is None:
                # A full page with no usable cursor: we cannot advance.
                return
            since_id = nxt
