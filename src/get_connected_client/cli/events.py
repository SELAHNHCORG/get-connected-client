"""``galaxy events`` -- the /events endpoints on the command line.

Every command that changes anything on the server goes through
:func:`~get_connected_client.cli._confirm.confirm_write` first.

The paths shown in those prompts are built with the resource's own
:meth:`~get_connected_client.resources.base.Resource.url`, never hand-typed, so
what the operator is asked to approve is exactly what goes on the wire.

.. note::
   Unlike ``needs``, ``agencies`` and ``hours``, ``/events`` does not accept
   ``show_inactive`` on its list endpoint (see
   :class:`~get_connected_client.resources.events.Events`), so ``list`` here
   does not offer ``--show-inactive``.
"""

from __future__ import annotations

from typing import Any

import typer

from ..client import MAX_PER_PAGE
from ._confirm import confirm_write
from ._output import output, output_one, output_result
from ._state import _merge_fields, get_state, handle_errors

events_app = typer.Typer(help="Manage events.", no_args_is_help=True)

#: Columns for the ``list`` table -- enough to identify a row and act on it.
LIST_COLUMNS = ["id", "event_title", "event_date_start", "event_location"]

_ID = typer.Argument(..., help="ID of the event.")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@events_app.command("list")
@handle_errors
def list_events(
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
) -> None:
    """List events, paging through every match.

    The spec's ``/events`` list endpoint has no ``show_inactive`` parameter,
    so unlike other ``list`` commands this one does not offer it.
    """
    state = get_state(ctx)
    rows = state.client.events.list(
        per_page=per_page,
        since_id=since_id,
        since_created=since_created,
        since_updated=since_updated,
    )
    output(state, rows, LIST_COLUMNS, title="Events")


@events_app.command("get")
@handle_errors
def get_event(ctx: typer.Context, id: int = _ID) -> None:
    """Show one event."""
    state = get_state(ctx)
    output_one(state, state.client.events.get(id))


def _event_fields(
    data: str | None, title: str | None, description: str | None
) -> dict[str, Any]:
    """Map the friendly options onto the spec's ``event_*`` field names."""
    return _merge_fields(data, event_title=title, event_description=description)


@events_app.command("create")
@handle_errors
def create_event(
    ctx: typer.Context,
    title: str | None = typer.Option(None, "--title", help="Event title."),
    description: str | None = typer.Option(
        None, "--description", help="Event description."
    ),
    data: str | None = typer.Option(
        None, "--data", help="JSON object of any further event_* fields."
    ),
) -> None:
    """Create an event.

    ``event_area``, ``event_area_id`` and ``event_date_start`` are required
    by the API but have no dedicated option -- pass them via ``--data``,
    e.g. ``--data '{"event_area":"agency","event_area_id":9,
    "event_date_start":"2024-03-01 08:00:00"}'``.
    """
    state = get_state(ctx)
    fields = _event_fields(data, title, description)
    confirm_write(state, f"POST {state.client.events.url()}", fields)
    output_result(state, state.client.events.create(**fields))


@events_app.command("update")
@handle_errors
def update_event(
    ctx: typer.Context,
    id: int = _ID,
    title: str | None = typer.Option(None, "--title", help="Event title."),
    description: str | None = typer.Option(
        None, "--description", help="Event description."
    ),
    data: str | None = typer.Option(
        None, "--data", help="JSON object of any further event_* fields."
    ),
) -> None:
    """Update an event, sending only the fields you name."""
    state = get_state(ctx)
    fields = _event_fields(data, title, description)
    confirm_write(state, f"PUT {state.client.events.url(id)}", fields)
    output_result(state, state.client.events.update(id, **fields))


@events_app.command("delete")
@handle_errors
def delete_event(ctx: typer.Context, id: int = _ID) -> None:
    """Delete an event (a soft delete: the record is marked inactive)."""
    state = get_state(ctx)
    confirm_write(state, f"DELETE {state.client.events.url(id)}")
    state.client.events.delete(id)
    output_result(state)
