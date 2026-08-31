"""``galaxy reports`` -- answers the API will not compute for you.

Everything here is a read-only aggregation over records the API already
stores, so no command in this module ever writes and none of them needs
:func:`~get_connected_client.cli._confirm.confirm_write`. They all work
unchanged under ``--read-only``.

The aggregating happens client-side because the endpoints give us no
choice: ``/hours`` accepts only the paging filters (``per_page``,
``since_id``, ``since_created``, ``since_updated``, ``show_inactive``) --
there is no ``need_id`` or ``user_id`` filter to push the work onto the
server -- so the scan pages through hour records and narrows them here.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from typing import Any

import typer

from ..models.hours import Hour
from ..models.needs import Need
from ._output import OutputFormat, console, output
from ._state import get_state, handle_errors

reports_app = typer.Typer(
    help="Reports aggregated from the API's records.", no_args_is_help=True
)

#: Columns for the ``attendance`` table, in ranking order.
ATTENDANCE_COLUMNS = [
    "rank",
    "volunteer",
    "user_id",
    "programs_attended",
    "hour_entries",
    "total_hours",
]

#: Module-level singletons so ruff's B008 (immutable-default check) does not
#: trip over a ``list[...]`` annotation paired with a call default.
_NEED_ID = typer.Option(
    None,
    "--need-id",
    help="Count this need id exactly, skipping title resolution (repeatable).",
)
_STATUS = typer.Option(
    None,
    "--status",
    help=(
        "Only count hour records with this status, e.g. 'approved' "
        "(case-insensitive, repeatable). Default: every status."
    ),
)


# ---------------------------------------------------------------------------
# period
# ---------------------------------------------------------------------------


def _period(
    start: str | None, end: str | None, year: int | None
) -> tuple[str | None, str | None]:
    """The inclusive ``(start, end)`` attendance-date bounds, as ISO dates.

    ``--year`` is shorthand for the whole calendar year, so it may not be
    combined with an explicit bound -- silently letting one win over the
    other would report a period nobody asked for.

    :raises typer.BadParameter: ``--year`` was combined with a bound.
    """
    if year is None:
        return start, end
    if start or end:
        raise typer.BadParameter("--year cannot be combined with --start/--end")
    return f"{year}-01-01", f"{year}-12-31"


def _period_label(start: str | None, end: str | None) -> str:
    """A human phrase for the period, for the table title."""
    if start and end:
        return f"{start} to {end}"
    if start:
        return f"since {start}"
    if end:
        return f"through {end}"
    return "all time"


# ---------------------------------------------------------------------------
# needs
# ---------------------------------------------------------------------------


def _title_matches(needs: Iterable[Need], wanted: str) -> list[tuple[int, str]]:
    """``(id, title)`` for every need whose title contains *wanted*.

    The comparison is a case-insensitive substring, and a need with no usable
    id is dropped: nothing in an hour record could ever match it.
    """
    return [
        (need.id, need.need_title or "")
        for need in needs
        if need.id is not None and wanted in (need.need_title or "").lower()
    ]


def _resolve_needs(
    state: Any, program: str | None, need_ids: list[int]
) -> list[dict[str, Any]]:
    """The needs to count attendance for, as ``{"id", "need_title"}`` rows.

    Ids from ``--need-id`` are taken at face value -- no lookup, so nothing
    depends on how the server chooses to interpret a title.

    ``--program`` is matched twice over. The server-side ``need_title``
    filter runs first (it is the cheap path), but its matching semantics are
    not documented, so every row it returns is still checked here for a
    case-insensitive substring. When that yields nothing -- a strict
    server-side filter would answer an empty page for "hollywood" -- the
    whole (inactive included) need list is scanned and matched locally.

    :raises typer.BadParameter: a ``--program`` matched no need at all.
    """
    matched: dict[int, str] = {int(i): "" for i in need_ids}
    if program:
        wanted = program.lower()
        found = _title_matches(
            state.client.needs.list(need_title=program, show_inactive=True), wanted
        )
        if not found:
            found = _title_matches(state.client.needs.list(show_inactive=True), wanted)
        if not found and not matched:
            raise typer.BadParameter(
                f"no needs matched --program {program!r}: check the title "
                "(`galaxy needs list --title ...`) or pin ids with --need-id"
            )
        matched.update(found)
    return [{"id": id, "need_title": title} for id, title in matched.items()]


def _needs_label(needs: list[dict[str, Any]]) -> str:
    """A short phrase naming the matched needs, for the table title."""
    names = [str(n["need_title"] or f"need {n['id']}") for n in needs]
    if len(names) > 3:
        return f"{len(names)} needs"
    return ", ".join(names)


# ---------------------------------------------------------------------------
# hours
# ---------------------------------------------------------------------------


def _scan_hours(state: Any, start: str | None, full_scan: bool) -> Iterator[Hour]:
    """Page every hour record the report might care about.

    ``show_inactive`` is on: the report counts attendance, and narrowing by
    status is what ``--status`` is for.

    With a start bound and without ``--full-scan``, ``since_created`` skips
    the pages of hours logged before the period began. It is an optimization
    on *creation* time standing in for a filter on *attendance* time, which
    the endpoint does not offer -- sound as long as hours are logged on or
    after the date they were served.
    """
    params: dict[str, Any] = {"show_inactive": "Yes"}
    if start and not full_scan:
        params["since_created"] = f"{start} 00:00"
    for row in state.client.paginate("/hours", params):
        yield Hour.model_validate(row)


def _in_period(date: str, start: str | None, end: str | None) -> bool:
    """Is *date* (``YYYY-MM-DD``) inside the inclusive bounds?

    ISO dates sort lexicographically, so string comparison is date
    comparison -- and it cannot raise on whatever the API sent.
    """
    if start and date < start:
        return False
    return not (end and date > end)


def _volunteer(user: Any, user_id: int) -> str:
    """A display name for a volunteer, degrading to email then id."""
    name = f"{user.user_fname or ''} {user.user_lname or ''}".strip()
    return name or user.user_email or f"user {user_id}"


def _tally(
    hours: Iterable[Hour],
    need_ids: set[int],
    start: str | None,
    end: str | None,
    statuses: set[str],
) -> list[dict[str, Any]]:
    """Rank volunteers by how many distinct days they turned up.

    A program attended is a *date*, not an hour record: somebody who logged
    a morning block and an afternoon block on the same day attended once.
    """
    tallies: dict[int, dict[str, Any]] = {}
    for hour in hours:
        if hour.need is None or hour.need.id not in need_ids:
            continue
        if hour.user is None or hour.user.id is None:
            # Nobody to credit the attendance to.
            continue
        date = (hour.hour_date_start or "")[:10]
        if not date or not _in_period(date, start, end):
            continue
        if statuses and (hour.hour_status or "").lower() not in statuses:
            continue
        user_id = hour.user.id
        row = tallies.setdefault(
            user_id,
            {
                "volunteer": _volunteer(hour.user, user_id),
                "user_id": user_id,
                "dates": set(),
                "hour_entries": 0,
                "total_hours": 0.0,
            },
        )
        row["dates"].add(date)
        row["hour_entries"] += 1
        try:
            row["total_hours"] += float(hour.hour_hours or 0)
        except (TypeError, ValueError):
            # A malformed hour_hours costs the report one addend, never the
            # attendance itself -- the volunteer was still there that day.
            pass
    rows = [
        {
            "volunteer": row["volunteer"],
            "user_id": row["user_id"],
            "programs_attended": len(row["dates"]),
            "hour_entries": row["hour_entries"],
            "total_hours": round(row["total_hours"], 2),
        }
        for row in tallies.values()
    ]
    rows.sort(
        key=lambda r: (
            -int(r["programs_attended"]),
            -float(r["total_hours"]),
            str(r["volunteer"]).lower(),
        )
    )
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------


@reports_app.command("attendance")
@handle_errors
def attendance(
    ctx: typer.Context,
    program: str | None = typer.Option(
        None,
        "--program",
        help="Match needs whose title contains this text (case-insensitive).",
    ),
    need_id: list[int] | None = _NEED_ID,
    start: str | None = typer.Option(
        None, "--start", help="Earliest attendance date, 'YYYY-MM-DD' (inclusive)."
    ),
    end: str | None = typer.Option(
        None, "--end", help="Latest attendance date, 'YYYY-MM-DD' (inclusive)."
    ),
    year: int | None = typer.Option(
        None, "--year", help="Shorthand for --start YEAR-01-01 --end YEAR-12-31."
    ),
    status: list[str] | None = _STATUS,
    full_scan: bool = typer.Option(
        False,
        "--full-scan",
        help=(
            "Page through every hour record. By default a --start bound also "
            "sends since_created, which skips hours logged before the period "
            "and makes the scan much shorter -- at the cost of missing "
            "attendance that was logged early (before the date it happened). "
            "Use --full-scan when completeness matters more than speed."
        ),
    ),
) -> None:
    """Rank a program's volunteers by how many of its sessions they attended.

    Attendance comes from hour records: a volunteer counts as attending on
    every distinct date they logged time against the matched needs. Name the
    program with --program (a title substring) or pin exact needs with
    --need-id; at least one is required.
    """
    state = get_state(ctx)
    need_ids = need_id or []
    if not program and not need_ids:
        raise typer.BadParameter("give --program and/or --need-id")
    start, end = _period(start, end, year)
    needs = _resolve_needs(state, program, need_ids)
    if state.format is not OutputFormat.JSON:
        # Show what was matched before the (potentially long) hours scan, so
        # a wrong match can be spotted without waiting for the report.
        for need in needs:
            console.print(f"[bold]need {need['id']}[/] {need['need_title']}")
    rows = _tally(
        _scan_hours(state, start, full_scan),
        {int(n["id"]) for n in needs},
        start,
        end,
        {s.lower() for s in (status or [])},
    )
    if state.format is OutputFormat.JSON:
        # output() emits rows alone; the matched needs are half the answer
        # (they say *what* was counted), so JSON gets both in one object.
        console.print_json(json.dumps({"needs": needs, "rows": rows}, default=str))
        return
    output(
        state,
        rows,
        ATTENDANCE_COLUMNS,
        title=f"attendance: {_needs_label(needs)} ({_period_label(start, end)})",
    )
