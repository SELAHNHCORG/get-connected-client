"""Interactive gate in front of every CLI write against production."""

from __future__ import annotations

import json
from typing import Any

import typer

from ._output import console


def confirm_write(state: Any, description: str, payload: Any = None) -> None:
    """Show what is about to be written and require consent (unless ``--yes``).

    :raises typer.Abort: the operator declined.
    """
    if state.assume_yes:
        return
    console.print(f"[bold red]About to write to the API:[/] {description}")
    if payload is not None:
        console.print_json(json.dumps(payload, default=str))
    if not typer.confirm("Proceed?"):
        raise typer.Abort()
