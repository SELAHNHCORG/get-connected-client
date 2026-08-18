"""Responses, teams and groups resources + their ``galaxy`` CLI commands.

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
from galaxy_digital_cli.models.groups import Group, GroupUser
from galaxy_digital_cli.models.responses import Response
from galaxy_digital_cli.models.teams import Team, TeamMember
from galaxy_digital_cli.resources.groups import Groups
from galaxy_digital_cli.resources.responses import Responses
from galaxy_digital_cli.resources.teams import Teams


runner = CliRunner()

RESPONSE_ROW = {
    "id": "7",
    "domain_id": "1",
    "response_status": "confirmed",
    "response_date_added": "2024-03-01 12:00:00",
}

TEAM_ROW = {
    "id": "3",
    "domain_id": "1",
    "team_title": "Park Crew",
    "team_status": "active",
}

GROUP_ROW = {
    "id": "9",
    "domain_id": "1",
    "ug_title": "Rotary Club",
    "ug_status": "active",
}


@pytest.fixture
def cli_env(monkeypatch):
    """Point the CLI's lazily-built client at the respx mock."""
    monkeypatch.setenv("GALAXY_API_URL", "https://api.test/api")


# --------------------------------------------------------------------------
# models
# --------------------------------------------------------------------------


def test_team_model_fields():
    team = Team.model_validate(TEAM_ROW)
    assert team.id == 3
    assert team.team_title == "Park Crew"
    for field in (
        "domain_id",
        "team_status",
        "team_description",
        "creator",
        "agency",
        "need",
        "members",
    ):
        assert field in Team.model_fields
    assert len(Team.model_fields) == 9


def test_team_nested_fields_parse():
    team = Team.model_validate(
        {
            "id": "3",
            "creator": {"id": "4", "user_fname": "Mary"},
            "agency": {"id": "9", "agency_name": "Helping Hands"},
            "need": {"id": "42", "need_title": "Park Cleanup"},
            "members": [
                {"id": "4", "user_fname": "Mary", "leader": "Yes"},
            ],
        }
    )
    assert team.creator.user_fname == "Mary"
    assert team.agency.agency_name == "Helping Hands"
    assert team.need.need_title == "Park Cleanup"
    assert isinstance(team.members[0], TeamMember)
    assert team.members[0].leader == "Yes"


def test_team_member_model_fields():
    member = TeamMember.model_validate(
        {"id": "4", "user_fname": "Mary", "leader": "Yes"}
    )
    assert member.id == 4
    for field in ("domain_id", "user_fname", "user_lname", "user_email", "leader"):
        assert field in TeamMember.model_fields
    assert len(TeamMember.model_fields) == 6


def test_group_model_fields():
    group = Group.model_validate(GROUP_ROW)
    assert group.id == 9
    assert group.ug_title == "Rotary Club"
    for field in (
        "domain_id",
        "ug_status",
        "ug_description",
        "ug_description_private",
        "ug_domains",
        "ug_color",
        "ug_text_color",
        "ug_icon",
        "ug_suppress_resume",
        "ug_allow_member_remove",
        "ug_submitted_hours",
        "ug_block_id",
        "ug_limit",
        "ug_goal",
        "ug_approval",
        "created_at",
        "updated_at",
        "needs",
        "users",
        "agencies",
        "questions_reflection",
        "questions_join",
    ):
        assert field in Group.model_fields
    assert len(Group.model_fields) == 24


def test_group_nested_fields_parse():
    group = Group.model_validate(
        {
            "id": "9",
            "needs": [{"id": "42", "need_title": "Park Cleanup"}],
            "users": [{"id": "4", "user_fname": "Mary", "leader": "No"}],
            "agencies": [{"id": "1", "agency_name": "Helping Hands"}],
            "questions_reflection": [{"id": "1", "q_label": "How was it?"}],
            "questions_join": [{"id": "2", "q_label": "Why join?"}],
        }
    )
    assert group.needs[0].need_title == "Park Cleanup"
    assert isinstance(group.users[0], GroupUser)
    assert group.users[0].user_fname == "Mary"
    assert group.agencies[0].agency_name == "Helping Hands"
    assert group.questions_reflection[0].q_label == "How was it?"
    assert group.questions_join[0].q_label == "Why join?"


def test_group_user_model_fields():
    user = GroupUser.model_validate({"id": "4", "user_fname": "Mary", "leader": "No"})
    assert user.id == 4
    for field in ("domain_id", "user_fname", "user_lname", "user_email", "leader"):
        assert field in GroupUser.model_fields
    assert len(GroupUser.model_fields) == 6


# --------------------------------------------------------------------------
# resource: responses -- URL + verb mapping
# --------------------------------------------------------------------------


def test_responses_crud(client, api):
    api.get("/responses/7").respond(json={"data": RESPONSE_ROW})
    assert Responses(client).get(7).response_status == "confirmed"

    created = api.post("/responses").respond(json={"data": RESPONSE_ROW})
    assert Responses(client).create(need_id=42, user_id=4).id == 7
    assert json.loads(created.calls.last.request.content) == {
        "need_id": 42,
        "user_id": 4,
    }

    updated = api.put("/responses/7").respond(json={})
    Responses(client).update(7, response_note="Bring gloves")
    assert json.loads(updated.calls.last.request.content) == {
        "response_note": "Bring gloves"
    }

    removed = api.delete("/responses/7").respond(status_code=204)
    Responses(client).delete(7)
    assert removed.called


def test_responses_list_show_inactive_is_sent(client, api):
    route = api.get("/responses").respond(json={"data": [RESPONSE_ROW]})
    rows = list(Responses(client).list(show_inactive=True))
    assert isinstance(rows[0], Response)
    params = route.calls.last.request.url.params
    assert params["show_inactive"] == "Yes"
    assert params["per_page"] == "150"


def test_responses_create_body(client, api):
    route = api.post("/responses").respond(json={"data": RESPONSE_ROW})
    Responses(client).create(
        need_id=42,
        user_id=4,
        team_id=3,
        schedule_ids=["1"],
        response_note="Bring gloves",
    )
    assert json.loads(route.calls.last.request.content) == {
        "need_id": 42,
        "user_id": 4,
        "team_id": 3,
        "schedule_ids": ["1"],
        "response_note": "Bring gloves",
    }


def test_client_attaches_responses_namespace(client):
    assert isinstance(client.responses, Responses)


def test_responses_covers_every_spec_operation():
    """Keep the class docstring's "5 operations" claim from going stale."""
    endpoints = {
        name
        for name, member in inspect.getmembers(Responses, inspect.isfunction)
        if not name.startswith("_") and name != "url"
    }
    assert len(endpoints) == 5


_COVERED_RESPONSES_PATHS = {"/responses", "/responses/{id}"}


def test_responses_covers_every_spec_path():
    """Guard the class docstring's "2 of 2 paths" claim against spec drift."""
    spec_path = Path(__file__).resolve().parent.parent / "doc" / "api.yml"
    spec = yaml.safe_load(spec_path.read_text())
    spec_responses_paths = {
        path
        for path in spec["paths"]
        if path == "/responses" or path.startswith("/responses/")
    }
    assert _COVERED_RESPONSES_PATHS <= spec_responses_paths, (
        "a covered path no longer exists in the spec"
    )
    assert spec_responses_paths - _COVERED_RESPONSES_PATHS == set()


# --------------------------------------------------------------------------
# resource: teams -- URL + verb mapping
# --------------------------------------------------------------------------


def test_teams_crud(client, api):
    api.get("/teams/3").respond(json={"data": TEAM_ROW})
    assert Teams(client).get(3).team_title == "Park Crew"

    created = api.post("/teams").respond(json={"data": TEAM_ROW})
    assert Teams(client).create(team_title="Park Crew", need_id=42).id == 3
    assert json.loads(created.calls.last.request.content) == {
        "team_title": "Park Crew",
        "need_id": 42,
    }

    removed = api.delete("/teams/3").respond(status_code=204)
    Teams(client).delete(3)
    assert removed.called


def test_teams_has_no_update():
    """The spec defines no ``PUT /teams/{id}``: UpdateMixin must be absent."""
    assert not hasattr(Teams, "update")


def test_client_teams_has_no_update(client):
    assert not hasattr(client.teams, "update")


def test_teams_list_show_inactive_is_sent(client, api):
    route = api.get("/teams").respond(json={"data": [TEAM_ROW]})
    rows = list(Teams(client).list(show_inactive=True))
    assert isinstance(rows[0], Team)
    params = route.calls.last.request.url.params
    assert params["show_inactive"] == "Yes"


@pytest.mark.parametrize(
    "call,method,path,body",
    [
        (lambda t: t.add_member(3, 4), "POST", "/teams/3/member/4", {}),
        (
            lambda t: t.add_member(3, 4, sch_id=99),
            "POST",
            "/teams/3/member/4",
            {"sch_id": 99},
        ),
        (lambda t: t.remove_member(3, 4), "DELETE", "/teams/3/member/4", None),
    ],
)
def test_teams_relationship_writes(client, api, call, method, path, body):
    route = api.request(method, path).respond(status_code=204)
    call(Teams(client))
    assert route.called
    if body is not None:
        assert json.loads(route.calls.last.request.content) == body


def test_client_attaches_teams_namespace(client):
    assert isinstance(client.teams, Teams)


def test_teams_covers_every_spec_operation():
    """Keep the class docstring's "6 operations" claim from going stale."""
    endpoints = {
        name
        for name, member in inspect.getmembers(Teams, inspect.isfunction)
        if not name.startswith("_") and name != "url"
    }
    assert len(endpoints) == 6


_COVERED_TEAMS_PATHS = {"/teams", "/teams/{id}", "/teams/{id}/member/{member}"}


def test_teams_covers_every_spec_path():
    """Guard the class docstring's "3 of 3 paths" claim against spec drift."""
    spec_path = Path(__file__).resolve().parent.parent / "doc" / "api.yml"
    spec = yaml.safe_load(spec_path.read_text())
    spec_teams_paths = {
        path for path in spec["paths"] if path == "/teams" or path.startswith("/teams/")
    }
    assert _COVERED_TEAMS_PATHS <= spec_teams_paths, (
        "a covered path no longer exists in the spec"
    )
    assert spec_teams_paths - _COVERED_TEAMS_PATHS == set()


# --------------------------------------------------------------------------
# resource: groups -- URL + verb mapping
# --------------------------------------------------------------------------


def test_groups_crud(client, api):
    api.get("/groups/9").respond(json={"data": GROUP_ROW})
    assert Groups(client).get(9).ug_title == "Rotary Club"

    created = api.post("/groups").respond(json={"data": GROUP_ROW})
    assert Groups(client).create(ug_title="Rotary Club", ug_status="active").id == 9
    assert json.loads(created.calls.last.request.content) == {
        "ug_title": "Rotary Club",
        "ug_status": "active",
    }

    updated = api.put("/groups/9").respond(json={})
    Groups(client).update(9, ug_status="inactive")
    assert json.loads(updated.calls.last.request.content) == {"ug_status": "inactive"}

    removed = api.delete("/groups/9").respond(status_code=204)
    Groups(client).delete(9)
    assert removed.called


def test_groups_list_show_inactive_is_sent(client, api):
    route = api.get("/groups").respond(json={"data": [GROUP_ROW]})
    rows = list(Groups(client).list(show_inactive=True))
    assert isinstance(rows[0], Group)
    params = route.calls.last.request.url.params
    assert params["show_inactive"] == "Yes"


@pytest.mark.parametrize(
    "call,method,path",
    [
        (lambda g: g.add_need(9, 42), "POST", "/groups/9/needs/42"),
        (lambda g: g.remove_need(9, 42), "DELETE", "/groups/9/needs/42"),
        (lambda g: g.add_user(9, 4), "POST", "/groups/9/users/4"),
        (lambda g: g.remove_user(9, 4), "DELETE", "/groups/9/users/4"),
    ],
)
def test_groups_relationship_writes(client, api, call, method, path):
    route = api.request(method, path).respond(status_code=204)
    call(Groups(client))
    assert route.called


def test_client_attaches_groups_namespace(client):
    assert isinstance(client.groups, Groups)


def test_groups_covers_every_spec_operation():
    """Keep the class docstring's "9 operations" claim from going stale."""
    endpoints = {
        name
        for name, member in inspect.getmembers(Groups, inspect.isfunction)
        if not name.startswith("_") and name != "url"
    }
    assert len(endpoints) == 9


_COVERED_GROUPS_PATHS = {
    "/groups",
    "/groups/{id}",
    "/groups/{id}/needs/{need_id}",
    "/groups/{id}/users/{user_id}",
}


def test_groups_covers_every_spec_path():
    """Guard the class docstring's "4 of 4 paths" claim against spec drift."""
    spec_path = Path(__file__).resolve().parent.parent / "doc" / "api.yml"
    spec = yaml.safe_load(spec_path.read_text())
    spec_groups_paths = {
        path
        for path in spec["paths"]
        if path == "/groups" or path.startswith("/groups/")
    }
    assert _COVERED_GROUPS_PATHS <= spec_groups_paths, (
        "a covered path no longer exists in the spec"
    )
    assert spec_groups_paths - _COVERED_GROUPS_PATHS == set()


# --------------------------------------------------------------------------
# CLI -- responses
# --------------------------------------------------------------------------


def test_cli_responses_list_json(api, cli_env):
    api.get("/responses").respond(json={"data": [RESPONSE_ROW]})
    result = runner.invoke(app, ["--json", "responses", "list"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["response_status"] == "confirmed"


def test_cli_responses_get(api, cli_env):
    api.get("/responses/7").respond(json={"data": RESPONSE_ROW})
    result = runner.invoke(app, ["responses", "get", "7"])
    assert result.exit_code == 0, result.output
    assert "confirmed" in result.output


def test_cli_responses_create_declined_makes_no_request(api, cli_env):
    result = runner.invoke(
        app,
        ["responses", "create", "--need-id", "42", "--user-id", "4"],
        input="n\n",
    )
    assert result.exit_code != 0
    assert not api.calls


def test_cli_responses_create_confirmed(api, cli_env):
    route = api.post("/responses").respond(json={"data": RESPONSE_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "responses",
            "create",
            "--need-id",
            "42",
            "--user-id",
            "4",
            "--team-id",
            "3",
            "--note",
            "Bring gloves",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "need_id": 42,
        "user_id": 4,
        "team_id": 3,
        "response_note": "Bring gloves",
    }


def test_cli_responses_update_merges_data(api, cli_env):
    route = api.put("/responses/7").respond(json={"data": RESPONSE_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "responses",
            "update",
            "7",
            "--note",
            "Bring gloves",
            "--data",
            '{"response_note":"Bring gloves and hat"}',
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "response_note": "Bring gloves and hat"
    }


def test_cli_responses_delete_declined_makes_no_request(api, cli_env):
    result = runner.invoke(app, ["responses", "delete", "7"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls


def test_cli_responses_delete_confirmed(api, cli_env):
    route = api.delete("/responses/7").respond(status_code=204)
    result = runner.invoke(app, ["responses", "delete", "7"], input="y\n")
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_responses_help_lists_every_command():
    out = runner.invoke(app, ["responses", "--help"]).output
    for command in ("list", "get", "create", "update", "delete"):
        assert command in out


# --------------------------------------------------------------------------
# CLI -- teams
# --------------------------------------------------------------------------


def test_cli_teams_list_json(api, cli_env):
    api.get("/teams").respond(json={"data": [TEAM_ROW]})
    result = runner.invoke(app, ["--json", "teams", "list"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["team_title"] == "Park Crew"


def test_cli_teams_get(api, cli_env):
    api.get("/teams/3").respond(json={"data": TEAM_ROW})
    result = runner.invoke(app, ["teams", "get", "3"])
    assert result.exit_code == 0, result.output
    assert "Park Crew" in result.output


def test_cli_teams_create_declined_makes_no_request(api, cli_env):
    result = runner.invoke(
        app, ["teams", "create", "--title", "Park Crew"], input="n\n"
    )
    assert result.exit_code != 0
    assert not api.calls


def test_cli_teams_create_confirmed(api, cli_env):
    route = api.post("/teams").respond(json={"data": TEAM_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "teams",
            "create",
            "--title",
            "Park Crew",
            "--need-id",
            "42",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "team_title": "Park Crew",
        "need_id": 42,
    }


def test_cli_teams_delete_declined_makes_no_request(api, cli_env):
    result = runner.invoke(app, ["teams", "delete", "3"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls


def test_cli_teams_delete_confirmed(api, cli_env):
    route = api.delete("/teams/3").respond(status_code=204)
    result = runner.invoke(app, ["teams", "delete", "3"], input="y\n")
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_teams_add_member_sends(api, cli_env):
    route = api.post("/teams/3/member/4").respond(status_code=201)
    result = runner.invoke(
        app, ["--yes", "teams", "add-member", "3", "4", "--sch-id", "99"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {"sch_id": 99}


def test_cli_teams_remove_member_sends(api, cli_env):
    route = api.delete("/teams/3/member/4").respond(status_code=204)
    result = runner.invoke(app, ["--yes", "teams", "remove-member", "3", "4"])
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_teams_has_no_update_command():
    """``galaxy teams`` must not offer an update subcommand -- the API has
    no ``PUT /teams/{id}``."""
    out = runner.invoke(app, ["teams", "--help"]).output
    assert "update" not in out


def test_cli_teams_help_lists_every_command():
    out = runner.invoke(app, ["teams", "--help"]).output
    for command in (
        "list",
        "get",
        "create",
        "delete",
        "add-member",
        "remove-member",
    ):
        assert command in out


# --------------------------------------------------------------------------
# CLI -- groups
# --------------------------------------------------------------------------


def test_cli_groups_list_json(api, cli_env):
    api.get("/groups").respond(json={"data": [GROUP_ROW]})
    result = runner.invoke(app, ["--json", "groups", "list"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["ug_title"] == "Rotary Club"


def test_cli_groups_get(api, cli_env):
    api.get("/groups/9").respond(json={"data": GROUP_ROW})
    result = runner.invoke(app, ["groups", "get", "9"])
    assert result.exit_code == 0, result.output
    assert "Rotary Club" in result.output


def test_cli_groups_create_declined_makes_no_request(api, cli_env):
    result = runner.invoke(
        app, ["groups", "create", "--title", "Rotary Club"], input="n\n"
    )
    assert result.exit_code != 0
    assert not api.calls


def test_cli_groups_create_confirmed(api, cli_env):
    route = api.post("/groups").respond(json={"data": GROUP_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "groups",
            "create",
            "--title",
            "Rotary Club",
            "--status",
            "active",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "ug_title": "Rotary Club",
        "ug_status": "active",
    }


def test_cli_groups_update_merges_data(api, cli_env):
    route = api.put("/groups/9").respond(json={"data": GROUP_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "groups",
            "update",
            "9",
            "--status",
            "inactive",
            "--data",
            '{"ug_description":"Local service club"}',
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "ug_status": "inactive",
        "ug_description": "Local service club",
    }


def test_cli_groups_delete_declined_makes_no_request(api, cli_env):
    result = runner.invoke(app, ["groups", "delete", "9"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls


def test_cli_groups_delete_confirmed(api, cli_env):
    route = api.delete("/groups/9").respond(status_code=204)
    result = runner.invoke(app, ["groups", "delete", "9"], input="y\n")
    assert result.exit_code == 0, result.output
    assert route.called


@pytest.mark.parametrize(
    "args,method,path",
    [
        (["add-need", "9", "42"], "POST", "/groups/9/needs/42"),
        (["remove-need", "9", "42"], "DELETE", "/groups/9/needs/42"),
        (["add-user", "9", "4"], "POST", "/groups/9/users/4"),
        (["remove-user", "9", "4"], "DELETE", "/groups/9/users/4"),
    ],
)
def test_cli_groups_relationship_commands(api, cli_env, args, method, path):
    route = api.request(method, path).respond(status_code=204)
    result = runner.invoke(app, ["--yes", "groups", *args])
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_groups_remove_user_declined(api, cli_env):
    result = runner.invoke(app, ["groups", "remove-user", "9", "4"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls


def test_cli_groups_help_lists_every_command():
    out = runner.invoke(app, ["groups", "--help"]).output
    for command in (
        "list",
        "get",
        "create",
        "update",
        "delete",
        "add-need",
        "remove-need",
        "add-user",
        "remove-user",
    ):
        assert command in out


def test_cli_write_emits_json(api, cli_env):
    """A 204 write still owes --json a parseable object on stdout."""
    route = api.delete("/responses/7").respond(status_code=204)
    result = runner.invoke(app, ["--json", "--yes", "responses", "delete", "7"])
    assert result.exit_code == 0, result.output
    assert route.called
    assert json.loads(result.output) == {"ok": True}


def test_cli_confirm_prompt_shows_the_wire_path(api, cli_env):
    """The prompt must name the path the request would really have taken."""
    result = runner.invoke(app, ["teams", "remove-member", "3", "4"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls
    assert "DELETE /teams/3/member/4" in result.output


def test_namespaces_attached(client):
    assert isinstance(client.responses, Responses)
    assert isinstance(client.teams, Teams)
    assert isinstance(client.groups, Groups)
