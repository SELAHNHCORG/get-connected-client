"""``galaxy users`` -- the /users endpoints on the command line.

Every command that changes anything on the server goes through
:func:`~galaxy_digital_cli.cli._confirm.confirm_write` first. That includes
``welcome-email``, which the API models as a GET but which really does put
mail in someone's inbox.
"""

from __future__ import annotations

from typing import Any

import typer

from ._confirm import confirm_write
from ._output import output, output_one
from ._state import State, _merge_fields, handle_errors

users_app = typer.Typer(help="Manage users.", no_args_is_help=True)

#: Columns for the ``list`` table -- enough to identify a row and act on it.
LIST_COLUMNS = ["id", "user_fname", "user_lname", "user_email", "user_status"]
NAMED_COLUMNS = ["id", "name"]

MAX_PER_PAGE = 150

_ID = typer.Argument(..., help="ID of the user.")
_TAG_NAMES = typer.Argument(..., help="Tag names to add.")
#: Module-level singleton so ruff's B008 (immutable-default check) does not
#: trip over a mutable ``list[str]`` annotation paired with a call default.
_STATUS = typer.Option(
    None, "--status", help="active, pending, imported or inactive (repeatable)."
)


def _state(ctx: typer.Context) -> State:
    """The per-invocation state the root callback stashed on the context."""
    return ctx.obj


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@users_app.command("list")
@handle_errors
def list_users(
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
    show_inactive: bool = typer.Option(
        False, "--show-inactive", help="Include inactive users."
    ),
    status: list[str] | None = _STATUS,
    email: str | None = typer.Option(None, "--email", help="Exact email address."),
    email_like: str | None = typer.Option(None, "--email-like", help="Partial email."),
    fname: str | None = typer.Option(None, "--fname", help="Exact first name."),
    fname_like: str | None = typer.Option(
        None, "--fname-like", help="Partial first name."
    ),
    lname: str | None = typer.Option(None, "--lname", help="Exact last name."),
    lname_like: str | None = typer.Option(
        None, "--lname-like", help="Partial last name."
    ),
) -> None:
    """List users, paging through every match."""
    state = _state(ctx)
    rows = state.client.users.list(
        per_page=per_page,
        since_id=since_id,
        since_created=since_created,
        since_updated=since_updated,
        show_inactive=True if show_inactive else None,
        user_status=status or None,
        user_email=email,
        user_email_like=email_like,
        user_fname=fname,
        user_fname_like=fname_like,
        user_lname=lname,
        user_lname_like=lname_like,
    )
    output(state, rows, LIST_COLUMNS, title="Users")


@users_app.command("get")
@handle_errors
def get_user(ctx: typer.Context, id: int = _ID) -> None:
    """Show one user."""
    state = _state(ctx)
    output_one(state, state.client.users.get(id))


def _user_fields(
    data: str | None, fname: str | None, lname: str | None, email: str | None
) -> dict[str, Any]:
    """Map the friendly options onto the spec's ``user_*`` field names."""
    return _merge_fields(data, user_fname=fname, user_lname=lname, user_email=email)


@users_app.command("create")
@handle_errors
def create_user(
    ctx: typer.Context,
    fname: str | None = typer.Option(None, "--fname", help="First name."),
    lname: str | None = typer.Option(None, "--lname", help="Last name."),
    email: str | None = typer.Option(None, "--email", help="Email address."),
    data: str | None = typer.Option(
        None, "--data", help="JSON object of any further user_* fields."
    ),
) -> None:
    """Create a user."""
    state = _state(ctx)
    fields = _user_fields(data, fname, lname, email)
    confirm_write(state, "POST /users", fields)
    output_one(state, state.client.users.create(**fields))


@users_app.command("update")
@handle_errors
def update_user(
    ctx: typer.Context,
    id: int = _ID,
    fname: str | None = typer.Option(None, "--fname", help="First name."),
    lname: str | None = typer.Option(None, "--lname", help="Last name."),
    email: str | None = typer.Option(None, "--email", help="Email address."),
    data: str | None = typer.Option(
        None, "--data", help="JSON object of any further user_* fields."
    ),
) -> None:
    """Update a user, sending only the fields you name."""
    state = _state(ctx)
    fields = _user_fields(data, fname, lname, email)
    confirm_write(state, f"PUT /users/{id}", fields)
    output_one(state, state.client.users.update(id, **fields))


@users_app.command("delete")
@handle_errors
def delete_user(ctx: typer.Context, id: int = _ID) -> None:
    """Delete a user (a soft delete: the record is marked inactive)."""
    state = _state(ctx)
    confirm_write(state, f"DELETE /users/{id}")
    state.client.users.delete(id)


# ---------------------------------------------------------------------------
# agencies
# ---------------------------------------------------------------------------


@users_app.command("agencies")
@handle_errors
def user_agencies(ctx: typer.Context, id: int = _ID) -> None:
    """List the agencies a user has fanned."""
    state = _state(ctx)
    output(state, state.client.users.agencies(id), ["id", "agency_name"])


@users_app.command("add-agency")
@handle_errors
def add_agency(
    ctx: typer.Context,
    id: int = _ID,
    agency_id: int = typer.Argument(..., help="ID of the agency."),
) -> None:
    """Fan an agency on a user's behalf."""
    state = _state(ctx)
    confirm_write(state, f"POST /users/{id}/agencies/{agency_id}")
    state.client.users.add_agency(id, agency_id)


@users_app.command("remove-agency")
@handle_errors
def remove_agency(
    ctx: typer.Context,
    id: int = _ID,
    agency_id: int = typer.Argument(..., help="ID of the agency."),
) -> None:
    """Drop a user's fan relationship with an agency."""
    state = _state(ctx)
    confirm_write(state, f"DELETE /users/{id}/agencies/{agency_id}")
    state.client.users.remove_agency(id, agency_id)


# ---------------------------------------------------------------------------
# benchmarks
# ---------------------------------------------------------------------------


@users_app.command("benchmarks")
@handle_errors
def user_benchmarks(ctx: typer.Context, id: int = _ID) -> None:
    """List the benchmarks a user has earned."""
    state = _state(ctx)
    output(
        state,
        state.client.users.benchmarks(id),
        ["id", "benchmark_title", "benchmark_status", "benchmark_hours"],
    )


@users_app.command("remove-benchmark")
@handle_errors
def remove_benchmark(
    ctx: typer.Context,
    id: int = _ID,
    benchmark_id: int = typer.Argument(..., help="ID of the benchmark."),
) -> None:
    """Take a benchmark away from a user."""
    state = _state(ctx)
    confirm_write(state, f"DELETE /users/{id}/benchmarks/{benchmark_id}")
    state.client.users.remove_benchmark(id, benchmark_id)


# ---------------------------------------------------------------------------
# causes
# ---------------------------------------------------------------------------


@users_app.command("causes")
@handle_errors
def user_causes(ctx: typer.Context, id: int = _ID) -> None:
    """List a user's causes."""
    state = _state(ctx)
    output(state, state.client.users.causes(id), NAMED_COLUMNS)


@users_app.command("add-cause")
@handle_errors
def add_cause(
    ctx: typer.Context,
    id: int = _ID,
    cause_id: int = typer.Argument(..., help="ID of the cause."),
) -> None:
    """Assign a cause to a user."""
    state = _state(ctx)
    confirm_write(state, f"POST /users/{id}/causes/{cause_id}")
    state.client.users.add_cause(id, cause_id)


@users_app.command("remove-cause")
@handle_errors
def remove_cause(
    ctx: typer.Context,
    id: int = _ID,
    cause_id: int = typer.Argument(..., help="ID of the cause."),
) -> None:
    """Unassign a cause from a user."""
    state = _state(ctx)
    confirm_write(state, f"DELETE /users/{id}/causes/{cause_id}")
    state.client.users.remove_cause(id, cause_id)


# ---------------------------------------------------------------------------
# extras
# ---------------------------------------------------------------------------

_SUBSET = typer.Option(None, "--subset", help="regExtra (default) or profile.")


@users_app.command("extras")
@handle_errors
def user_extras(
    ctx: typer.Context, id: int = _ID, subset: str | None = _SUBSET
) -> None:
    """List a user's custom key/value data."""
    state = _state(ctx)
    output(state, state.client.users.extras(id, subset=subset), ["key", "value"])


@users_app.command("set-extras")
@handle_errors
def set_extras(
    ctx: typer.Context,
    id: int = _ID,
    data: str = typer.Option(
        ...,
        "--data",
        help='JSON body, e.g. \'{"extras": [{"key": "Language", "value": "es"}]}\'.',
    ),
    subset: str | None = _SUBSET,
) -> None:
    """Replace a user's extras.

    The payload is the *entirety* of the user's extras for the subset, so
    include the pairs you want to keep.
    """
    state = _state(ctx)
    fields = _merge_fields(data)
    confirm_write(state, f"POST /users/{id}/extras", fields)
    state.client.users.set_extras(id, fields, subset=subset)


# ---------------------------------------------------------------------------
# hours
# ---------------------------------------------------------------------------


@users_app.command("hours")
@handle_errors
def user_hours(ctx: typer.Context, id: int = _ID) -> None:
    """List the hours a user has submitted."""
    state = _state(ctx)
    output(
        state,
        state.client.users.hours(id),
        ["id", "hour_hours", "hour_date_start", "hour_status"],
    )


# ---------------------------------------------------------------------------
# interests
# ---------------------------------------------------------------------------


@users_app.command("interests")
@handle_errors
def user_interests(ctx: typer.Context, id: int = _ID) -> None:
    """List a user's interests."""
    state = _state(ctx)
    output(state, state.client.users.interests(id), NAMED_COLUMNS)


@users_app.command("add-interest")
@handle_errors
def add_interest(
    ctx: typer.Context,
    id: int = _ID,
    interest_id: int = typer.Argument(..., help="ID of the interest."),
) -> None:
    """Assign an interest to a user."""
    state = _state(ctx)
    confirm_write(state, f"POST /users/{id}/interests/{interest_id}")
    state.client.users.add_interest(id, interest_id)


@users_app.command("remove-interest")
@handle_errors
def remove_interest(
    ctx: typer.Context,
    id: int = _ID,
    interest_id: int = typer.Argument(..., help="ID of the interest."),
) -> None:
    """Unassign an interest from a user."""
    state = _state(ctx)
    confirm_write(state, f"DELETE /users/{id}/interests/{interest_id}")
    state.client.users.remove_interest(id, interest_id)


# ---------------------------------------------------------------------------
# messaging and login
# ---------------------------------------------------------------------------


@users_app.command("welcome-email")
@handle_errors
def welcome_email(ctx: typer.Context, id: int = _ID) -> None:
    """Send a user the site's welcome email.

    The API serves this over GET, but it really does send mail, so it
    confirms like any other write.
    """
    state = _state(ctx)
    confirm_write(state, f"GET /users/{id}/welcomeEmail (sends mail)")
    state.client.users.send_welcome_email(id)


@users_app.command("oneclick")
@handle_errors
def oneclick(ctx: typer.Context, id: int = _ID) -> None:
    """Mint a one-click login link for a user."""
    state = _state(ctx)
    output_one(state, state.client.users.oneclick(id))


# ---------------------------------------------------------------------------
# optouts
# ---------------------------------------------------------------------------

_OPTOUT_DATA = typer.Option(
    ...,
    "--data",
    help='JSON body, e.g. \'{"optout_areas": ["blast"]}\'.',
)


@users_app.command("optouts")
@handle_errors
def optouts(ctx: typer.Context, id: int = _ID) -> None:
    """Show which message areas a user has opted out of."""
    state = _state(ctx)
    output_one(state, state.client.users.optouts(id))


@users_app.command("add-optout")
@handle_errors
def add_optout(ctx: typer.Context, id: int = _ID, data: str = _OPTOUT_DATA) -> None:
    """Opt a user out of messaging (supersedes their stored optouts)."""
    state = _state(ctx)
    fields = _merge_fields(data)
    confirm_write(state, f"POST /users/{id}/optouts", fields)
    state.client.users.add_optout(id, **fields)


@users_app.command("remove-optout")
@handle_errors
def remove_optout(ctx: typer.Context, id: int = _ID, data: str = _OPTOUT_DATA) -> None:
    """Lift named areas from a user's opt-out list."""
    state = _state(ctx)
    fields = _merge_fields(data)
    confirm_write(state, f"DELETE /users/{id}/optouts", fields)
    state.client.users.remove_optout(id, **fields)


# ---------------------------------------------------------------------------
# qualifications, registration questions, responses, tracks
# ---------------------------------------------------------------------------


@users_app.command("qualifications")
@handle_errors
def qualifications(ctx: typer.Context, id: int = _ID) -> None:
    """List a user's qualifications."""
    state = _state(ctx)
    output(
        state,
        state.client.users.qualifications(id),
        ["id", "qualification_title", "status", "expires"],
    )


@users_app.command("registration-questions")
@handle_errors
def registration_questions(ctx: typer.Context, id: int = _ID) -> None:
    """List a user's answers to the custom registration questions."""
    state = _state(ctx)
    output(
        state,
        state.client.users.registration_answers(id),
        ["question_id", "area", "question", "answer"],
    )


@users_app.command("set-registration-questions")
@handle_errors
def set_registration_questions(
    ctx: typer.Context,
    id: int = _ID,
    data: str = typer.Option(
        ...,
        "--data",
        help=(
            'JSON body, e.g. \'{"answers": [{"question_id": "1", '
            '"answer": ["blue"]}]}\'.'
        ),
    ),
) -> None:
    """Store a user's answers to the custom registration questions."""
    state = _state(ctx)
    fields = _merge_fields(data)
    answers = fields.get("answers")
    if not isinstance(answers, list):
        raise typer.BadParameter('--data must be an object with an "answers" array')
    confirm_write(state, f"POST /users/{id}/registrationQuestions", fields)
    state.client.users.set_registration_answers(id, answers)


@users_app.command("responses")
@handle_errors
def responses(ctx: typer.Context, id: int = _ID) -> None:
    """List the needs a user has signed up for."""
    state = _state(ctx)
    output(
        state,
        state.client.users.responses(id),
        ["id", "need_id", "date_start", "duration", "status"],
    )


@users_app.command("tracks")
@handle_errors
def tracks(ctx: typer.Context, id: int = _ID) -> None:
    """List a user's tracks."""
    state = _state(ctx)
    output(state, state.client.users.tracks(id), ["id", "name", "created_at"])


# ---------------------------------------------------------------------------
# tags
# ---------------------------------------------------------------------------


@users_app.command("tags")
@handle_errors
def tags(ctx: typer.Context, id: int = _ID) -> None:
    """List a user's tags."""
    state = _state(ctx)
    output(state, state.client.users.tags(id), NAMED_COLUMNS)


@users_app.command("add-tags")
@handle_errors
def add_tags(
    ctx: typer.Context,
    id: int = _ID,
    tags: list[str] = _TAG_NAMES,
) -> None:
    """Add one or more tags -- by name, not id -- to a user."""
    state = _state(ctx)
    confirm_write(state, f"POST /users/{id}/tags", {"tags": tags})
    state.client.users.add_tags(id, list(tags))


@users_app.command("remove-tag")
@handle_errors
def remove_tag(
    ctx: typer.Context,
    id: int = _ID,
    tag_id: int = typer.Argument(..., help="ID of the tag."),
) -> None:
    """Remove a tag from a user."""
    state = _state(ctx)
    confirm_write(state, f"DELETE /users/{id}/tags/{tag_id}")
    state.client.users.remove_tag(id, tag_id)
