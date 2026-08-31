"""``galaxy config`` -- show the settings the CLI resolved for this run.

There is no configuration file to manage. Settings come from the global
flags (``--api-key``, ``--token``, ``--url``, ``--read-only``), then the
environment variables ``GALAXY_API_KEY``, ``GALAXY_API_TOKEN``,
``GALAXY_API_URL`` and ``GALAXY_READ_ONLY``, then the built-in defaults.
This sub-app only reports what that chain produced, so it is a diagnostic,
not an editor.

The ``format`` row is the odd one out: ``--format`` / ``GALAXY_FORMAT``
picks a renderer and is never handed to the client, so it lives on the
state rather than in :class:`~get_connected_client.config.Settings`. It is
reported here anyway because an exported ``GALAXY_FORMAT`` is exactly the
kind of invisible environment setting this command exists to surface.
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
        "GALAXY_API_TOKEN, GALAXY_API_URL, GALAXY_READ_ONLY, "
        "GALAXY_FORMAT)."
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


def _source(flag_given: bool, env_set: bool) -> str:
    """Label where a setting's value came from: flag > env > default."""
    if flag_given:
        return "flag"
    if env_set:
        return "env"
    return "default"


@config_app.command("show")
def show(ctx: typer.Context) -> None:
    """Show the resolved settings and where each one came from."""
    state = get_state(ctx)
    settings = state.settings
    root_params = ctx.find_root().params

    rows: list[dict[str, Any]] = [
        {
            "setting": "api_key",
            "value": _redact(settings.api_key),
            "source": _source(
                root_params.get("api_key") is not None,
                bool(os.environ.get("GALAXY_API_KEY")),
            ),
        },
        {
            "setting": "token",
            "value": _redact(settings.token),
            "source": _source(
                root_params.get("token") is not None,
                bool(os.environ.get("GALAXY_API_TOKEN")),
            ),
        },
        {
            "setting": "url",
            "value": settings.url,
            "source": _source(
                root_params.get("url") is not None,
                bool(os.environ.get("GALAXY_API_URL")),
            ),
        },
        {
            "setting": "read_only",
            "value": settings.read_only,
            "source": _source(
                bool(root_params.get("read_only")),
                env_read_only() is not None,
            ),
        },
        {
            "setting": "format",
            "value": state.format.value,
            # The only row that is not a Settings field: the output format
            # never reaches the client, it only picks a renderer. Its env
            # var is resolved by click rather than load_settings, so the
            # flag half of the source has to come from the parameter
            # source -- root_params alone cannot tell --format json from
            # GALAXY_FORMAT=json. Both --format and its --json shorthand
            # count as flags.
            "source": _source(
                bool(root_params.get("json_output"))
                or getattr(
                    ctx.find_root().get_parameter_source("output_format"), "name", ""
                )
                == "COMMANDLINE",
                bool(os.environ.get("GALAXY_FORMAT")),
            ),
        },
    ]
    output(ctx.obj, rows, ["setting", "value", "source"], title="configuration")
