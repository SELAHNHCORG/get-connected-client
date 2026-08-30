"""Per-invocation CLI state built by the root callback."""

from __future__ import annotations

import functools
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, TypeVar

import typer
from pydantic import ValidationError

from ..client import GalaxyClient
from ..config import Settings
from ..exceptions import GalaxyError
from ._output import OutputFormat, err_console

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class State:
    """Everything a command needs: resolved settings plus the global flags."""

    settings: Settings
    format: OutputFormat = OutputFormat.TABLE
    assume_yes: bool = False
    debug: bool = False
    _client: GalaxyClient | None = field(default=None, repr=False)

    @property
    def client(self) -> GalaxyClient:
        """The API client, constructed on first use.

        Building it lazily keeps commands that never touch the network --
        ``--help``, ``config`` -- working without any credentials.
        """
        if self._client is None:
            self._client = GalaxyClient(
                api_key=self.settings.api_key,
                base_url=self.settings.url,
                token=self.settings.token,
                read_only=self.settings.read_only,
            )
        return self._client


@functools.lru_cache(maxsize=1)
def _current_context_getter() -> Callable[..., Any] | None:
    """Locate click's ``get_current_context``.

    Recent typer vendors click as ``typer._click``; older releases depend on
    the standalone package. Try both so this works either way.
    """
    for module in ("typer._click.globals", "click.globals"):
        try:
            return import_module(module).get_current_context
        except ImportError:  # pragma: no cover - depends on installed typer
            continue
    return None  # pragma: no cover - neither layout available


def click_current_context_or_none() -> Any:
    """The click context of the running command, or None outside a CLI run."""
    getter = _current_context_getter()
    if getter is None:  # pragma: no cover - neither layout available
        return None
    return getter(silent=True)


def get_state(ctx: typer.Context) -> State:
    """The per-invocation state the root callback stashed on the context."""
    return ctx.obj


def handle_errors(fn: F) -> F:
    """Decorator for CLI commands: expected errors -> stderr message + exit 1.

    Catches :class:`~get_connected_cli.exceptions.GalaxyError` and pydantic's
    :class:`~pydantic.ValidationError` -- an API payload that does not match
    our models is the server's problem, not a bug worth a traceback.

    Re-raises the original exception when ``--debug`` was passed so typer
    prints the full traceback, for both error kinds.
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except (GalaxyError, ValidationError) as error:
            ctx = click_current_context_or_none()
            if ctx is not None and getattr(ctx.obj, "debug", False):
                raise
            err_console.print(f"[red]error:[/] {error}")
            raise typer.Exit(code=1) from error

    return wrapper  # type: ignore[return-value]


def _merge_fields(data: str | None = None, **options: Any) -> dict[str, Any]:
    """Merge a raw JSON ``--data`` object over explicit options.

    Options left unset (None) are dropped, so only what the operator actually
    asked for is sent; keys in ``data`` win over the named options.

    :raises typer.BadParameter: ``data`` is not a JSON object.
    """
    fields: dict[str, Any] = {k: v for k, v in options.items() if v is not None}
    if not data:
        return fields
    try:
        extra = json.loads(data)
    except ValueError as error:
        raise typer.BadParameter(f"--data is not valid JSON: {error}") from error
    if not isinstance(extra, dict):
        raise typer.BadParameter("--data must be a JSON object")
    fields.update(extra)
    return fields
