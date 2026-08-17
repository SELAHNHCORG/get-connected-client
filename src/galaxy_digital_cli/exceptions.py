"""Exception hierarchy for the Galaxy Digital API client."""

from __future__ import annotations


class GalaxyError(Exception):
    """Base for all errors raised by this library."""


class MissingAPIKeyError(GalaxyError):
    """No API key was provided or discoverable."""


class ReadOnlyError(GalaxyError):
    """A write was attempted while the client is in read-only mode."""


class GalaxyHTTPError(GalaxyError):
    """An HTTP-level error response from the API."""

    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(
            f"HTTP {status_code}: {detail}" if detail else f"HTTP {status_code}"
        )

    @classmethod
    def for_status(cls, status_code: int, detail: str = "") -> GalaxyHTTPError:
        klass = {
            401: AuthError,
            403: AuthError,
            404: NotFoundError,
            422: ValidationFailedError,
            429: RateLimitError,
        }.get(status_code, GalaxyHTTPError)
        return klass(status_code, detail)


class AuthError(GalaxyHTTPError):
    """401/403 — bad or missing credentials."""


class NotFoundError(GalaxyHTTPError):
    """404 — the API also uses this for empty list results."""


class ValidationFailedError(GalaxyHTTPError):
    """422 — the API rejected the payload."""


class RateLimitError(GalaxyHTTPError):
    """429 — too many requests."""
