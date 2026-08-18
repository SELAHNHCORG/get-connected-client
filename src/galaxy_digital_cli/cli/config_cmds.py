"""``galaxy config`` -- show the settings the CLI resolved for this run.

There is no configuration file to manage. Settings come from the global
flags (``--api-key``, ``--url``, ``--read-only``), then the environment
variables ``GALAXY_API_KEY``, ``GALAXY_API_URL`` and ``GALAXY_READ_ONLY``,
then the built-in defaults. This sub-app only reports what that chain
produced, so it is a diagnostic, not an editor.
"""

from __future__ import annotations

import os
from typing import Any

import typer

from ..config import env_read_only, load_settings
from ._output import output

config_app = typer.Typer(
    help=(
        "Inspect the resolved configuration "
        "(GALAXY_API_KEY, GALAXY_API_URL, GALAXY_READ_ONLY)."
    ),
    no_args_is_help=True,
)


def _redact(value: str | None) -> str:
    """Mask the API key so ``config show`` is safe to paste into a bug report."""
    if not value:
        return "(not set)"
    if len(value) <= 4:
        return "…redacted"
    return f"…{value[-4:]}"


def _source(var: str) -> str:
    """Report whether ``var`` supplied the value, or the default did."""
    return "env" if os.environ.get(var) else "default"


@config_app.command("show")
def show(ctx: typer.Context) -> None:
    """Show the resolved settings and where each one came from."""
    settings = load_settings()
    rows: list[dict[str, Any]] = [
        {
            "setting": "api_key",
            "value": _redact(settings.api_key),
            "source": _source("GALAXY_API_KEY"),
        },
        {
            "setting": "url",
            "value": settings.url,
            "source": _source("GALAXY_API_URL"),
        },
        {
            "setting": "read_only",
            "value": settings.read_only,
            "source": "env" if env_read_only() is not None else "default",
        },
    ]
    output(ctx.obj, rows, ["setting", "value", "source"], title="configuration")
