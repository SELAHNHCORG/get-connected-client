"""``galaxy hours`` -- the /hours endpoints on the command line.

Every command that changes anything on the server goes through
:func:`~get_connected_cli.cli._confirm.confirm_write` first.

The paths shown in those prompts are built with the resource's own
:meth:`~get_connected_cli.resources.base.Resource.url`, never hand-typed, so
what the operator is asked to approve is exactly what goes on the wire.
"""

from __future__ import annotations

from typing import Any

import typer

from ..client import MAX_PER_PAGE
from ._confirm import confirm_write
from ._output import output, output_one, output_result
from ._state import _merge_fields, get_state, handle_errors

hours_app = typer.Typer(help="Manage hours.", no_args_is_help=True)

#: Columns for the ``list`` table -- enough to identify a row and act on it.
LIST_COLUMNS = ["id", "hour_hours", "hour_date_start", "hour_status"]

_ID = typer.Argument(..., help="ID of the hour record.")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@hours_app.command("list")
@handle_errors
def list_hours(
    ctx: typer.Context,
    per_page: int = typer.Option(
        MAX_PER_PAGE, "--per-page", max=MAX_PER_PAGE, min=1, help="Rows per request."
    ),
    since_id: int | None = typer.Option(
        None, "--since-id", help="Only ids above this."
    ),
    since_created: str | None = typer.Option(
        None, "--since-created", help="Created since 'YYYY-MM-DD HH:MM'."
    ),
    since_updated: str | None = typer.Option(
        None, "--since-updated", help="Updated since 'YYYY-MM-DD HH:MM'."
    ),
    show_inactive: bool | None = typer.Option(
        None,
        "--show-inactive/--no-show-inactive",
        help="Include inactive hour records; omit for the server default.",
    ),
) -> None:
    """List hour records, paging through every match."""
    state = get_state(ctx)
    rows = state.client.hours.list(
        per_page=per_page,
        since_id=since_id,
        since_created=since_created,
        since_updated=since_updated,
        # Tri-state, passed through untouched: None omits the parameter and
        # takes the server default, True sends Yes, False sends No.
        show_inactive=show_inactive,
    )
    output(state, rows, LIST_COLUMNS, title="Hours")


@hours_app.command("get")
@handle_errors
def get_hour(ctx: typer.Context, id: int = _ID) -> None:
    """Show one hour record."""
    state = get_state(ctx)
    output_one(state, state.client.hours.get(id))


def _hour_fields(
    data: str | None,
    user_id: int | None,
    response_id: int | None,
    hours: str | None,
    miles: str | None,
    start: str | None,
    status: str | None,
) -> dict[str, Any]:
    """Map the friendly options onto the spec's ``hour_*``/``*_id`` field names."""
    return _merge_fields(
        data,
        user_id=user_id,
        response_id=response_id,
        hour_hours=hours,
        hour_miles=miles,
        hour_start=start,
        hour_status=status,
    )


@hours_app.command("create")
@handle_errors
def create_hour(
    ctx: typer.Context,
    user_id: int | None = typer.Option(
        None, "--user-id", help="ID of the user the hours belong to."
    ),
    response_id: int | None = typer.Option(
        None, "--response-id", help="ID of the need response these hours are for."
    ),
    hours: str | None = typer.Option(None, "--hours", help="Number of hours."),
    miles: str | None = typer.Option(None, "--miles", help="Number of miles."),
    start: str | None = typer.Option(
        None, "--start", help="Start datetime, e.g. '2024-03-01 08:00:00'."
    ),
    status: str | None = typer.Option(
        None,
        "--status",
        help="approved, inactive, pending, denied or entered.",
    ),
    data: str | None = typer.Option(
        None, "--data", help="JSON object of any further hour_* fields."
    ),
) -> None:
    """Create an hour record."""
    state = get_state(ctx)
    fields = _hour_fields(data, user_id, response_id, hours, miles, start, status)
    confirm_write(state, f"POST {state.client.hours.url()}", fields)
    output_result(state, state.client.hours.create(**fields))


@hours_app.command("update")
@handle_errors
def update_hour(
    ctx: typer.Context,
    id: int = _ID,
    user_id: int | None = typer.Option(
        None, "--user-id", help="ID of the user the hours belong to."
    ),
    response_id: int | None = typer.Option(
        None, "--response-id", help="ID of the need response these hours are for."
    ),
    hours: str | None = typer.Option(None, "--hours", help="Number of hours."),
    miles: str | None = typer.Option(None, "--miles", help="Number of miles."),
    start: str | None = typer.Option(
        None, "--start", help="Start datetime, e.g. '2024-03-01 08:00:00'."
    ),
    status: str | None = typer.Option(
        None,
        "--status",
        help="approved, inactive, pending, denied or entered.",
    ),
    data: str | None = typer.Option(
        None, "--data", help="JSON object of any further hour_* fields."
    ),
) -> None:
    """Update an hour record, sending only the fields you name."""
    state = get_state(ctx)
    fields = _hour_fields(data, user_id, response_id, hours, miles, start, status)
    confirm_write(state, f"PUT {state.client.hours.url(id)}", fields)
    output_result(state, state.client.hours.update(id, **fields))


@hours_app.command("delete")
@handle_errors
def delete_hour(ctx: typer.Context, id: int = _ID) -> None:
    """Delete an hour record (a soft delete: the record is marked inactive)."""
    state = get_state(ctx)
    confirm_write(state, f"DELETE {state.client.hours.url(id)}")
    state.client.hours.delete(id)
    output_result(state)
