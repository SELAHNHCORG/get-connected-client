"""``galaxy responses`` -- the /responses endpoints on the command line.

Every command that changes anything on the server goes through
:func:`~get_connected_client.cli._confirm.confirm_write` first.

The paths shown in those prompts are built with the resource's own
:meth:`~get_connected_client.resources.base.Resource.url`, never hand-typed, so
what the operator is asked to approve is exactly what goes on the wire.
"""

from __future__ import annotations

from typing import Any

import typer

from ..client import MAX_PER_PAGE
from ._confirm import confirm_write
from ._output import output, output_one, output_result
from ._state import _merge_fields, get_state, handle_errors

responses_app = typer.Typer(help="Manage responses.", no_args_is_help=True)

#: Columns for the ``list`` table -- enough to identify a row and act on it.
LIST_COLUMNS = ["id", "response_status", "response_date_added"]

_ID = typer.Argument(..., help="ID of the response.")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@responses_app.command("list")
@handle_errors
def list_responses(
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
        help="Include inactive responses; omit for the server default.",
    ),
) -> None:
    """List responses, paging through every match."""
    state = get_state(ctx)
    rows = state.client.responses.list(
        per_page=per_page,
        since_id=since_id,
        since_created=since_created,
        since_updated=since_updated,
        # Tri-state, passed through untouched: None omits the parameter and
        # takes the server default, True sends Yes, False sends No.
        show_inactive=show_inactive,
    )
    output(state, rows, LIST_COLUMNS, title="Responses")


@responses_app.command("get")
@handle_errors
def get_response(ctx: typer.Context, id: int = _ID) -> None:
    """Show one response."""
    state = get_state(ctx)
    output_one(state, state.client.responses.get(id))


def _response_fields(
    data: str | None,
    need_id: int | None,
    user_id: int | None,
    team_id: int | None,
    note: str | None,
) -> dict[str, Any]:
    """Map the friendly options onto the spec's ``responseRequestSchema`` names."""
    return _merge_fields(
        data,
        need_id=need_id,
        user_id=user_id,
        team_id=team_id,
        response_note=note,
    )


@responses_app.command("create")
@handle_errors
def create_response(
    ctx: typer.Context,
    need_id: int | None = typer.Option(
        None, "--need-id", help="ID of the need being responded to."
    ),
    user_id: int | None = typer.Option(
        None, "--user-id", help="ID of the responding user."
    ),
    team_id: int | None = typer.Option(
        None, "--team-id", help="ID of the team the response belongs to."
    ),
    note: str | None = typer.Option(None, "--note", help="Note from the responder."),
    data: str | None = typer.Option(
        None,
        "--data",
        help="JSON object of any further fields, e.g. schedule_ids, questions.",
    ),
) -> None:
    """Create a response."""
    state = get_state(ctx)
    fields = _response_fields(data, need_id, user_id, team_id, note)
    confirm_write(state, f"POST {state.client.responses.url()}", fields)
    output_result(state, state.client.responses.create(**fields))


@responses_app.command("update")
@handle_errors
def update_response(
    ctx: typer.Context,
    id: int = _ID,
    need_id: int | None = typer.Option(
        None, "--need-id", help="ID of the need being responded to."
    ),
    user_id: int | None = typer.Option(
        None, "--user-id", help="ID of the responding user."
    ),
    team_id: int | None = typer.Option(
        None, "--team-id", help="ID of the team the response belongs to."
    ),
    note: str | None = typer.Option(None, "--note", help="Note from the responder."),
    data: str | None = typer.Option(
        None,
        "--data",
        help="JSON object of any further fields, e.g. schedule_ids, questions.",
    ),
) -> None:
    """Update a response, sending only the fields you name."""
    state = get_state(ctx)
    fields = _response_fields(data, need_id, user_id, team_id, note)
    confirm_write(state, f"PUT {state.client.responses.url(id)}", fields)
    output_result(state, state.client.responses.update(id, **fields))


@responses_app.command("delete")
@handle_errors
def delete_response(ctx: typer.Context, id: int = _ID) -> None:
    """Delete a response (a soft delete: the record is marked inactive)."""
    state = get_state(ctx)
    confirm_write(state, f"DELETE {state.client.responses.url(id)}")
    state.client.responses.delete(id)
    output_result(state)
