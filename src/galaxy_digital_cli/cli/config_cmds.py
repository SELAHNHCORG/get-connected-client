"""``galaxy config`` -- show the settings the CLI resolved for this run.

There is no configuration file to manage. Settings come from the global
flags (``--api-key``, ``--token``, ``--url``, ``--read-only``), then the
environment variables ``GALAXY_API_KEY``, ``GALAXY_API_TOKEN``,
``GALAXY_API_URL`` and ``GALAXY_READ_ONLY``, then the built-in defaults.
This sub-app only reports what that chain produced, so it is a diagnostic,
not an editor.
"""

from __future__ import annotations

import os
from typing import Any

import typer

from ..config import env_read_only
from ._output import output
from ._state import get_state

config_app = typer.Typer(
    help=(
        "Inspect the resolved configuration (GALAXY_API_KEY, "
        "GALAXY_API_TOKEN, GALAXY_API_URL, GALAXY_READ_ONLY)."
    ),
    no_args_is_help=True,
)


def _redact(value: str | None) -> str:
    """Mask a credential so ``config show`` is safe to paste into a bug report."""
    if not value:
        return "(not set)"
    if len(value) <= 4:
        return "…redacted"
    return f"…{value[-4:]}"


@config_app.command("show")
def show(ctx: typer.Context) -> None:
    """Show the resolved settings and where each one came from."""
    settings = get_state(ctx).settings
    root_params = ctx.find_root().params

    if root_params.get("api_key") is not None:
        api_key_source = "flag"
    elif os.environ.get("GALAXY_API_KEY"):
        api_key_source = "env"
    else:
        api_key_source = "default"

    if root_params.get("token") is not None:
        token_source = "flag"
    elif os.environ.get("GALAXY_API_TOKEN"):
        token_source = "env"
    else:
        token_source = "default"

    if root_params.get("url") is not None:
        url_source = "flag"
    elif os.environ.get("GALAXY_API_URL"):
        url_source = "env"
    else:
        url_source = "default"

    if root_params.get("read_only"):
        read_only_source = "flag"
    elif env_read_only() is not None:
        read_only_source = "env"
    else:
        read_only_source = "default"

    rows: list[dict[str, Any]] = [
        {
            "setting": "api_key",
            "value": _redact(settings.api_key),
            "source": api_key_source,
        },
        {
            "setting": "token",
            "value": _redact(settings.token),
            "source": token_source,
        },
        {
            "setting": "url",
            "value": settings.url,
            "source": url_source,
        },
        {
            "setting": "read_only",
            "value": settings.read_only,
            "source": read_only_source,
        },
    ]
    output(ctx.obj, rows, ["setting", "value", "source"], title="configuration")
