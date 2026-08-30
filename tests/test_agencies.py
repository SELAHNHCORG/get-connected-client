"""Agencies resource + ``galaxy agencies`` CLI.

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
from get_connected_client.models.agencies import Agency
from get_connected_client.models.common import Cause, Cluster, Tag, UserMini
from get_connected_client.resources.agencies import Agencies


runner = CliRunner()

AGENCY_ROW = {
    "id": "9",
    "domain_id": "1",
    "agency_name": "Helping Hands",
    "agency_city": "Springfield",
    "agency_state": "IL",
    "agency_status": "active",
}


@pytest.fixture
def cli_env(monkeypatch):
    """Point the CLI's lazily-built client at the respx mock."""
    monkeypatch.setenv("GALAXY_API_URL", "https://api.test/api")


# --------------------------------------------------------------------------
# models
# --------------------------------------------------------------------------


def test_agency_model_fields():
    agency = Agency.model_validate(AGENCY_ROW)
    assert agency.id == 9
    assert agency.agency_name == "Helping Hands"
    # every documented field exists, ids coerced from the API's strings
    for field in (
        "domain_id",
        "agency_link",
        "agency_address",
        "agency_address2",
        "agency_city",
        "agency_state",
        "agency_postal",
        "agency_extra_location",
        "agency_phone",
        "agency_phone_extension",
        "agency_fax",
        "agency_twitter_link",
        "agency_facebook_link",
        "agency_instagram_link",
        "agency_youtube_link",
        "agency_linkedin_link",
        "agency_email",
        "agency_video",
        "agency_url",
        "agency_ein",
        "agency_comments",
        "agency_status",
        "agency_latitude",
        "agency_longitude",
        "agency_contact",
        "agency_contact_title",
        "agency_news",
        "agency_mission",
        "agency_contacts",
        "agency_hours",
        "agency_partner",
        "logo",
        "created_at",
        "updated_at",
    ):
        assert field in Agency.model_fields
    assert len(Agency.model_fields) == 36


def test_agency_contacts_is_a_list():
    agency = Agency.model_validate(
        {"id": "1", "agency_contacts": ["mary@example.com", "kevin@example.com"]}
    )
    assert agency.agency_contacts == ["mary@example.com", "kevin@example.com"]


# --------------------------------------------------------------------------
# resource: URL + verb mapping
# --------------------------------------------------------------------------


def test_crud(client, api):
    api.get("/agencies/9").respond(json={"data": AGENCY_ROW})
    assert Agencies(client).get(9).agency_name == "Helping Hands"

    created = api.post("/agencies").respond(json={"data": AGENCY_ROW})
    assert Agencies(client).create(agency_name="Helping Hands").id == 9
    assert json.loads(created.calls.last.request.content) == {
        "agency_name": "Helping Hands"
    }

    updated = api.put("/agencies/9").respond(json={})
    Agencies(client).update(9, agency_city="Shelbyville")
    assert json.loads(updated.calls.last.request.content) == {
        "agency_city": "Shelbyville"
    }

    removed = api.delete("/agencies/9").respond(status_code=204)
    Agencies(client).delete(9)
    assert removed.called


def test_list_filter_mapping(client, api):
    route = api.get("/agencies").respond(json={"data": [AGENCY_ROW]})
    rows = list(Agencies(client).list(show_inactive=True))
    assert isinstance(rows[0], Agency)
    params = route.calls.last.request.url.params
    assert params["show_inactive"] == "Yes"
    assert params["per_page"] == "150"


@pytest.mark.parametrize(
    "call,method,path,model",
    [
        (lambda a: a.causes(9), "GET", "/agencies/9/causes", Cause),
        (lambda a: a.clusters(9), "GET", "/agencies/9/clusters", Cluster),
        (lambda a: a.managers(9), "GET", "/agencies/9/managers", UserMini),
        (lambda a: a.tags(9), "GET", "/agencies/9/tags", Tag),
    ],
)
def test_sublists(client, api, call, method, path, model):
    route = api.request(method, path).respond(json={"data": [{"id": "1"}]})
    rows = call(Agencies(client))
    assert route.called
    assert isinstance(rows[0], model)


@pytest.mark.parametrize(
    "call,method,path",
    [
        (lambda a: a.add_cause(9, 4), "POST", "/agencies/9/causes/4"),
        (lambda a: a.remove_cause(9, 4), "DELETE", "/agencies/9/causes/4"),
        (lambda a: a.add_cluster(9, 3), "POST", "/agencies/9/clusters/3"),
        (lambda a: a.remove_cluster(9, 3), "DELETE", "/agencies/9/clusters/3"),
        (lambda a: a.add_manager(9, 5), "POST", "/agencies/9/managers/5"),
        (lambda a: a.remove_manager(9, 5), "DELETE", "/agencies/9/managers/5"),
        (lambda a: a.remove_tag(9, 7), "DELETE", "/agencies/9/tags/7"),
    ],
)
def test_relationship_writes(client, api, call, method, path):
    route = api.request(method, path).respond(status_code=204)
    call(Agencies(client))
    assert route.called


def test_add_tags_body(client, api):
    route = api.post("/agencies/9/tags").respond(status_code=201)
    Agencies(client).add_tags(9, ["Tag 1", "Tag 2"])
    assert json.loads(route.calls.last.request.content) == {"tags": ["Tag 1", "Tag 2"]}


def test_sublist_404_is_empty(client, api):
    api.get("/agencies/9/causes").respond(status_code=404)
    assert Agencies(client).causes(9) == []


def test_client_attaches_namespace(client):
    assert isinstance(client.agencies, Agencies)


def test_agencies_covers_every_spec_operation():
    """Keep the class docstring's "17 operations" claim from going stale.

    ``url`` is excluded: it builds paths, it is not an endpoint.
    """
    endpoints = {
        name
        for name, member in inspect.getmembers(Agencies, inspect.isfunction)
        if not name.startswith("_") and name != "url"
    }
    assert len(endpoints) == 17


#: The paths this namespace covers, taken straight from the (callable,
#: method, path) tables in ``test_sublists`` and ``test_relationship_writes``
#: above, plus the CRUD paths those tables don't need a parametrization row
#: for.
_COVERED_AGENCIES_PATHS = {
    "/agencies",
    "/agencies/{id}",
    "/agencies/{id}/causes",
    "/agencies/{id}/causes/{cause_id}",
    "/agencies/{id}/clusters",
    "/agencies/{id}/clusters/{cluster_id}",
    "/agencies/{id}/managers",
    "/agencies/{id}/managers/{user_id}",
    "/agencies/{id}/tags",
    "/agencies/{id}/tags/{tag_id}",
}


def test_agencies_covers_every_spec_path():
    """Guard the class docstring's "10 of 10 paths" claim against spec drift.

    Parses ``doc/api.yml`` directly rather than trusting the docstring: this
    namespace excludes nothing, unlike users, so any ``/agencies`` path in
    the spec must appear in ``_COVERED_AGENCIES_PATHS``.
    """
    spec_path = Path(__file__).resolve().parent.parent / "doc" / "api.yml"
    spec = yaml.safe_load(spec_path.read_text())
    spec_agencies_paths = {
        path
        for path in spec["paths"]
        if path == "/agencies" or path.startswith("/agencies/")
    }

    assert _COVERED_AGENCIES_PATHS <= spec_agencies_paths, (
        "a covered path no longer exists in the spec"
    )
    assert spec_agencies_paths - _COVERED_AGENCIES_PATHS == set()


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def test_cli_list_json(api, cli_env):
    api.get("/agencies").respond(json={"data": [AGENCY_ROW]})
    result = runner.invoke(app, ["--json", "agencies", "list"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["agency_name"] == "Helping Hands"


def test_cli_get(api, cli_env):
    api.get("/agencies/9").respond(json={"data": AGENCY_ROW})
    result = runner.invoke(app, ["agencies", "get", "9"])
    assert result.exit_code == 0, result.output
    assert "Helping Hands" in result.output


def test_cli_create_declined_makes_no_request(api, cli_env):
    # No route is registered on purpose: a request would not merely fail the
    # `api.calls` assertion, it would have nothing to answer it.
    result = runner.invoke(
        app, ["agencies", "create", "--name", "Helping Hands"], input="n\n"
    )
    assert result.exit_code != 0
    assert not api.calls


def test_cli_create_confirmed(api, cli_env):
    route = api.post("/agencies").respond(json={"data": AGENCY_ROW})
    result = runner.invoke(
        app, ["--yes", "agencies", "create", "--name", "Helping Hands"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "agency_name": "Helping Hands"
    }


def test_cli_update_merges_data(api, cli_env):
    route = api.put("/agencies/9").respond(json={"data": AGENCY_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "agencies",
            "update",
            "9",
            "--name",
            "Helping Hands",
            "--data",
            '{"agency_city":"X"}',
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "agency_name": "Helping Hands",
        "agency_city": "X",
    }


def test_cli_delete_declined_makes_no_request(api, cli_env):
    result = runner.invoke(app, ["agencies", "delete", "9"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls


def test_cli_delete_confirmed(api, cli_env):
    route = api.delete("/agencies/9").respond(status_code=204)
    result = runner.invoke(app, ["agencies", "delete", "9"], input="y\n")
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_add_tags(api, cli_env):
    route = api.post("/agencies/9/tags").respond(status_code=201)
    result = runner.invoke(
        app, ["--yes", "agencies", "add-tags", "9", "Tag 1", "Tag 2"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {"tags": ["Tag 1", "Tag 2"]}


@pytest.mark.parametrize(
    "args,path,payload",
    [
        (["causes", "9"], "/agencies/9/causes", {"data": [{"id": "1"}]}),
        (["clusters", "9"], "/agencies/9/clusters", {"data": [{"id": "1"}]}),
        (["managers", "9"], "/agencies/9/managers", {"data": [{"id": "1"}]}),
        (["tags", "9"], "/agencies/9/tags", {"data": [{"id": "1"}]}),
    ],
)
def test_cli_read_commands(api, cli_env, args, path, payload):
    route = api.get(path).respond(json=payload)
    result = runner.invoke(app, ["agencies", *args])
    assert result.exit_code == 0, result.output
    assert route.called


@pytest.mark.parametrize(
    "args,method,path",
    [
        (["add-cause", "9", "4"], "POST", "/agencies/9/causes/4"),
        (["remove-cause", "9", "4"], "DELETE", "/agencies/9/causes/4"),
        (["add-cluster", "9", "3"], "POST", "/agencies/9/clusters/3"),
        (["remove-cluster", "9", "3"], "DELETE", "/agencies/9/clusters/3"),
        (["add-manager", "9", "5"], "POST", "/agencies/9/managers/5"),
        (["remove-manager", "9", "5"], "DELETE", "/agencies/9/managers/5"),
        (["remove-tag", "9", "7"], "DELETE", "/agencies/9/tags/7"),
    ],
)
def test_cli_relationship_commands(api, cli_env, args, method, path):
    route = api.request(method, path).respond(status_code=204)
    result = runner.invoke(app, ["--yes", "agencies", *args])
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_remove_cause_declined(api, cli_env):
    result = runner.invoke(app, ["agencies", "remove-cause", "9", "4"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls


def test_cli_confirm_prompt_shows_the_wire_path(api, cli_env):
    """The prompt must name the path the request would really have taken.

    ``/agencies/9/causes/4`` is the path ``test_cli_relationship_commands``
    registers for this same command, so a prompt that drifts from the
    client's URL builder fails here.
    """
    result = runner.invoke(app, ["agencies", "remove-cause", "9", "4"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls
    assert "DELETE /agencies/9/causes/4" in result.output


@pytest.mark.parametrize(
    "flag,expected",
    [(None, None), ("--show-inactive", "Yes"), ("--no-show-inactive", "No")],
)
def test_cli_show_inactive_is_tri_state(api, cli_env, flag, expected):
    """Omitted means "take the server default", not "send No"."""
    route = api.get("/agencies").respond(json={"data": [AGENCY_ROW]})
    result = runner.invoke(app, ["agencies", "list", *([flag] if flag else [])])
    assert result.exit_code == 0, result.output
    params = route.calls.last.request.url.params
    if expected is None:
        assert "show_inactive" not in params
    else:
        assert params["show_inactive"] == expected


def test_cli_write_emits_json(api, cli_env):
    """A 204 write still owes --json a parseable object on stdout."""
    route = api.delete("/agencies/9").respond(status_code=204)
    result = runner.invoke(app, ["--json", "--yes", "agencies", "delete", "9"])
    assert result.exit_code == 0, result.output
    assert route.called
    assert json.loads(result.output) == {"ok": True}


def test_cli_sublist_json(api, cli_env):
    api.get("/agencies/9/tags").respond(json={"data": [{"id": "1", "name": "VIP"}]})
    result = runner.invoke(app, ["--json", "agencies", "tags", "9"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["name"] == "VIP"


def test_cli_get_json(api, cli_env):
    api.get("/agencies/9").respond(json={"data": AGENCY_ROW})
    result = runner.invoke(app, ["--json", "agencies", "get", "9"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["agency_name"] == "Helping Hands"


def test_cli_help_lists_every_command():
    out = runner.invoke(app, ["agencies", "--help"]).output
    for command in (
        "list",
        "get",
        "create",
        "update",
        "delete",
        "causes",
        "add-cause",
        "remove-cause",
        "clusters",
        "add-cluster",
        "remove-cluster",
        "managers",
        "add-manager",
        "remove-manager",
        "tags",
        "add-tags",
        "remove-tag",
    ):
        assert command in out
