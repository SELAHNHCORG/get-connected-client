"""Typer application for the ``galaxy`` command."""

from __future__ import annotations

import typer

import galaxy_digital_cli

from ..config import load_settings
from ._state import State
from .agencies import agencies_app
from .auth import auth_app
from .benchmarks import benchmarks_app
from .config_cmds import config_app
from .events import events_app
from .groups import groups_app
from .hours import hours_app
from .misc import (
    causes_app,
    clusters_app,
    impacts_app,
    interests_app,
    registration_questions_app,
)
from .needs import needs_app
from .qualifications import qualifications_app
from .responses import responses_app
from .teams import teams_app
from .users import users_app

app = typer.Typer(
    help="CLI for the Galaxy Digital Get Connected API.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)
app.add_typer(config_app, name="config")
app.add_typer(users_app, name="users")
app.add_typer(agencies_app, name="agencies")
app.add_typer(needs_app, name="needs")
app.add_typer(events_app, name="events")
app.add_typer(hours_app, name="hours")
app.add_typer(responses_app, name="responses")
app.add_typer(teams_app, name="teams")
app.add_typer(groups_app, name="groups")
app.add_typer(qualifications_app, name="qualifications")
app.add_typer(benchmarks_app, name="benchmarks")
app.add_typer(clusters_app, name="clusters")
app.add_typer(causes_app, name="causes")
app.add_typer(interests_app, name="interests")
app.add_typer(impacts_app, name="impacts")
app.add_typer(registration_questions_app, name="registration-questions")
app.add_typer(auth_app, name="auth")


def _version(value: bool) -> None:
    if value:
        typer.echo(galaxy_digital_cli.__version__)
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    api_key: str | None = typer.Option(
        None, "--api-key", help="API key (or GALAXY_API_KEY)."
    ),
    url: str | None = typer.Option(
        None, "--url", help="Server URL or alias us1/us2/ca."
    ),
    read_only: bool = typer.Option(False, "--read-only", help="Block all writes."),
    json_output: bool = typer.Option(False, "--json", help="Emit raw JSON."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip write confirmations."),
    debug: bool = typer.Option(False, "--debug", help="Show tracebacks."),
    version: bool = typer.Option(
        False, "--version", callback=_version, is_eager=True, help="Show the version."
    ),
) -> None:
    """Galaxy Digital API command line interface."""
    ctx.obj = State(
        settings=load_settings(api_key=api_key, url=url, read_only=read_only or None),
        json_output=json_output,
        assume_yes=yes,
        debug=debug,
    )
