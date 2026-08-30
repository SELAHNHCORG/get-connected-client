"""``galaxy groups`` -- the /groups endpoints on the command line.

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

groups_app = typer.Typer(help="Manage groups.", no_args_is_help=True)

#: Columns for the ``list`` table -- enough to identify a row and act on it.
LIST_COLUMNS = ["id", "ug_title", "ug_status"]

_ID = typer.Argument(..., help="ID of the group.")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@groups_app.command("list")
@handle_errors
def list_groups(
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
        help="Include inactive groups; omit for the server default.",
    ),
) -> None:
    """List groups, paging through every match."""
    state = get_state(ctx)
    rows = state.client.groups.list(
        per_page=per_page,
        since_id=since_id,
        since_created=since_created,
        since_updated=since_updated,
        # Tri-state, passed through untouched: None omits the parameter and
        # takes the server default, True sends Yes, False sends No.
        show_inactive=show_inactive,
    )
    output(state, rows, LIST_COLUMNS, title="Groups")


@groups_app.command("get")
@handle_errors
def get_group(ctx: typer.Context, id: int = _ID) -> None:
    """Show one group."""
    state = get_state(ctx)
    output_one(state, state.client.groups.get(id))


def _group_fields(
    data: str | None, title: str | None, status: str | None
) -> dict[str, Any]:
    """Map the friendly options onto the spec's ``ug_*`` field names."""
    return _merge_fields(data, ug_title=title, ug_status=status)


@groups_app.command("create")
@handle_errors
def create_group(
    ctx: typer.Context,
    title: str | None = typer.Option(None, "--title", help="Group title."),
    status: str | None = typer.Option(
        None, "--status", help="active, pending or inactive."
    ),
    data: str | None = typer.Option(
        None, "--data", help="JSON object of any further ug_* fields, e.g. ug_type."
    ),
) -> None:
    """Create a group."""
    state = get_state(ctx)
    fields = _group_fields(data, title, status)
    confirm_write(state, f"POST {state.client.groups.url()}", fields)
    output_result(state, state.client.groups.create(**fields))


@groups_app.command("update")
@handle_errors
def update_group(
    ctx: typer.Context,
    id: int = _ID,
    title: str | None = typer.Option(None, "--title", help="Group title."),
    status: str | None = typer.Option(
        None, "--status", help="active, pending or inactive."
    ),
    data: str | None = typer.Option(
        None, "--data", help="JSON object of any further ug_* fields, e.g. ug_type."
    ),
) -> None:
    """Update a group, sending only the fields you name."""
    state = get_state(ctx)
    fields = _group_fields(data, title, status)
    confirm_write(state, f"PUT {state.client.groups.url(id)}", fields)
    output_result(state, state.client.groups.update(id, **fields))


@groups_app.command("delete")
@handle_errors
def delete_group(ctx: typer.Context, id: int = _ID) -> None:
    """Delete a group (a soft delete: the record is marked inactive)."""
    state = get_state(ctx)
    confirm_write(state, f"DELETE {state.client.groups.url(id)}")
    state.client.groups.delete(id)
    output_result(state)


# ---------------------------------------------------------------------------
# needs
# ---------------------------------------------------------------------------


@groups_app.command("add-need")
@handle_errors
def add_need(
    ctx: typer.Context,
    id: int = _ID,
    need_id: int = typer.Argument(..., help="ID of the need."),
) -> None:
    """Attach a need to a group."""
    state = get_state(ctx)
    confirm_write(state, f"POST {state.client.groups.url(id, 'needs', need_id)}")
    output_result(state, state.client.groups.add_need(id, need_id))


@groups_app.command("remove-need")
@handle_errors
def remove_need(
    ctx: typer.Context,
    id: int = _ID,
    need_id: int = typer.Argument(..., help="ID of the need."),
) -> None:
    """Detach a need from a group."""
    state = get_state(ctx)
    confirm_write(state, f"DELETE {state.client.groups.url(id, 'needs', need_id)}")
    output_result(state, state.client.groups.remove_need(id, need_id))


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------


@groups_app.command("add-user")
@handle_errors
def add_user(
    ctx: typer.Context,
    id: int = _ID,
    user_id: int = typer.Argument(..., help="ID of the user."),
) -> None:
    """Attach a user to a group."""
    state = get_state(ctx)
    confirm_write(state, f"POST {state.client.groups.url(id, 'users', user_id)}")
    output_result(state, state.client.groups.add_user(id, user_id))


@groups_app.command("remove-user")
@handle_errors
def remove_user(
    ctx: typer.Context,
    id: int = _ID,
    user_id: int = typer.Argument(..., help="ID of the user."),
) -> None:
    """Detach a user from a group."""
    state = get_state(ctx)
    confirm_write(state, f"DELETE {state.client.groups.url(id, 'users', user_id)}")
    output_result(state, state.client.groups.remove_user(id, user_id))
