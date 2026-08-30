"""``galaxy reports`` -- the attendance report.

Every request is mocked with respx. Nothing here may ever reach the
production API, and nothing in this module writes anyway: the report is a
read-only aggregation.
"""

import json

import httpx
import pytest
from typer.testing import CliRunner

from get_connected_client.cli import app
from get_connected_client.cli.reports import _period, _period_label
from get_connected_client.client import MAX_PER_PAGE

runner = CliRunner()


@pytest.fixture
def cli_env(monkeypatch):
    """Point the CLI's lazily-built client at the respx mock."""
    monkeypatch.setenv("GALAXY_API_URL", "https://api.test/api")


HOLLYWOOD = {"id": "42", "need_title": "Hollywood Drop-In"}
OTHER_NEED = {"id": "99", "need_title": "Park Cleanup"}


def hour(
    id,
    user_id,
    date,
    need_id=42,
    hours="3.5",
    status="Approved",
    fname="Mary",
    lname="Shelley",
    email="mary@example.org",
):
    """One hourObject row as the API would send it (ids as strings)."""
    return {
        "id": str(id),
        "user": {
            "id": str(user_id),
            "user_fname": fname,
            "user_lname": lname,
            "user_email": email,
        },
        "need": {"id": str(need_id), "need_title": "Hollywood Drop-In"},
        "hour_date_start": f"{date} 09:00:00",
        "hour_hours": hours,
        "hour_status": status,
    }


def pages(*groups):
    """A respx side_effect that answers each request with the next page."""
    payloads = [{"data": list(group)} for group in groups]
    payloads.append({"data": []})
    calls = iter(payloads)

    def _next(request):
        return httpx.Response(200, json=next(calls))

    return _next


def padded(rows, first_id, size=MAX_PER_PAGE):
    """*rows* topped up to a full page, so the client asks for another one.

    ``paginate`` stops on the first short page and advances its ``since_id``
    cursor to the highest id it saw, so a multi-page test needs a genuinely
    full first page whose ids all sit below the next page's.
    """
    filler = [
        hour(id, 999, "1999-01-01", need_id=99)
        for id in range(first_id, first_id + size - len(rows))
    ]
    return [*rows, *filler]


# --------------------------------------------------------------------------
# period helpers
# --------------------------------------------------------------------------


def test_period_from_year():
    assert _period(None, None, 2026) == ("2026-01-01", "2026-12-31")
    assert _period("2026-03-01", None, None) == ("2026-03-01", None)
    assert _period(None, None, None) == (None, None)


def test_period_labels():
    assert _period_label("2026-01-01", "2026-12-31") == "2026-01-01 to 2026-12-31"
    assert _period_label("2026-01-01", None) == "since 2026-01-01"
    assert _period_label(None, "2026-12-31") == "through 2026-12-31"
    assert _period_label(None, None) == "all time"


# --------------------------------------------------------------------------
# needs resolution
# --------------------------------------------------------------------------


def test_server_filter_match(api, cli_env):
    """The title-filtered /needs request is the cheap path, and it is tried."""
    needs = api.get("/needs").mock(side_effect=pages([HOLLYWOOD]))
    api.get("/hours").mock(side_effect=pages([hour(1, 7, "2026-02-01")]))
    result = runner.invoke(app, ["reports", "attendance", "--program", "hollywood"])
    assert result.exit_code == 0, result.output
    assert needs.calls[0].request.url.params["need_title"] == "hollywood"
    assert needs.calls[0].request.url.params["show_inactive"] == "Yes"
    assert "Hollywood Drop-In" in result.output


def test_falls_back_to_unfiltered_scan(api, cli_env):
    """A strict (or 404-ing) server filter must not lose the match.

    The client's paginate treats a 404 as "no rows", so the fallback is what
    stands between a strict ``need_title`` and an empty report.
    """
    calls = []

    def _needs(request):
        calls.append(request.url.params)
        if "need_title" in request.url.params:
            return httpx.Response(404)
        return httpx.Response(200, json={"data": [OTHER_NEED, HOLLYWOOD]})

    api.get("/needs").mock(side_effect=_needs)
    api.get("/hours").mock(side_effect=pages([hour(1, 7, "2026-02-01")]))
    result = runner.invoke(app, ["reports", "attendance", "--program", "HOLLYwood"])
    assert result.exit_code == 0, result.output
    assert "need_title" in calls[0]
    assert "need_title" not in calls[1]
    assert "Hollywood Drop-In" in result.output
    # the unrelated need in the same payload is not counted
    assert "Park Cleanup" not in result.output


def test_no_match_exits_with_help(api, cli_env):
    api.get("/needs").mock(side_effect=pages([OTHER_NEED]))
    result = runner.invoke(app, ["reports", "attendance", "--program", "hollywood"])
    assert result.exit_code != 0
    assert "no needs matched" in result.output
    assert "--need-id" in result.output


def test_need_id_skips_the_needs_lookup(api, cli_env):
    """No /needs route is registered: a lookup would have nothing to answer it."""
    api.get("/hours").mock(side_effect=pages([hour(1, 7, "2026-02-01")]))
    result = runner.invoke(app, ["reports", "attendance", "--need-id", "42"])
    assert result.exit_code == 0, result.output
    assert "need 42" in result.output
    assert all(call.request.url.path != "/api/needs" for call in api.calls)


def test_need_id_is_repeatable(api, cli_env):
    api.get("/hours").mock(
        side_effect=pages(
            [
                hour(1, 7, "2026-02-01"),
                hour(2, 8, "2026-02-01", need_id=99),
                hour(3, 9, "2026-02-01", need_id=13),
            ]
        )
    )
    result = runner.invoke(
        app,
        ["--json", "reports", "attendance", "--need-id", "42", "--need-id", "99"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert [n["id"] for n in payload["needs"]] == [42, 99]
    assert {row["user_id"] for row in payload["rows"]} == {7, 8}


# --------------------------------------------------------------------------
# aggregation
# --------------------------------------------------------------------------


def test_ranking_over_multiple_pages(api, cli_env):
    """Distinct dates rank volunteers, not raw hour rows."""
    api.get("/needs").mock(side_effect=pages([HOLLYWOOD]))
    hours = api.get("/hours").mock(
        side_effect=pages(
            padded(
                [
                    # Mary: two entries the same day -> one program attended
                    hour(1, 7, "2026-01-05", hours="2", fname="Mary", lname="Shelley"),
                    hour(
                        2, 7, "2026-01-05", hours="1.5", fname="Mary", lname="Shelley"
                    ),
                    hour(3, 8, "2026-01-05", hours="4", fname="Ada", lname="Lovelace"),
                    # another need entirely
                    hour(4, 9, "2026-01-05", need_id=99, fname="Nope", lname="Nope"),
                ],
                first_id=10,
            ),
            [
                # Ada: three distinct days -> the winner
                hour(1005, 8, "2026-01-12", hours="4", fname="Ada", lname="Lovelace"),
                hour(1006, 8, "2026-01-19", hours="4", fname="Ada", lname="Lovelace"),
                # out of period
                hour(1007, 7, "2025-12-30", fname="Mary", lname="Shelley"),
                # unparseable hours: the attendance still counts
                hour(1008, 7, "2026-02-02", hours="n/a", fname="Mary", lname="Shelley"),
            ],
        )
    )
    result = runner.invoke(
        app,
        [
            "--json",
            "reports",
            "attendance",
            "--program",
            "hollywood",
            "--year",
            "2026",
        ],
    )
    assert result.exit_code == 0, result.output
    # a full first page, then a short one: the scan really paged
    assert len(hours.calls) == 2
    payload = json.loads(result.output)
    assert payload["needs"] == [{"id": 42, "need_title": "Hollywood Drop-In"}]
    ada, mary = payload["rows"]
    assert ada == {
        "volunteer": "Ada Lovelace",
        "user_id": 8,
        "programs_attended": 3,
        "hour_entries": 3,
        "total_hours": 12.0,
        "rank": 1,
    }
    assert mary["volunteer"] == "Mary Shelley"
    assert mary["rank"] == 2
    # two same-day entries collapse to one attended program
    assert mary["programs_attended"] == 2
    assert mary["hour_entries"] == 3
    # the "n/a" row contributed no hours but was still counted
    assert mary["total_hours"] == 3.5
    # nobody from need 99 made it in
    assert {row["user_id"] for row in payload["rows"]} == {7, 8}


def test_explicit_bounds_are_inclusive(api, cli_env):
    api.get("/hours").mock(
        side_effect=pages(
            [
                hour(1, 7, "2026-03-01"),
                hour(2, 7, "2026-03-31"),
                hour(3, 7, "2026-04-01"),
                hour(4, 7, "2026-02-28"),
            ]
        )
    )
    result = runner.invoke(
        app,
        [
            "--json",
            "reports",
            "attendance",
            "--need-id",
            "42",
            "--start",
            "2026-03-01",
            "--end",
            "2026-03-31",
            "--full-scan",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["rows"][0]["programs_attended"] == 2


def test_status_filter(api, cli_env):
    api.get("/hours").mock(
        side_effect=pages(
            [
                hour(1, 7, "2026-01-05", status="Approved"),
                hour(2, 7, "2026-01-06", status="pending"),
                hour(3, 7, "2026-01-07", status=None),
            ]
        )
    )
    result = runner.invoke(
        app,
        ["--json", "reports", "attendance", "--need-id", "42", "--status", "approved"],
    )
    assert result.exit_code == 0, result.output
    rows = json.loads(result.output)["rows"]
    assert rows[0]["programs_attended"] == 1
    assert rows[0]["hour_entries"] == 1


def test_status_filter_is_repeatable(api, cli_env):
    api.get("/hours").mock(
        side_effect=pages(
            [
                hour(1, 7, "2026-01-05", status="Approved"),
                hour(2, 7, "2026-01-06", status="pending"),
                hour(3, 7, "2026-01-07", status="denied"),
            ]
        )
    )
    result = runner.invoke(
        app,
        [
            "--json",
            "reports",
            "attendance",
            "--need-id",
            "42",
            "--status",
            "APPROVED",
            "--status",
            "Pending",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["rows"][0]["programs_attended"] == 2


def test_rows_without_a_user_or_date_are_skipped(api, cli_env):
    api.get("/hours").mock(
        side_effect=pages(
            [
                {"id": "1", "need": {"id": "42"}, "hour_date_start": "2026-01-05"},
                {"id": "2", "user": {"id": "7"}, "need": {"id": "42"}},
                {"id": "3", "user": {"id": "7"}, "hour_date_start": "2026-01-05"},
                hour(4, 7, "2026-01-05"),
            ]
        )
    )
    result = runner.invoke(app, ["--json", "reports", "attendance", "--need-id", "42"])
    assert result.exit_code == 0, result.output
    rows = json.loads(result.output)["rows"]
    assert len(rows) == 1
    assert rows[0]["hour_entries"] == 1


def test_volunteer_falls_back_to_email_then_id(api, cli_env):
    api.get("/hours").mock(
        side_effect=pages(
            [
                hour(1, 7, "2026-01-05", fname=None, lname=None),
                {
                    "id": "2",
                    "user": {"id": "8"},
                    "need": {"id": "42"},
                    "hour_date_start": "2026-01-05 09:00:00",
                    "hour_hours": "1",
                },
            ]
        )
    )
    result = runner.invoke(app, ["--json", "reports", "attendance", "--need-id", "42"])
    assert result.exit_code == 0, result.output
    names = {
        row["user_id"]: row["volunteer"] for row in json.loads(result.output)["rows"]
    }
    assert names == {7: "mary@example.org", 8: "user 8"}


def test_ties_break_on_hours_then_name(api, cli_env):
    api.get("/hours").mock(
        side_effect=pages(
            [
                hour(1, 7, "2026-01-05", hours="1", fname="Zoe", lname="Zed"),
                hour(2, 8, "2026-01-05", hours="5", fname="Bob", lname="Bee"),
                hour(3, 9, "2026-01-05", hours="1", fname="Amy", lname="Ant"),
            ]
        )
    )
    result = runner.invoke(app, ["--json", "reports", "attendance", "--need-id", "42"])
    assert result.exit_code == 0, result.output
    assert [row["volunteer"] for row in json.loads(result.output)["rows"]] == [
        "Bob Bee",  # most hours
        "Amy Ant",  # tied hours, name asc
        "Zoe Zed",
    ]


# --------------------------------------------------------------------------
# the since_created optimization
# --------------------------------------------------------------------------


def test_start_sends_since_created(api, cli_env):
    hours = api.get("/hours").mock(side_effect=pages([hour(1, 7, "2026-02-01")]))
    result = runner.invoke(
        app,
        ["reports", "attendance", "--need-id", "42", "--start", "2026-01-01"],
    )
    assert result.exit_code == 0, result.output
    params = hours.calls[0].request.url.params
    assert params["since_created"] == "2026-01-01 00:00"
    assert params["show_inactive"] == "Yes"


def test_year_sends_since_created(api, cli_env):
    hours = api.get("/hours").mock(side_effect=pages([hour(1, 7, "2026-02-01")]))
    result = runner.invoke(
        app, ["reports", "attendance", "--need-id", "42", "--year", "2026"]
    )
    assert result.exit_code == 0, result.output
    assert hours.calls[0].request.url.params["since_created"] == "2026-01-01 00:00"


def test_full_scan_omits_since_created(api, cli_env):
    hours = api.get("/hours").mock(side_effect=pages([hour(1, 7, "2026-02-01")]))
    result = runner.invoke(
        app,
        [
            "reports",
            "attendance",
            "--need-id",
            "42",
            "--year",
            "2026",
            "--full-scan",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "since_created" not in hours.calls[0].request.url.params


def test_no_start_bound_omits_since_created(api, cli_env):
    hours = api.get("/hours").mock(side_effect=pages([hour(1, 7, "2026-02-01")]))
    result = runner.invoke(
        app, ["reports", "attendance", "--need-id", "42", "--end", "2026-12-31"]
    )
    assert result.exit_code == 0, result.output
    assert "since_created" not in hours.calls[0].request.url.params


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------


def test_table_lists_the_ranking_highest_first(api, cli_env, monkeypatch):
    # a console wide enough that rich prints the column names in full
    monkeypatch.setenv("COLUMNS", "200")
    api.get("/needs").mock(side_effect=pages([HOLLYWOOD]))
    api.get("/hours").mock(
        side_effect=pages(
            [
                hour(1, 7, "2026-01-05", fname="Mary", lname="Shelley"),
                hour(2, 8, "2026-01-05", fname="Ada", lname="Lovelace"),
                hour(3, 8, "2026-01-12", fname="Ada", lname="Lovelace"),
            ]
        )
    )
    result = runner.invoke(
        app, ["reports", "attendance", "--program", "hollywood", "--year", "2026"]
    )
    assert result.exit_code == 0, result.output
    out = result.output
    assert "attendance" in out
    assert "2026-01-01 to 2026-12-31" in out
    for column in ("rank", "volunteer", "programs_attended", "total_hours"):
        assert column in out
    assert out.index("Ada Lovelace") < out.index("Mary Shelley")


def test_json_carries_needs_and_rows(api, cli_env):
    api.get("/needs").mock(side_effect=pages([HOLLYWOOD]))
    api.get("/hours").mock(side_effect=pages([hour(1, 7, "2026-01-05")]))
    result = runner.invoke(
        app, ["--json", "reports", "attendance", "--program", "hollywood"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["needs"] == [{"id": 42, "need_title": "Hollywood Drop-In"}]
    assert payload["rows"][0]["rank"] == 1
    assert payload["rows"][0]["volunteer"] == "Mary Shelley"


def test_empty_report_is_not_an_error(api, cli_env):
    api.get("/needs").mock(side_effect=pages([HOLLYWOOD]))
    api.get("/hours").mock(side_effect=pages([hour(1, 7, "2020-01-05")]))
    result = runner.invoke(
        app,
        ["--json", "reports", "attendance", "--program", "hollywood", "--year", "2026"],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["rows"] == []


def test_many_needs_collapse_in_the_title(api, cli_env):
    api.get("/hours").mock(side_effect=pages([hour(1, 7, "2026-01-05")]))
    result = runner.invoke(
        app,
        [
            "reports",
            "attendance",
            "--need-id",
            "1",
            "--need-id",
            "2",
            "--need-id",
            "3",
            "--need-id",
            "42",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "4 needs" in result.output


# --------------------------------------------------------------------------
# argument validation / safety
# --------------------------------------------------------------------------


def test_requires_a_program_or_need_id(api, cli_env):
    result = runner.invoke(app, ["reports", "attendance"])
    assert result.exit_code != 0
    assert "--program" in result.output
    assert not api.calls


def test_year_conflicts_with_explicit_bounds(api, cli_env):
    result = runner.invoke(
        app,
        [
            "reports",
            "attendance",
            "--need-id",
            "42",
            "--year",
            "2026",
            "--start",
            "2026-06-01",
        ],
    )
    assert result.exit_code != 0
    assert "--year" in result.output
    assert not api.calls


def test_works_in_read_only_mode(api, cli_env, monkeypatch):
    """The report only reads, so the write guard must never fire."""
    monkeypatch.setenv("GALAXY_READ_ONLY", "1")
    api.get("/hours").mock(side_effect=pages([hour(1, 7, "2026-01-05")]))
    result = runner.invoke(
        app, ["--read-only", "--json", "reports", "attendance", "--need-id", "42"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["rows"][0]["user_id"] == 7


def test_reports_makes_no_write_requests(api, cli_env):
    api.get("/needs").mock(side_effect=pages([HOLLYWOOD]))
    api.get("/hours").mock(side_effect=pages([hour(1, 7, "2026-01-05")]))
    result = runner.invoke(app, ["reports", "attendance", "--program", "hollywood"])
    assert result.exit_code == 0, result.output
    assert {call.request.method for call in api.calls} == {"GET"}
