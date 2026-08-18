"""``galaxy qualifications`` -- the /qualifications endpoints on the command line.

Every command that changes anything on the server goes through
:func:`~galaxy_digital_cli.cli._confirm.confirm_write` first.

The paths shown in those prompts are built with the resource's own
:meth:`~galaxy_digital_cli.resources.base.Resource.url`, never hand-typed, so
what the operator is asked to approve is exactly what goes on the wire.
"""

from __future__ import annotations

from typing import Any

import typer

from ..client import MAX_PER_PAGE
from ._confirm import confirm_write
from ._output import output, output_one, output_result
from ._state import _merge_fields, get_state, handle_errors

qualifications_app = typer.Typer(help="Manage qualifications.", no_args_is_help=True)

#: Columns for the ``list`` table -- enough to identify a row and act on it.
LIST_COLUMNS = [
    "id",
    "qualification_title",
    "qualification_status",
    "qualification_type",
]

_ID = typer.Argument(..., help="ID of the qualification.")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@qualifications_app.command("list")
@handle_errors
def list_qualifications(
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
        help="Include inactive qualifications; omit for the server default.",
    ),
) -> None:
    """List qualifications, paging through every match."""
    state = get_state(ctx)
    rows = state.client.qualifications.list(
        per_page=per_page,
        since_id=since_id,
        since_created=since_created,
        since_updated=since_updated,
        show_inactive=show_inactive,
    )
    output(state, rows, LIST_COLUMNS, title="Qualifications")


@qualifications_app.command("get")
@handle_errors
def get_qualification(ctx: typer.Context, id: int = _ID) -> None:
    """Show one qualification."""
    state = get_state(ctx)
    output_one(state, state.client.qualifications.get(id))


def _qualification_fields(data: str | None, title: str | None) -> dict[str, Any]:
    """Map the friendly options onto the spec's ``qualification_*`` names."""
    return _merge_fields(data, qualification_title=title)


@qualifications_app.command("create")
@handle_errors
def create_qualification(
    ctx: typer.Context,
    title: str | None = typer.Option(None, "--title", help="Qualification title."),
    data: str | None = typer.Option(
        None,
        "--data",
        help=(
            "JSON object of any further fields, e.g. qualification_status, "
            "qualification_type, qualification_question."
        ),
    ),
) -> None:
    """Create a qualification."""
    state = get_state(ctx)
    fields = _qualification_fields(data, title)
    confirm_write(state, f"POST {state.client.qualifications.url()}", fields)
    output_result(state, state.client.qualifications.create(**fields))


@qualifications_app.command("update")
@handle_errors
def update_qualification(
    ctx: typer.Context,
    id: int = _ID,
    title: str | None = typer.Option(None, "--title", help="Qualification title."),
    data: str | None = typer.Option(
        None, "--data", help="JSON object of any further fields."
    ),
) -> None:
    """Update a qualification, sending only the fields you name."""
    state = get_state(ctx)
    fields = _qualification_fields(data, title)
    confirm_write(state, f"PUT {state.client.qualifications.url(id)}", fields)
    output_result(state, state.client.qualifications.update(id, **fields))


@qualifications_app.command("delete")
@handle_errors
def delete_qualification(ctx: typer.Context, id: int = _ID) -> None:
    """Delete a qualification (a soft delete: the record is marked inactive)."""
    state = get_state(ctx)
    confirm_write(state, f"DELETE {state.client.qualifications.url(id)}")
    state.client.qualifications.delete(id)
    output_result(state)


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------


@qualifications_app.command("users")
@handle_errors
def qualification_users(ctx: typer.Context, id: int = _ID) -> None:
    """List the users who hold a qualification."""
    state = get_state(ctx)
    output(
        state,
        state.client.qualifications.users(id),
        ["id", "user_fname", "user_lname", "status", "expires"],
        title="Qualification Users",
    )
