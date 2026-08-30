"""``galaxy agencies`` -- the /agencies endpoints on the command line.

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

agencies_app = typer.Typer(help="Manage agencies.", no_args_is_help=True)

#: Columns for the ``list`` table -- enough to identify a row and act on it.
LIST_COLUMNS = ["id", "agency_name", "agency_city", "agency_state"]
NAMED_COLUMNS = ["id", "name"]

_ID = typer.Argument(..., help="ID of the agency.")
_TAG_NAMES = typer.Argument(..., help="Tag names to add.")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@agencies_app.command("list")
@handle_errors
def list_agencies(
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
        help="Include inactive agencies; omit for the server default.",
    ),
) -> None:
    """List agencies, paging through every match."""
    state = get_state(ctx)
    rows = state.client.agencies.list(
        per_page=per_page,
        since_id=since_id,
        since_created=since_created,
        since_updated=since_updated,
        # Tri-state, passed through untouched: None omits the parameter and
        # takes the server default, True sends Yes, False sends No.
        show_inactive=show_inactive,
    )
    output(state, rows, LIST_COLUMNS, title="Agencies")


@agencies_app.command("get")
@handle_errors
def get_agency(ctx: typer.Context, id: int = _ID) -> None:
    """Show one agency."""
    state = get_state(ctx)
    output_one(state, state.client.agencies.get(id))


def _agency_fields(data: str | None, name: str | None) -> dict[str, Any]:
    """Map the friendly options onto the spec's ``agency_*`` field names."""
    return _merge_fields(data, agency_name=name)


@agencies_app.command("create")
@handle_errors
def create_agency(
    ctx: typer.Context,
    name: str | None = typer.Option(None, "--name", help="Agency name."),
    data: str | None = typer.Option(
        None, "--data", help="JSON object of any further agency_* fields."
    ),
) -> None:
    """Create an agency."""
    state = get_state(ctx)
    fields = _agency_fields(data, name)
    confirm_write(state, f"POST {state.client.agencies.url()}", fields)
    output_result(state, state.client.agencies.create(**fields))


@agencies_app.command("update")
@handle_errors
def update_agency(
    ctx: typer.Context,
    id: int = _ID,
    name: str | None = typer.Option(None, "--name", help="Agency name."),
    data: str | None = typer.Option(
        None, "--data", help="JSON object of any further agency_* fields."
    ),
) -> None:
    """Update an agency, sending only the fields you name."""
    state = get_state(ctx)
    fields = _agency_fields(data, name)
    confirm_write(state, f"PUT {state.client.agencies.url(id)}", fields)
    output_result(state, state.client.agencies.update(id, **fields))


@agencies_app.command("delete")
@handle_errors
def delete_agency(ctx: typer.Context, id: int = _ID) -> None:
    """Delete an agency (a soft delete: the record is marked inactive)."""
    state = get_state(ctx)
    confirm_write(state, f"DELETE {state.client.agencies.url(id)}")
    state.client.agencies.delete(id)
    output_result(state)


# ---------------------------------------------------------------------------
# causes
# ---------------------------------------------------------------------------


@agencies_app.command("causes")
@handle_errors
def causes(ctx: typer.Context, id: int = _ID) -> None:
    """List the causes attached to an agency."""
    state = get_state(ctx)
    output(state, state.client.agencies.causes(id), NAMED_COLUMNS)


@agencies_app.command("add-cause")
@handle_errors
def add_cause(
    ctx: typer.Context,
    id: int = _ID,
    cause_id: int = typer.Argument(..., help="ID of the cause."),
) -> None:
    """Attach a cause to an agency."""
    state = get_state(ctx)
    confirm_write(state, f"POST {state.client.agencies.url(id, 'causes', cause_id)}")
    output_result(state, state.client.agencies.add_cause(id, cause_id))


@agencies_app.command("remove-cause")
@handle_errors
def remove_cause(
    ctx: typer.Context,
    id: int = _ID,
    cause_id: int = typer.Argument(..., help="ID of the cause."),
) -> None:
    """Detach a cause from an agency."""
    state = get_state(ctx)
    confirm_write(state, f"DELETE {state.client.agencies.url(id, 'causes', cause_id)}")
    output_result(state, state.client.agencies.remove_cause(id, cause_id))


# ---------------------------------------------------------------------------
# clusters
# ---------------------------------------------------------------------------


@agencies_app.command("clusters")
@handle_errors
def clusters(ctx: typer.Context, id: int = _ID) -> None:
    """List the clusters attached to an agency."""
    state = get_state(ctx)
    output(state, state.client.agencies.clusters(id), NAMED_COLUMNS)


@agencies_app.command("add-cluster")
@handle_errors
def add_cluster(
    ctx: typer.Context,
    id: int = _ID,
    cluster_id: int = typer.Argument(..., help="ID of the cluster."),
) -> None:
    """Attach a cluster to an agency."""
    state = get_state(ctx)
    confirm_write(
        state, f"POST {state.client.agencies.url(id, 'clusters', cluster_id)}"
    )
    output_result(state, state.client.agencies.add_cluster(id, cluster_id))


@agencies_app.command("remove-cluster")
@handle_errors
def remove_cluster(
    ctx: typer.Context,
    id: int = _ID,
    cluster_id: int = typer.Argument(..., help="ID of the cluster."),
) -> None:
    """Detach a cluster from an agency."""
    state = get_state(ctx)
    confirm_write(
        state, f"DELETE {state.client.agencies.url(id, 'clusters', cluster_id)}"
    )
    output_result(state, state.client.agencies.remove_cluster(id, cluster_id))


# ---------------------------------------------------------------------------
# managers
# ---------------------------------------------------------------------------


@agencies_app.command("managers")
@handle_errors
def managers(ctx: typer.Context, id: int = _ID) -> None:
    """List the users who manage an agency."""
    state = get_state(ctx)
    output(
        state,
        state.client.agencies.managers(id),
        ["id", "user_fname", "user_lname", "user_email"],
    )


@agencies_app.command("add-manager")
@handle_errors
def add_manager(
    ctx: typer.Context,
    id: int = _ID,
    user_id: int = typer.Argument(..., help="ID of the user."),
) -> None:
    """Make a user a manager of an agency."""
    state = get_state(ctx)
    confirm_write(state, f"POST {state.client.agencies.url(id, 'managers', user_id)}")
    output_result(state, state.client.agencies.add_manager(id, user_id))


@agencies_app.command("remove-manager")
@handle_errors
def remove_manager(
    ctx: typer.Context,
    id: int = _ID,
    user_id: int = typer.Argument(..., help="ID of the user."),
) -> None:
    """Remove a user as a manager of an agency."""
    state = get_state(ctx)
    confirm_write(state, f"DELETE {state.client.agencies.url(id, 'managers', user_id)}")
    output_result(state, state.client.agencies.remove_manager(id, user_id))


# ---------------------------------------------------------------------------
# tags
# ---------------------------------------------------------------------------


@agencies_app.command("tags")
@handle_errors
def tags(ctx: typer.Context, id: int = _ID) -> None:
    """List an agency's tags."""
    state = get_state(ctx)
    output(state, state.client.agencies.tags(id), NAMED_COLUMNS)


@agencies_app.command("add-tags")
@handle_errors
def add_tags(
    ctx: typer.Context,
    id: int = _ID,
    tags: list[str] = _TAG_NAMES,
) -> None:
    """Add one or more tags -- by name, not id -- to an agency."""
    state = get_state(ctx)
    confirm_write(
        state, f"POST {state.client.agencies.url(id, 'tags')}", {"tags": list(tags)}
    )
    output_result(state, state.client.agencies.add_tags(id, list(tags)))


@agencies_app.command("remove-tag")
@handle_errors
def remove_tag(
    ctx: typer.Context,
    id: int = _ID,
    tag_id: int = typer.Argument(..., help="ID of the tag."),
) -> None:
    """Remove a tag from an agency."""
    state = get_state(ctx)
    confirm_write(state, f"DELETE {state.client.agencies.url(id, 'tags', tag_id)}")
    output_result(state, state.client.agencies.remove_tag(id, tag_id))
