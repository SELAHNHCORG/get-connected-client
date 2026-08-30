"""``galaxy teams`` -- the /teams endpoints on the command line.

Every command that changes anything on the server goes through
:func:`~get_connected_cli.cli._confirm.confirm_write` first.

The paths shown in those prompts are built with the resource's own
:meth:`~get_connected_cli.resources.base.Resource.url`, never hand-typed, so
what the operator is asked to approve is exactly what goes on the wire.

There is no ``update`` command: the API has no ``PUT /teams/{id}``.
"""

from __future__ import annotations

from typing import Any

import typer

from ..client import MAX_PER_PAGE
from ._confirm import confirm_write
from ._output import output, output_one, output_result
from ._state import _merge_fields, get_state, handle_errors

teams_app = typer.Typer(help="Manage teams.", no_args_is_help=True)

#: Columns for the ``list`` table -- enough to identify a row and act on it.
LIST_COLUMNS = ["id", "team_title", "team_status"]

_ID = typer.Argument(..., help="ID of the team.")
_MEMBER = typer.Argument(..., help="ID of the member (user).")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@teams_app.command("list")
@handle_errors
def list_teams(
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
        help="Include inactive teams; omit for the server default.",
    ),
) -> None:
    """List teams, paging through every match."""
    state = get_state(ctx)
    rows = state.client.teams.list(
        per_page=per_page,
        since_id=since_id,
        since_created=since_created,
        since_updated=since_updated,
        # Tri-state, passed through untouched: None omits the parameter and
        # takes the server default, True sends Yes, False sends No.
        show_inactive=show_inactive,
    )
    output(state, rows, LIST_COLUMNS, title="Teams")


@teams_app.command("get")
@handle_errors
def get_team(ctx: typer.Context, id: int = _ID) -> None:
    """Show one team."""
    state = get_state(ctx)
    output_one(state, state.client.teams.get(id))


def _team_fields(
    data: str | None, title: str | None, need_id: int | None
) -> dict[str, Any]:
    """Map the friendly options onto the spec's ``team_*``/``need_id`` names."""
    return _merge_fields(data, team_title=title, need_id=need_id)


@teams_app.command("create")
@handle_errors
def create_team(
    ctx: typer.Context,
    title: str | None = typer.Option(None, "--title", help="Team title."),
    need_id: int | None = typer.Option(
        None, "--need-id", help="ID of the need this team is responding to."
    ),
    data: str | None = typer.Option(
        None,
        "--data",
        help="JSON object of any further fields, e.g. team_status, sch_id, user_id.",
    ),
) -> None:
    """Create a team."""
    state = get_state(ctx)
    fields = _team_fields(data, title, need_id)
    confirm_write(state, f"POST {state.client.teams.url()}", fields)
    output_result(state, state.client.teams.create(**fields))


@teams_app.command("delete")
@handle_errors
def delete_team(ctx: typer.Context, id: int = _ID) -> None:
    """Delete a team (a soft delete: the record is marked inactive)."""
    state = get_state(ctx)
    confirm_write(state, f"DELETE {state.client.teams.url(id)}")
    state.client.teams.delete(id)
    output_result(state)


# ---------------------------------------------------------------------------
# members
# ---------------------------------------------------------------------------


@teams_app.command("add-member")
@handle_errors
def add_member(
    ctx: typer.Context,
    id: int = _ID,
    member: int = _MEMBER,
    sch_id: int | None = typer.Option(
        None, "--sch-id", help="Schedule ID for the member's shift."
    ),
) -> None:
    """Attach a member to a team."""
    state = get_state(ctx)
    fields = {} if sch_id is None else {"sch_id": sch_id}
    confirm_write(state, f"POST {state.client.teams.url(id, 'member', member)}", fields)
    output_result(state, state.client.teams.add_member(id, member, sch_id=sch_id))


@teams_app.command("remove-member")
@handle_errors
def remove_member(ctx: typer.Context, id: int = _ID, member: int = _MEMBER) -> None:
    """Detach a member from a team."""
    state = get_state(ctx)
    confirm_write(state, f"DELETE {state.client.teams.url(id, 'member', member)}")
    output_result(state, state.client.teams.remove_member(id, member))
