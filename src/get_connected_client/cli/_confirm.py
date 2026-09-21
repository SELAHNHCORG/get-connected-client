"""The interactive gates in front of every CLI write against production.

:func:`confirm_write` shows verbatim the body a command will send -- every
``create``, every ``delete``, and an ``update --replace``. :func:`confirm_patch`
is the merged-``update`` gate: the body on the wire is the whole record, so it
shows only the fields that change, and :func:`warn_missing_required` names the
required fields the merge could not supply.
"""

from __future__ import annotations

import json
from typing import Any

import typer
from rich.table import Table
from rich.text import Text

from ..resources.base import PatchPlan
from ._output import console, err_console


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


def _cell(value: Any) -> Text:
    """Render one table cell; user data goes through ``Text`` so a ``[`` in a
    value can never be read as rich markup."""
    if value is None:
        return Text("(none)", style="dim")
    if isinstance(value, str):
        return Text(value)
    return Text(json.dumps(value, default=str))


def warn_missing_required(plan: PatchPlan) -> None:
    """Say which required fields the merged body lacks, if any.

    Printed to stderr whether or not the prompt is shown, so ``--yes`` runs
    still hear about a PUT the API will almost certainly reject. It never
    blocks: the API is the authority and the vendored spec is imperfect.
    """
    if plan.missing_required:
        err_console.print(
            "[yellow]Warning:[/] the body lacks fields the API marks required: "
            + ", ".join(plan.missing_required)
            + " -- the write will likely be rejected (422). Pass them explicitly."
        )


def confirm_patch(state: Any, description: str, plan: PatchPlan) -> None:
    """Show only what a merged update changes and require consent.

    The payload on the wire is the whole record (see
    :meth:`~get_connected_client.resources.base.UpdateMixin.prepare_patch`);
    printing it would bury the two fields the operator typed under thirty
    they did not. So this lists the changed fields alone, current value
    beside new, and says the rest is carried over.

    Values are folded across as many lines as they take, never truncated:
    for the same reason :mod:`~get_connected_client.cli._output` never
    ellipsises a value the operator must see, nobody should approve a write
    whose value the prompt cut short.

    :raises typer.Abort: the operator declined.
    """
    warn_missing_required(plan)
    if state.assume_yes:
        return
    console.print(
        f"[bold red]About to write to the API:[/] {description} "
        "(merged over the current record)"
    )
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("field", overflow="fold")
    table.add_column("current", overflow="fold")
    table.add_column("new", overflow="fold")
    for change in plan.changes:
        table.add_row(change.field, _cell(change.old), _cell(change.new))
    console.print(table)
    if not typer.confirm("Proceed?"):
        raise typer.Abort()
