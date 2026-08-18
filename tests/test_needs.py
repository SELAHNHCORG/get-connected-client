"""Needs resource + ``galaxy needs`` CLI.

Every write in this file is mocked with respx. Nothing here may ever reach
the production API.
"""

import inspect
import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from galaxy_digital_cli.cli import app
from galaxy_digital_cli.models.common import Question
from galaxy_digital_cli.models.needs import Need
from galaxy_digital_cli.models.responses import Response
from galaxy_digital_cli.resources.needs import Needs


runner = CliRunner()

NEED_ROW = {
    "id": "42",
    "domain_id": "1",
    "need_title": "Park Cleanup",
    "need_status": "active",
    "need_date": "2024-03-01",
}

RESPONSE_ROW = {
    "id": "7",
    "domain_id": "1",
    "response_status": "confirmed",
    "response_date_added": "2024-03-01 12:00:00",
}


@pytest.fixture
def cli_env(monkeypatch):
    """Point the CLI's lazily-built client at the respx mock."""
    monkeypatch.setenv("GALAXY_API_URL", "https://api.test/api")


# --------------------------------------------------------------------------
# models
# --------------------------------------------------------------------------


def test_need_model_fields():
    need = Need.model_validate(NEED_ROW)
    assert need.id == 42
    assert need.need_title == "Park Cleanup"
    # every documented field exists, ids coerced from the API's strings
    for field in (
        "domain_id",
        "agency",
        "initiative",
        "groups",
        "need_body",
        "need_address",
        "need_address2",
        "need_city",
        "need_state",
        "need_postal",
        "need_type",
        "need_contact",
        "need_response_notify",
        "need_date_type",
        "need_impact_area",
        "need_volunteers_needed",
        "need_public",
        "need_allow_groups",
        "need_hours",
        "need_comments",
        "need_latitude",
        "need_longitude",
        "need_date_close",
        "family_friendly",
        "outdoors",
        "outdoors_plan",
        "accessible",
        "tags",
        "shifts",
        "created_at",
        "background_check_required",
        "updated_at",
    ):
        assert field in Need.model_fields
    assert len(Need.model_fields) == 36


def test_need_nested_fields_parse():
    need = Need.model_validate(
        {
            "id": "1",
            "agency": {"id": "9", "agency_name": "Helping Hands"},
            "initiative": {"id": "3", "init_title": "Spring Clean"},
            "groups": [{"id": "2", "group_title": "Rotary"}],
            "tags": [{"id": "1", "name": "Outdoors"}],
            "shifts": [{"id": "5", "slots": 10}],
        }
    )
    assert need.agency.agency_name == "Helping Hands"
    assert need.initiative.init_title == "Spring Clean"
    assert need.groups[0].group_title == "Rotary"
    assert need.tags[0].name == "Outdoors"
    assert need.shifts[0].slots == 10


def test_response_model_fields():
    response = Response.model_validate(RESPONSE_ROW)
    assert response.id == 7
    assert response.response_status == "confirmed"
    for field in (
        "domain_id",
        "agency",
        "shift",
        "need",
        "user",
        "initiative",
        "team",
        "response_phone",
        "response_address",
        "response_note",
        "response_date_updated",
        "response_source",
        "response_comments",
        "answers",
    ):
        assert field in Response.model_fields
    assert len(Response.model_fields) == 17


def test_response_nested_fields_parse():
    response = Response.model_validate(
        {
            "id": "1",
            "user": {"id": "4", "user_fname": "Mary"},
            "need": {"id": "42", "need_title": "Park Cleanup"},
            "answers": [{"question": "Shirt size?", "answer": "M"}],
        }
    )
    assert response.user.user_fname == "Mary"
    assert response.need.need_title == "Park Cleanup"
    assert response.answers[0].answer == "M"


# --------------------------------------------------------------------------
# resource: URL + verb mapping
# --------------------------------------------------------------------------


def test_crud(client, api):
    api.get("/needs/42").respond(json={"data": NEED_ROW})
    assert Needs(client).get(42).need_title == "Park Cleanup"

    created = api.post("/needs").respond(json={"data": NEED_ROW})
    assert Needs(client).create(need_title="Park Cleanup").id == 42
    assert json.loads(created.calls.last.request.content) == {
        "need_title": "Park Cleanup"
    }

    updated = api.put("/needs/42").respond(json={})
    Needs(client).update(42, need_status="inactive")
    assert json.loads(updated.calls.last.request.content) == {"need_status": "inactive"}

    removed = api.delete("/needs/42").respond(status_code=204)
    Needs(client).delete(42)
    assert removed.called


def test_list_filter_mapping(client, api):
    route = api.get("/needs").respond(json={"data": [NEED_ROW]})
    rows = list(
        Needs(client).list(agency_id=9, need_title="Cleanup", need_status="active")
    )
    assert isinstance(rows[0], Need)
    params = route.calls.last.request.url.params
    assert params["agency_id"] == "9"
    assert params["need_title"] == "Cleanup"
    assert params["need_status"] == "active"
    assert params["per_page"] == "150"


@pytest.mark.parametrize(
    "call,method,path,model",
    [
        (lambda n: n.responses(42), "GET", "/needs/42/responses", Response),
        (lambda n: n.questions(42), "GET", "/needs/42/questions", Question),
    ],
)
def test_sublists(client, api, call, method, path, model):
    route = api.request(method, path).respond(json={"data": [{"id": "1"}]})
    rows = call(Needs(client))
    assert route.called
    assert isinstance(rows[0], model)


@pytest.mark.parametrize(
    "call,method,path",
    [
        (lambda n: n.remove_shift(42, 5), "DELETE", "/needs/42/shifts/5"),
        (lambda n: n.add_interest(42, 4), "POST", "/needs/42/interests/4"),
        (lambda n: n.remove_interest(42, 4), "DELETE", "/needs/42/interests/4"),
        (
            lambda n: n.add_qualification(42, 8),
            "POST",
            "/needs/42/qualifications/8",
        ),
        (
            lambda n: n.remove_qualification(42, 8),
            "DELETE",
            "/needs/42/qualifications/8",
        ),
    ],
)
def test_relationship_writes(client, api, call, method, path):
    route = api.request(method, path).respond(status_code=204)
    call(Needs(client))
    assert route.called


def test_add_shift_body(client, api):
    """The wire body is a `shifts` list of {start, slots, duration} objects.

    `shiftRequestSchema` (slots/start_date/start_time/duration as flat
    fields) is only used inside `needRequestSchema`'s embedded `shifts`
    array on need create/update -- the dedicated `/needs/{id}/shifts`
    endpoint has its own inline schema with a single combined `start`.
    """
    route = api.post("/needs/42/shifts").respond(status_code=201)
    Needs(client).add_shift(
        42, slots=10, start_date="2024-02-28", start_time="12:00:00", duration="120"
    )
    assert json.loads(route.calls.last.request.content) == {
        "shifts": [{"start": "2024-02-28 12:00:00", "slots": 10, "duration": "120"}]
    }


def test_sublist_404_is_empty(client, api):
    api.get("/needs/42/responses").respond(status_code=404)
    assert Needs(client).responses(42) == []


def test_client_attaches_namespace(client):
    assert isinstance(client.needs, Needs)


def test_needs_covers_every_spec_operation():
    """Keep the class docstring's "13 operations" claim from going stale.

    ``url`` is excluded: it builds paths, it is not an endpoint.
    """
    endpoints = {
        name
        for name, member in inspect.getmembers(Needs, inspect.isfunction)
        if not name.startswith("_") and name != "url"
    }
    assert len(endpoints) == 13


#: The paths this namespace covers, taken straight from the (callable,
#: method, path) tables in ``test_sublists`` and ``test_relationship_writes``
#: above, plus the CRUD paths and add_shift's own path, none of which need a
#: parametrization row.
_COVERED_NEEDS_PATHS = {
    "/needs",
    "/needs/{id}",
    "/needs/{id}/responses",
    "/needs/{id}/shifts",
    "/needs/{id}/shifts/{shift_id}",
    "/needs/{id}/interests/{interest_id}",
    "/needs/{id}/qualifications/{qualification_id}",
    "/needs/{id}/questions",
}


def test_needs_covers_every_spec_path():
    """Guard the class docstring's "8 of 8 paths" claim against spec drift.

    Parses ``doc/api.yml`` directly rather than trusting the docstring: this
    namespace excludes nothing, so any ``/needs`` path in the spec must
    appear in ``_COVERED_NEEDS_PATHS``.
    """
    spec_path = Path(__file__).resolve().parent.parent / "doc" / "api.yml"
    spec = yaml.safe_load(spec_path.read_text())
    spec_needs_paths = {
        path for path in spec["paths"] if path == "/needs" or path.startswith("/needs/")
    }

    assert _COVERED_NEEDS_PATHS <= spec_needs_paths, (
        "a covered path no longer exists in the spec"
    )
    assert spec_needs_paths - _COVERED_NEEDS_PATHS == set()


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def test_cli_list_json(api, cli_env):
    api.get("/needs").respond(json={"data": [NEED_ROW]})
    result = runner.invoke(app, ["--json", "needs", "list"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["need_title"] == "Park Cleanup"


def test_cli_list_extra_filters(api, cli_env):
    route = api.get("/needs").respond(json={"data": [NEED_ROW]})
    result = runner.invoke(
        app,
        [
            "needs",
            "list",
            "--agency-id",
            "9",
            "--title",
            "Cleanup",
            "--status",
            "active",
        ],
    )
    assert result.exit_code == 0, result.output
    params = route.calls.last.request.url.params
    assert params["agency_id"] == "9"
    assert params["need_title"] == "Cleanup"
    assert params["need_status"] == "active"


def test_cli_list_agency_id_repeatable(api, cli_env):
    """The spec types ``agency_id`` as an array, so the flag repeats."""
    route = api.get("/needs").respond(json={"data": [NEED_ROW]})
    result = runner.invoke(
        app,
        ["needs", "list", "--agency-id", "9", "--agency-id", "11"],
    )
    assert result.exit_code == 0, result.output
    assert route.calls.last.request.url.params.get_list("agency_id") == ["9", "11"]


def test_cli_list_without_agency_id_omits_the_param(api, cli_env):
    """An empty repeatable must drop out, not send ``agency_id=[]``."""
    route = api.get("/needs").respond(json={"data": [NEED_ROW]})
    result = runner.invoke(app, ["needs", "list"])
    assert result.exit_code == 0, result.output
    assert "agency_id" not in route.calls.last.request.url.params


def test_cli_get(api, cli_env):
    api.get("/needs/42").respond(json={"data": NEED_ROW})
    result = runner.invoke(app, ["needs", "get", "42"])
    assert result.exit_code == 0, result.output
    assert "Park Cleanup" in result.output


def test_cli_create_declined_makes_no_request(api, cli_env):
    # No route is registered on purpose: a request would not merely fail the
    # `api.calls` assertion, it would have nothing to answer it.
    result = runner.invoke(
        app, ["needs", "create", "--title", "Park Cleanup"], input="n\n"
    )
    assert result.exit_code != 0
    assert not api.calls


def test_cli_create_confirmed(api, cli_env):
    route = api.post("/needs").respond(json={"data": NEED_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "needs",
            "create",
            "--title",
            "Park Cleanup",
            "--agency-id",
            "9",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "need_title": "Park Cleanup",
        "agency_id": 9,
    }


def test_cli_update_merges_data(api, cli_env):
    route = api.put("/needs/42").respond(json={"data": NEED_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "needs",
            "update",
            "42",
            "--title",
            "Park Cleanup",
            "--data",
            '{"need_status":"inactive"}',
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "need_title": "Park Cleanup",
        "need_status": "inactive",
    }


def test_cli_delete_declined_makes_no_request(api, cli_env):
    result = runner.invoke(app, ["needs", "delete", "42"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls


def test_cli_delete_confirmed(api, cli_env):
    route = api.delete("/needs/42").respond(status_code=204)
    result = runner.invoke(app, ["needs", "delete", "42"], input="y\n")
    assert result.exit_code == 0, result.output
    assert route.called


@pytest.mark.parametrize(
    "args,path,payload",
    [
        (["responses", "42"], "/needs/42/responses", {"data": [RESPONSE_ROW]}),
        (["questions", "42"], "/needs/42/questions", {"data": [{"id": "1"}]}),
    ],
)
def test_cli_read_commands(api, cli_env, args, path, payload):
    route = api.get(path).respond(json=payload)
    result = runner.invoke(app, ["needs", *args])
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_add_shift_sends(api, cli_env):
    route = api.post("/needs/42/shifts").respond(status_code=201)
    result = runner.invoke(
        app,
        [
            "--yes",
            "needs",
            "add-shift",
            "42",
            "--slots",
            "10",
            "--start-date",
            "2024-02-28",
            "--start-time",
            "12:00:00",
            "--duration",
            "120",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "shifts": [{"start": "2024-02-28 12:00:00", "slots": 10, "duration": "120"}]
    }


def test_cli_add_shift_prompt_shows_the_wire_body(api, cli_env):
    """The prompt must show the ``shifts`` envelope, not the flat options.

    ``test_cli_add_shift_sends`` above pins the body that really goes out;
    a prompt that showed ``start_date``/``start_time`` would be describing
    a request the client never makes.
    """
    declined = runner.invoke(
        app,
        [
            "needs",
            "add-shift",
            "42",
            "--slots",
            "10",
            "--start-date",
            "2024-02-28",
            "--start-time",
            "12:00:00",
            "--duration",
            "120",
        ],
        input="n\n",
    )
    assert declined.exit_code != 0
    assert not api.calls
    # rich wraps and pretty-prints the JSON, so compare on collapsed
    # whitespace rather than an exact substring.
    output = " ".join(declined.output.split())
    assert "POST /needs/42/shifts" in output
    assert '"shifts"' in output
    assert '"start": "2024-02-28 12:00:00"' in output
    assert "start_date" not in output


@pytest.mark.parametrize(
    "args,method,path",
    [
        (["remove-shift", "42", "5"], "DELETE", "/needs/42/shifts/5"),
        (["add-interest", "42", "4"], "POST", "/needs/42/interests/4"),
        (["remove-interest", "42", "4"], "DELETE", "/needs/42/interests/4"),
        (
            ["add-qualification", "42", "8"],
            "POST",
            "/needs/42/qualifications/8",
        ),
        (
            ["remove-qualification", "42", "8"],
            "DELETE",
            "/needs/42/qualifications/8",
        ),
    ],
)
def test_cli_relationship_commands(api, cli_env, args, method, path):
    route = api.request(method, path).respond(status_code=204)
    result = runner.invoke(app, ["--yes", "needs", *args])
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_remove_interest_declined(api, cli_env):
    result = runner.invoke(app, ["needs", "remove-interest", "42", "4"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls


def test_cli_confirm_prompt_shows_the_wire_path(api, cli_env):
    """The prompt must name the path the request would really have taken.

    ``/needs/42/interests/4`` is the path ``test_cli_relationship_commands``
    registers for this same command, so a prompt that drifts from the
    client's URL builder fails here.
    """
    result = runner.invoke(app, ["needs", "remove-interest", "42", "4"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls
    assert "DELETE /needs/42/interests/4" in result.output


@pytest.mark.parametrize(
    "flag,expected",
    [(None, None), ("--show-inactive", "Yes"), ("--no-show-inactive", "No")],
)
def test_cli_show_inactive_is_tri_state(api, cli_env, flag, expected):
    """Omitted means "take the server default", not "send No"."""
    route = api.get("/needs").respond(json={"data": [NEED_ROW]})
    result = runner.invoke(app, ["needs", "list", *([flag] if flag else [])])
    assert result.exit_code == 0, result.output
    params = route.calls.last.request.url.params
    if expected is None:
        assert "show_inactive" not in params
    else:
        assert params["show_inactive"] == expected


def test_cli_write_emits_json(api, cli_env):
    """A 204 write still owes --json a parseable object on stdout."""
    route = api.delete("/needs/42").respond(status_code=204)
    result = runner.invoke(app, ["--json", "--yes", "needs", "delete", "42"])
    assert result.exit_code == 0, result.output
    assert route.called
    assert json.loads(result.output) == {"ok": True}


def test_cli_sublist_json(api, cli_env):
    api.get("/needs/42/responses").respond(json={"data": [RESPONSE_ROW]})
    result = runner.invoke(app, ["--json", "needs", "responses", "42"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["response_status"] == "confirmed"


def test_cli_get_json(api, cli_env):
    api.get("/needs/42").respond(json={"data": NEED_ROW})
    result = runner.invoke(app, ["--json", "needs", "get", "42"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["need_title"] == "Park Cleanup"


def test_cli_help_lists_every_command():
    out = runner.invoke(app, ["needs", "--help"]).output
    for command in (
        "list",
        "get",
        "create",
        "update",
        "delete",
        "responses",
        "questions",
        "add-shift",
        "remove-shift",
        "add-interest",
        "remove-interest",
        "add-qualification",
        "remove-qualification",
    ):
        assert command in out
