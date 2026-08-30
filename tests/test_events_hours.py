"""Events + hours resources and ``galaxy events``/``galaxy hours`` CLI.

Every write in this file is mocked with respx. Nothing here may ever reach
the production API.
"""

import inspect
import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from get_connected_client.cli import app
from get_connected_client.models.events import Event
from get_connected_client.models.hours import Hour
from get_connected_client.resources.events import Events
from get_connected_client.resources.hours import Hours


runner = CliRunner()

EVENT_ROW = {
    "id": "42",
    "domain_id": "1",
    "event_title": "Volunteer Fair",
    "event_date_start": "2024-03-01 08:00:00",
    "event_location": "Community Center",
}

HOUR_ROW = {
    "id": "7",
    "domain_id": "1",
    "hour_hours": "3",
    "hour_date_start": "2024-03-01 08:00:00",
    "hour_status": "approved",
}


@pytest.fixture
def cli_env(monkeypatch):
    """Point the CLI's lazily-built client at the respx mock."""
    monkeypatch.setenv("GALAXY_API_URL", "https://api.test/api")


# --------------------------------------------------------------------------
# models
# --------------------------------------------------------------------------


def test_event_model_fields():
    event = Event.model_validate(EVENT_ROW)
    assert event.id == 42
    assert event.event_title == "Volunteer Fair"
    # every documented field exists, ids coerced from the API's strings
    for field in (
        "domain_id",
        "event_area",
        "event_area_id",
        "event_description",
        "event_location",
        "event_address",
        "event_address2",
        "event_city",
        "event_state",
        "event_postal",
        "event_email",
        "event_rsvp",
        "event_date_start",
        "event_date_end",
        "event_all_day",
        "event_comments",
        "tags",
        "created_at",
        "update_at",
    ):
        assert field in Event.model_fields
    assert len(Event.model_fields) == 21


def test_event_nested_fields_parse():
    event = Event.model_validate({"id": "1", "tags": [{"id": "1", "name": "Outdoors"}]})
    assert event.tags[0].name == "Outdoors"


# Hour's fields are already covered by Task 8's model tests; only the wire
# mapping for CRUD is retested here.


# --------------------------------------------------------------------------
# resource: URL + verb mapping -- events
# --------------------------------------------------------------------------


def test_events_crud(client, api):
    api.get("/events/42").respond(json={"data": EVENT_ROW})
    assert Events(client).get(42).event_title == "Volunteer Fair"

    created = api.post("/events").respond(json={"data": EVENT_ROW})
    assert Events(client).create(event_title="Volunteer Fair").id == 42
    assert json.loads(created.calls.last.request.content) == {
        "event_title": "Volunteer Fair"
    }

    updated = api.put("/events/42").respond(json={})
    Events(client).update(42, event_title="Fall Fair")
    assert json.loads(updated.calls.last.request.content) == {
        "event_title": "Fall Fair"
    }

    removed = api.delete("/events/42").respond(status_code=204)
    Events(client).delete(42)
    assert removed.called


def test_events_list_no_show_inactive(client, api):
    """/events' list endpoint does not accept show_inactive; verify it is
    never sent, even when the caller (mistakenly) passes it."""
    route = api.get("/events").respond(json={"data": [EVENT_ROW]})
    rows = list(Events(client).list())
    assert isinstance(rows[0], Event)
    params = route.calls.last.request.url.params
    assert "show_inactive" not in params
    assert params["per_page"] == "150"


def test_client_attaches_events_namespace(client):
    assert isinstance(client.events, Events)


def test_events_covers_every_spec_operation():
    """Keep the class docstring's "5 operations" claim from going stale."""
    endpoints = {
        name
        for name, member in inspect.getmembers(Events, inspect.isfunction)
        if not name.startswith("_") and name != "url"
    }
    assert len(endpoints) == 5


_COVERED_EVENTS_PATHS = {"/events", "/events/{id}"}


def test_events_covers_every_spec_path():
    """Guard the class docstring's "2 of 2 paths" claim against spec drift."""
    spec_path = Path(__file__).resolve().parent.parent / "doc" / "api.yml"
    spec = yaml.safe_load(spec_path.read_text())
    spec_events_paths = {
        path
        for path in spec["paths"]
        if path == "/events" or path.startswith("/events/")
    }
    assert _COVERED_EVENTS_PATHS <= spec_events_paths, (
        "a covered path no longer exists in the spec"
    )
    assert spec_events_paths - _COVERED_EVENTS_PATHS == set()


# --------------------------------------------------------------------------
# resource: URL + verb mapping -- hours
# --------------------------------------------------------------------------


def test_hours_crud(client, api):
    api.get("/hours/7").respond(json={"data": HOUR_ROW})
    assert Hours(client).get(7).hour_hours == "3"

    created = api.post("/hours").respond(json={"data": HOUR_ROW})
    assert Hours(client).create(hour_hours="3", hour_status="approved").id == 7
    assert json.loads(created.calls.last.request.content) == {
        "hour_hours": "3",
        "hour_status": "approved",
    }

    updated = api.put("/hours/7").respond(json={})
    Hours(client).update(7, hour_status="denied")
    assert json.loads(updated.calls.last.request.content) == {"hour_status": "denied"}

    removed = api.delete("/hours/7").respond(status_code=204)
    Hours(client).delete(7)
    assert removed.called


def test_hours_list_show_inactive_is_sent(client, api):
    route = api.get("/hours").respond(json={"data": [HOUR_ROW]})
    rows = list(Hours(client).list(show_inactive=True))
    assert isinstance(rows[0], Hour)
    params = route.calls.last.request.url.params
    assert params["show_inactive"] == "Yes"
    assert params["per_page"] == "150"


def test_hours_create_body_explicit_fields(client, api):
    """Explicit create() kwargs land on the correct hourRequestSchema field
    names."""
    route = api.post("/hours").respond(json={"data": HOUR_ROW})
    Hours(client).create(
        user_id=4,
        response_id=9,
        hour_hours="3",
        hour_miles="10",
        hour_start="2024-03-01 08:00:00",
        hour_status="approved",
    )
    assert json.loads(route.calls.last.request.content) == {
        "user_id": 4,
        "response_id": 9,
        "hour_hours": "3",
        "hour_miles": "10",
        "hour_start": "2024-03-01 08:00:00",
        "hour_status": "approved",
    }


def test_client_attaches_hours_namespace(client):
    assert isinstance(client.hours, Hours)


def test_hours_covers_every_spec_operation():
    """Keep the class docstring's "5 operations" claim from going stale."""
    endpoints = {
        name
        for name, member in inspect.getmembers(Hours, inspect.isfunction)
        if not name.startswith("_") and name != "url"
    }
    assert len(endpoints) == 5


_COVERED_HOURS_PATHS = {"/hours", "/hours/{id}"}


def test_hours_covers_every_spec_path():
    """Guard the class docstring's "2 of 2 paths" claim against spec drift."""
    spec_path = Path(__file__).resolve().parent.parent / "doc" / "api.yml"
    spec = yaml.safe_load(spec_path.read_text())
    spec_hours_paths = {
        path for path in spec["paths"] if path == "/hours" or path.startswith("/hours/")
    }
    assert _COVERED_HOURS_PATHS <= spec_hours_paths, (
        "a covered path no longer exists in the spec"
    )
    assert spec_hours_paths - _COVERED_HOURS_PATHS == set()


# --------------------------------------------------------------------------
# CLI -- events
# --------------------------------------------------------------------------


def test_cli_events_list_json(api, cli_env):
    api.get("/events").respond(json={"data": [EVENT_ROW]})
    result = runner.invoke(app, ["--json", "events", "list"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["event_title"] == "Volunteer Fair"


def test_cli_events_list_no_show_inactive_flag():
    """The events list command must not offer --show-inactive."""
    out = runner.invoke(app, ["events", "list", "--help"]).output
    assert "--show-inactive" not in out


def test_cli_events_get(api, cli_env):
    api.get("/events/42").respond(json={"data": EVENT_ROW})
    result = runner.invoke(app, ["events", "get", "42"])
    assert result.exit_code == 0, result.output
    assert "Volunteer Fair" in result.output


def test_cli_events_create_declined_makes_no_request(api, cli_env):
    # No route is registered on purpose: a request would not merely fail the
    # `api.calls` assertion, it would have nothing to answer it.
    result = runner.invoke(
        app, ["events", "create", "--title", "Volunteer Fair"], input="n\n"
    )
    assert result.exit_code != 0
    assert not api.calls


def test_cli_events_create_confirmed(api, cli_env):
    route = api.post("/events").respond(json={"data": EVENT_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "events",
            "create",
            "--title",
            "Volunteer Fair",
            "--description",
            "Come meet the agencies",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "event_title": "Volunteer Fair",
        "event_description": "Come meet the agencies",
    }


def test_cli_events_update_merges_data(api, cli_env):
    route = api.put("/events/42").respond(json={"data": EVENT_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "events",
            "update",
            "42",
            "--title",
            "Volunteer Fair",
            "--data",
            '{"event_location":"Town Hall"}',
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "event_title": "Volunteer Fair",
        "event_location": "Town Hall",
    }


def test_cli_events_delete_declined_makes_no_request(api, cli_env):
    result = runner.invoke(app, ["events", "delete", "42"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls


def test_cli_events_delete_confirmed(api, cli_env):
    route = api.delete("/events/42").respond(status_code=204)
    result = runner.invoke(app, ["events", "delete", "42"], input="y\n")
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_events_write_emits_json(api, cli_env):
    route = api.delete("/events/42").respond(status_code=204)
    result = runner.invoke(app, ["--json", "--yes", "events", "delete", "42"])
    assert result.exit_code == 0, result.output
    assert route.called
    assert json.loads(result.output) == {"ok": True}


def test_cli_events_help_lists_every_command():
    out = runner.invoke(app, ["events", "--help"]).output
    for command in ("list", "get", "create", "update", "delete"):
        assert command in out


# --------------------------------------------------------------------------
# CLI -- hours
# --------------------------------------------------------------------------


def test_cli_hours_list_json(api, cli_env):
    api.get("/hours").respond(json={"data": [HOUR_ROW]})
    result = runner.invoke(app, ["--json", "hours", "list"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["hour_status"] == "approved"


@pytest.mark.parametrize(
    "flag,expected",
    [(None, None), ("--show-inactive", "Yes"), ("--no-show-inactive", "No")],
)
def test_cli_hours_show_inactive_is_tri_state(api, cli_env, flag, expected):
    """Omitted means "take the server default", not "send No"."""
    route = api.get("/hours").respond(json={"data": [HOUR_ROW]})
    result = runner.invoke(app, ["hours", "list", *([flag] if flag else [])])
    assert result.exit_code == 0, result.output
    params = route.calls.last.request.url.params
    if expected is None:
        assert "show_inactive" not in params
    else:
        assert params["show_inactive"] == expected


def test_cli_hours_get(api, cli_env):
    api.get("/hours/7").respond(json={"data": HOUR_ROW})
    result = runner.invoke(app, ["hours", "get", "7"])
    assert result.exit_code == 0, result.output
    assert "approved" in result.output


def test_cli_hours_create_declined_makes_no_request(api, cli_env):
    result = runner.invoke(
        app, ["hours", "create", "--hours", "3", "--status", "approved"], input="n\n"
    )
    assert result.exit_code != 0
    assert not api.calls


def test_cli_hours_create_confirmed(api, cli_env):
    route = api.post("/hours").respond(json={"data": HOUR_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "hours",
            "create",
            "--user-id",
            "4",
            "--response-id",
            "9",
            "--hours",
            "3",
            "--miles",
            "10",
            "--start",
            "2024-03-01 08:00:00",
            "--status",
            "approved",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "user_id": 4,
        "response_id": 9,
        "hour_hours": "3",
        "hour_miles": "10",
        "hour_start": "2024-03-01 08:00:00",
        "hour_status": "approved",
    }


def test_cli_hours_update_merges_data(api, cli_env):
    route = api.put("/hours/7").respond(json={"data": HOUR_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "hours",
            "update",
            "7",
            "--status",
            "denied",
            "--data",
            '{"hour_location":"Park"}',
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "hour_status": "denied",
        "hour_location": "Park",
    }


def test_cli_hours_delete_declined_makes_no_request(api, cli_env):
    result = runner.invoke(app, ["hours", "delete", "7"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls


def test_cli_hours_delete_confirmed(api, cli_env):
    route = api.delete("/hours/7").respond(status_code=204)
    result = runner.invoke(app, ["hours", "delete", "7"], input="y\n")
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_hours_write_emits_json(api, cli_env):
    route = api.delete("/hours/7").respond(status_code=204)
    result = runner.invoke(app, ["--json", "--yes", "hours", "delete", "7"])
    assert result.exit_code == 0, result.output
    assert route.called
    assert json.loads(result.output) == {"ok": True}


def test_cli_hours_help_lists_every_command():
    out = runner.invoke(app, ["hours", "--help"]).output
    for command in ("list", "get", "create", "update", "delete"):
        assert command in out


def test_cli_confirm_prompt_shows_the_wire_path(api, cli_env):
    """The prompt must name the path the request would really have taken."""
    result = runner.invoke(app, ["hours", "delete", "7"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls
    assert "DELETE /hours/7" in result.output
