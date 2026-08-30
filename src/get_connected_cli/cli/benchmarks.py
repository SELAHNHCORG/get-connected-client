"""``galaxy benchmarks`` -- the /benchmarks endpoints on the command line.

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

benchmarks_app = typer.Typer(help="Manage benchmarks.", no_args_is_help=True)

#: Columns for the ``list`` table -- enough to identify a row and act on it.
LIST_COLUMNS = ["id", "benchmark_title", "benchmark_status", "benchmark_hours"]

_ID = typer.Argument(..., help="ID of the benchmark.")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@benchmarks_app.command("list")
@handle_errors
def list_benchmarks(
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
        help="Include inactive benchmarks; omit for the server default.",
    ),
) -> None:
    """List benchmarks, paging through every match."""
    state = get_state(ctx)
    rows = state.client.benchmarks.list(
        per_page=per_page,
        since_id=since_id,
        since_created=since_created,
        since_updated=since_updated,
        show_inactive=show_inactive,
    )
    output(state, rows, LIST_COLUMNS, title="Benchmarks")


@benchmarks_app.command("get")
@handle_errors
def get_benchmark(ctx: typer.Context, id: int = _ID) -> None:
    """Show one benchmark."""
    state = get_state(ctx)
    output_one(state, state.client.benchmarks.get(id))


def _benchmark_fields(
    data: str | None, title: str | None, hours: str | None
) -> dict[str, Any]:
    """Map the friendly options onto the spec's ``benchmark_*`` names."""
    return _merge_fields(data, benchmark_title=title, benchmark_hours=hours)


@benchmarks_app.command("create")
@handle_errors
def create_benchmark(
    ctx: typer.Context,
    title: str | None = typer.Option(None, "--title", help="Benchmark title."),
    hours: str | None = typer.Option(
        None, "--hours", help="Hours required to earn the benchmark."
    ),
    data: str | None = typer.Option(
        None,
        "--data",
        help=(
            "JSON object of any further fields, e.g. benchmark_status, "
            "benchmark_icon, benchmark_date_start, benchmark_date_end."
        ),
    ),
) -> None:
    """Create a benchmark."""
    state = get_state(ctx)
    fields = _benchmark_fields(data, title, hours)
    confirm_write(state, f"POST {state.client.benchmarks.url()}", fields)
    output_result(state, state.client.benchmarks.create(**fields))


@benchmarks_app.command("update")
@handle_errors
def update_benchmark(
    ctx: typer.Context,
    id: int = _ID,
    title: str | None = typer.Option(None, "--title", help="Benchmark title."),
    hours: str | None = typer.Option(
        None, "--hours", help="Hours required to earn the benchmark."
    ),
    data: str | None = typer.Option(
        None, "--data", help="JSON object of any further fields."
    ),
) -> None:
    """Update a benchmark, sending only the fields you name."""
    state = get_state(ctx)
    fields = _benchmark_fields(data, title, hours)
    confirm_write(state, f"PUT {state.client.benchmarks.url(id)}", fields)
    output_result(state, state.client.benchmarks.update(id, **fields))


@benchmarks_app.command("delete")
@handle_errors
def delete_benchmark(ctx: typer.Context, id: int = _ID) -> None:
    """Delete a benchmark (a soft delete: the record is marked inactive)."""
    state = get_state(ctx)
    confirm_write(state, f"DELETE {state.client.benchmarks.url(id)}")
    state.client.benchmarks.delete(id)
    output_result(state)


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------


@benchmarks_app.command("users")
@handle_errors
def benchmark_users(ctx: typer.Context, id: int = _ID) -> None:
    """List the users who have earned a benchmark."""
    state = get_state(ctx)
    output(
        state,
        state.client.benchmarks.users(id),
        ["id", "user_fname", "user_lname", "user_email"],
        title="Benchmark Users",
    )
