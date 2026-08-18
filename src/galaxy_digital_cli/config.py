"""Settings resolution: explicit args > env vars > defaults.

There is no configuration file. Anything the CLI does not receive as an
explicit flag comes from ``GALAXY_API_KEY``, ``GALAXY_API_TOKEN``,
``GALAXY_API_URL`` or ``GALAXY_READ_ONLY``, and failing those from the
built-in defaults (server ``us1``, read-only off, no credentials).

The two credentials are not interchangeable: ``GALAXY_API_KEY`` is the site
key, which only ever identifies the site in a login body, while
``GALAXY_API_TOKEN`` is the session token ``galaxy auth login`` mints and
the only thing that authenticates a request.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

US1 = "https://api.galaxydigital.com/api"
SERVERS = {
    "us1": US1,
    "us2": "https://www.volunteerapi.com/api",
    "ca": "https://ca.volunteerapi.com/api",
}

_TRUTHY = {"1", "true", "yes", "on"}


def parse_bool(value: str) -> bool:
    """Coerce a string to a boolean by membership in the truthy set."""
    return value.strip().lower() in _TRUTHY


def env_read_only() -> bool | None:
    """Read the GALAXY_READ_ONLY env var as a tri-state boolean."""
    raw = os.environ.get("GALAXY_READ_ONLY")
    if raw is None or raw.strip() == "":
        return None
    return parse_bool(raw)


def resolve_url(url: str) -> str:
    """Resolve a server alias (us1/us2/ca) to its full URL, or pass through."""
    return SERVERS.get(url.strip().lower(), url).rstrip("/")


@dataclass
class Settings:
    """Resolved settings for the Galaxy Digital API client.

    ``token`` defaults to None so callers constructing a ``Settings``
    positionally keep working; it is the session credential, ``api_key`` the
    site key used to log in.
    """

    api_key: str | None
    url: str
    read_only: bool
    token: str | None = None


def load_settings(
    api_key: str | None = None,
    url: str | None = None,
    read_only: bool | None = None,
    token: str | None = None,
) -> Settings:
    """Resolve settings with precedence: explicit args > env vars > defaults.

    ``token`` resolves from the argument, then ``GALAXY_API_TOKEN``, then
    None -- the same shape as ``api_key`` and ``GALAXY_API_KEY``.
    """
    resolved_key = api_key or os.environ.get("GALAXY_API_KEY")
    resolved_token = token or os.environ.get("GALAXY_API_TOKEN")
    resolved_url = url or os.environ.get("GALAXY_API_URL") or US1
    if read_only is None:
        read_only = env_read_only()
    if read_only is None:
        read_only = False
    return Settings(
        api_key=resolved_key or None,
        url=resolve_url(resolved_url),
        read_only=read_only,
        token=resolved_token or None,
    )
