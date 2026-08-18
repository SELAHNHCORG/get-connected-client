"""``galaxy config`` -- inspect and edit the persisted TOML settings file."""

from __future__ import annotations

from typing import Any

import typer

from ..config import config_file, parse_bool, read_config, save_config
from ._output import console, output_one

#: The keys the config file understands, and how to coerce their values.
KEYS = ("api_key", "url", "read_only")

config_app = typer.Typer(
    help="Manage the persisted configuration file.",
    no_args_is_help=True,
)


def _coerce(key: str, value: str) -> Any:
    """Turn a command line string into the value stored for *key*."""
    if key == "read_only":
        return parse_bool(value)
    return value


def _redact(key: str, value: Any) -> Any:
    """Mask secrets so ``config show`` is safe to paste into a bug report."""
    if key == "api_key" and isinstance(value, str) and value:
        if len(value) <= 4:
            return "…redacted"
        return f"…{value[-4:]}"
    return value


@config_app.command("path")
def path() -> None:
    """Print the path of the configuration file."""
    # Deliberately not rendered through rich: a long path must not be wrapped.
    typer.echo(str(config_file()))


@config_app.command("show")
def show(ctx: typer.Context) -> None:
    """Show the stored configuration, with the API key redacted."""
    values = {key: _redact(key, value) for key, value in read_config().items()}
    if not values and not ctx.obj.json_output:
        console.print("[dim]no configuration set[/]")
        return
    output_one(ctx.obj, values)


@config_app.command("set")
def set_value(
    key: str = typer.Argument(..., help=f"One of: {', '.join(KEYS)}."),
    value: str = typer.Argument(..., help="The value to store."),
) -> None:
    """Set a configuration value, leaving the other keys untouched."""
    if key not in KEYS:
        raise typer.BadParameter(
            f"unknown key {key!r}, expected one of: {', '.join(KEYS)}"
        )
    current = read_config()
    current[key] = _coerce(key, value)
    typer.echo(f"set {key} in {save_config(current)}")


@config_app.command("unset")
def unset(
    key: str = typer.Argument(..., help=f"One of: {', '.join(KEYS)}."),
) -> None:
    """Remove a configuration value, leaving the other keys untouched."""
    current = read_config()
    if key not in current:
        typer.echo(f"{key} is not set")
        return
    current.pop(key)
    typer.echo(f"unset {key} in {save_config(current)}")
