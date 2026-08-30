"""``galaxy needs`` -- the /needs endpoints on the command line.

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

needs_app = typer.Typer(help="Manage needs.", no_args_is_help=True)

#: Columns for the ``list`` table -- enough to identify a row and act on it.
LIST_COLUMNS = ["id", "need_title", "need_status", "need_date"]

_ID = typer.Argument(..., help="ID of the need.")
#: Module-level singleton so ruff's B008 (immutable-default check) does not
#: trip over a mutable ``list[int]`` annotation paired with a call default.
#: The spec types the ``/needs`` filter as an array, so the flag repeats.
_AGENCY_ID = typer.Option(
    None, "--agency-id", help="Only needs from this agency (repeatable)."
)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@needs_app.command("list")
@handle_errors
def list_needs(
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
        help="Include inactive needs; omit for the server default.",
    ),
    agency_id: list[int] | None = _AGENCY_ID,
    title: str | None = typer.Option(None, "--title", help="Search by need title."),
    status: str | None = typer.Option(
        None, "--status", help="active, inactive or pending."
    ),
) -> None:
    """List needs, paging through every match."""
    state = get_state(ctx)
    rows = state.client.needs.list(
        per_page=per_page,
        since_id=since_id,
        since_created=since_created,
        since_updated=since_updated,
        # Tri-state, passed through untouched: None omits the parameter and
        # takes the server default, True sends Yes, False sends No.
        show_inactive=show_inactive,
        agency_id=agency_id or None,
        need_title=title,
        need_status=status,
    )
    output(state, rows, LIST_COLUMNS, title="Needs")


@needs_app.command("get")
@handle_errors
def get_need(ctx: typer.Context, id: int = _ID) -> None:
    """Show one need."""
    state = get_state(ctx)
    output_one(state, state.client.needs.get(id))


def _need_fields(
    data: str | None, title: str | None, body: str | None, agency_id: int | None
) -> dict[str, Any]:
    """Map the friendly options onto the spec's ``need_*`` field names."""
    return _merge_fields(data, need_title=title, need_body=body, agency_id=agency_id)


@needs_app.command("create")
@handle_errors
def create_need(
    ctx: typer.Context,
    title: str | None = typer.Option(None, "--title", help="Need title."),
    body: str | None = typer.Option(None, "--body", help="Need description."),
    agency_id: int | None = typer.Option(
        None, "--agency-id", help="ID of the agency posting the need."
    ),
    data: str | None = typer.Option(
        None, "--data", help="JSON object of any further need_* fields."
    ),
) -> None:
    """Create a need."""
    state = get_state(ctx)
    fields = _need_fields(data, title, body, agency_id)
    confirm_write(state, f"POST {state.client.needs.url()}", fields)
    output_result(state, state.client.needs.create(**fields))


@needs_app.command("update")
@handle_errors
def update_need(
    ctx: typer.Context,
    id: int = _ID,
    title: str | None = typer.Option(None, "--title", help="Need title."),
    body: str | None = typer.Option(None, "--body", help="Need description."),
    agency_id: int | None = typer.Option(
        None, "--agency-id", help="ID of the agency posting the need."
    ),
    data: str | None = typer.Option(
        None, "--data", help="JSON object of any further need_* fields."
    ),
) -> None:
    """Update a need, sending only the fields you name."""
    state = get_state(ctx)
    fields = _need_fields(data, title, body, agency_id)
    confirm_write(state, f"PUT {state.client.needs.url(id)}", fields)
    output_result(state, state.client.needs.update(id, **fields))


@needs_app.command("delete")
@handle_errors
def delete_need(ctx: typer.Context, id: int = _ID) -> None:
    """Delete a need (a soft delete: the record is marked inactive)."""
    state = get_state(ctx)
    confirm_write(state, f"DELETE {state.client.needs.url(id)}")
    state.client.needs.delete(id)
    output_result(state)


# ---------------------------------------------------------------------------
# responses / questions
# ---------------------------------------------------------------------------


@needs_app.command("responses")
@handle_errors
def responses(ctx: typer.Context, id: int = _ID) -> None:
    """List the responses (sign-ups) to a need."""
    state = get_state(ctx)
    output(
        state,
        state.client.needs.responses(id),
        ["id", "response_status", "response_date_added"],
        title="Responses",
    )


@needs_app.command("questions")
@handle_errors
def questions(ctx: typer.Context, id: int = _ID) -> None:
    """List the custom questions asked of volunteers responding to a need."""
    state = get_state(ctx)
    output(
        state,
        state.client.needs.questions(id),
        ["id", "q_type", "q_label", "q_status"],
        title="Questions",
    )


# ---------------------------------------------------------------------------
# shifts
# ---------------------------------------------------------------------------


@needs_app.command("add-shift")
@handle_errors
def add_shift(
    ctx: typer.Context,
    id: int = _ID,
    slots: int = typer.Option(..., "--slots", help="Number of volunteer slots."),
    start_date: str = typer.Option(
        ..., "--start-date", help="Shift start date, e.g. '2024-02-28'."
    ),
    start_time: str = typer.Option(
        ..., "--start-time", help="Shift start time, e.g. '12:00:00'."
    ),
    duration: str = typer.Option(..., "--duration", help="Shift duration in minutes."),
) -> None:
    """Add a shift to a need."""
    state = get_state(ctx)
    # Preview the real wire body, not the flat options: the endpoint takes a
    # ``shifts`` array with one combined ``start``. This mirrors the envelope
    # :meth:`~get_connected_client.resources.needs.Needs.add_shift` builds from
    # the very same arguments -- keep the two in step.
    body = {
        "shifts": [
            {
                "start": f"{start_date} {start_time}",
                "slots": slots,
                "duration": duration,
            }
        ]
    }
    confirm_write(state, f"POST {state.client.needs.url(id, 'shifts')}", body)
    output_result(
        state,
        state.client.needs.add_shift(
            id,
            slots=slots,
            start_date=start_date,
            start_time=start_time,
            duration=duration,
        ),
    )


@needs_app.command("remove-shift")
@handle_errors
def remove_shift(
    ctx: typer.Context,
    id: int = _ID,
    shift_id: int = typer.Argument(..., help="ID of the shift."),
) -> None:
    """Remove a shift from a need."""
    state = get_state(ctx)
    confirm_write(state, f"DELETE {state.client.needs.url(id, 'shifts', shift_id)}")
    output_result(state, state.client.needs.remove_shift(id, shift_id))


# ---------------------------------------------------------------------------
# interests
# ---------------------------------------------------------------------------


@needs_app.command("add-interest")
@handle_errors
def add_interest(
    ctx: typer.Context,
    id: int = _ID,
    interest_id: int = typer.Argument(..., help="ID of the interest."),
) -> None:
    """Attach an interest to a need."""
    state = get_state(ctx)
    confirm_write(state, f"POST {state.client.needs.url(id, 'interests', interest_id)}")
    output_result(state, state.client.needs.add_interest(id, interest_id))


@needs_app.command("remove-interest")
@handle_errors
def remove_interest(
    ctx: typer.Context,
    id: int = _ID,
    interest_id: int = typer.Argument(..., help="ID of the interest."),
) -> None:
    """Detach an interest from a need."""
    state = get_state(ctx)
    confirm_write(
        state, f"DELETE {state.client.needs.url(id, 'interests', interest_id)}"
    )
    output_result(state, state.client.needs.remove_interest(id, interest_id))


# ---------------------------------------------------------------------------
# qualifications
# ---------------------------------------------------------------------------


@needs_app.command("add-qualification")
@handle_errors
def add_qualification(
    ctx: typer.Context,
    id: int = _ID,
    qualification_id: int = typer.Argument(..., help="ID of the qualification."),
) -> None:
    """Attach a qualification to a need."""
    state = get_state(ctx)
    confirm_write(
        state,
        f"POST {state.client.needs.url(id, 'qualifications', qualification_id)}",
    )
    output_result(state, state.client.needs.add_qualification(id, qualification_id))


@needs_app.command("remove-qualification")
@handle_errors
def remove_qualification(
    ctx: typer.Context,
    id: int = _ID,
    qualification_id: int = typer.Argument(..., help="ID of the qualification."),
) -> None:
    """Detach a qualification from a need."""
    state = get_state(ctx)
    confirm_write(
        state,
        f"DELETE {state.client.needs.url(id, 'qualifications', qualification_id)}",
    )
    output_result(state, state.client.needs.remove_qualification(id, qualification_id))
