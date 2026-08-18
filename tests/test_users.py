"""Users resource + ``galaxy users`` CLI.

Every write in this file is mocked with respx. Nothing here may ever reach
the production API.
"""

import json

import pytest
from typer.testing import CliRunner

from galaxy_digital_cli.cli import app
from galaxy_digital_cli.client import GalaxyClient
from galaxy_digital_cli.exceptions import ReadOnlyError
from galaxy_digital_cli.models.common import (
    AgencyMini,
    BenchmarkMini,
    Cause,
    Extra,
    GroupMini,
    Interest,
    Tag,
    TrackMini,
)
from galaxy_digital_cli.models.hours import Hour
from galaxy_digital_cli.models.users import (
    RegistrationAnswer,
    User,
    UserOneclick,
    UserOptouts,
    UserQualification,
    UserResponse,
)
from galaxy_digital_cli.resources.users import Users

from .conftest import BASE

runner = CliRunner()

USER_ROW = {
    "id": "5",
    "domain_id": "1",
    "user_fname": "Ada",
    "user_lname": "Lovelace",
    "user_email": "ada@example.com",
    "user_status": "active",
}


@pytest.fixture
def cli_env(monkeypatch):
    """Point the CLI's lazily-built client at the respx mock."""
    monkeypatch.setenv("GALAXY_API_URL", "https://api.test/api")


# --------------------------------------------------------------------------
# models
# --------------------------------------------------------------------------


def test_user_model_fields():
    user = User.model_validate(USER_ROW)
    assert user.id == 5
    assert user.user_fname == "Ada"
    # every documented field exists, ids coerced from the API's strings
    for field in (
        "domain_sitename",
        "user_reference_id",
        "user_mname",
        "user_phone",
        "user_phone_cell",
        "user_username",
        "user_address",
        "user_address2",
        "user_city",
        "user_state",
        "user_postal",
        "user_county",
        "user_country",
        "user_age_range",
        "user_disaster",
        "user_birthday",
        "user_company",
        "user_company_title",
        "user_department",
        "user_ethnicity",
        "user_gender",
        "user_grad_semester",
        "user_grad_year",
        "user_notes",
        "user_comments",
        "created_at",
        "updated_at",
    ):
        assert field in User.model_fields
    assert len(User.model_fields) == 33


def test_hour_model_nested():
    hour = Hour.model_validate(
        {
            "id": "3",
            "hour_hours": "2.5",
            "hour_status": "approved",
            "user": {"id": "5", "user_fname": "Ada"},
            "need": {"id": "9", "need_title": "Sort cans"},
            "groups": [{"id": "2", "group_title": "Team"}],
        }
    )
    assert hour.id == 3
    assert hour.user and hour.user.user_fname == "Ada"
    assert hour.need and hour.need.need_title == "Sort cans"
    assert hour.groups and hour.groups[0].group_title == "Team"
    assert len(Hour.model_fields) == 20


def test_hour_groups_tolerates_bare_object():
    """doc/api.yml declares `groups` as a bare object; the API sends a list."""
    single = Hour.model_validate({"id": 1, "groups": {"id": 2}})
    assert single.groups == [GroupMini(id=2)]

    listed = Hour.model_validate({"id": 1, "groups": [{"id": 2}, {"id": 3}]})
    assert listed.groups == [GroupMini(id=2), GroupMini(id=3)]


def test_small_user_models():
    assert BenchmarkMini.model_validate({"id": "1", "update_at": "x"}).update_at == "x"
    assert UserOneclick.model_validate({"link": "http://x/"}).link == "http://x/"
    opt = UserOptouts.model_validate({"id": "2", "optout_areas": ["blast"]})
    assert opt.optout_areas == ["blast"]
    qual = UserQualification.model_validate({"id": "1", "qualification_id": "7"})
    assert qual.qualification_id == 7
    resp = UserResponse.model_validate({"id": "1", "need_id": "8"})
    assert resp.need_id == 8
    answer = RegistrationAnswer.model_validate({"question_id": "4", "answer": "blue"})
    assert answer.question_id == 4 and answer.answer == "blue"


# --------------------------------------------------------------------------
# resource: URL + verb mapping
# --------------------------------------------------------------------------


def test_crud(client, api):
    api.get("/users/5").respond(json={"data": USER_ROW})
    assert Users(client).get(5).user_email == "ada@example.com"

    created = api.post("/users").respond(json={"data": USER_ROW})
    assert Users(client).create(user_fname="Ada").id == 5
    assert json.loads(created.calls.last.request.content) == {"user_fname": "Ada"}

    updated = api.put("/users/5").respond(json={})
    Users(client).update(5, user_lname="L")
    assert json.loads(updated.calls.last.request.content) == {"user_lname": "L"}

    removed = api.delete("/users/5").respond(status_code=204)
    Users(client).delete(5)
    assert removed.called


def test_list_filter_mapping(client, api):
    route = api.get("/users").respond(json={"data": [USER_ROW]})
    rows = list(
        Users(client).list(
            user_status="active",
            user_email_like="@example.com",
            user_fname_like="Ad",
            user_lname_like="Love",
            show_inactive=True,
        )
    )
    assert isinstance(rows[0], User)
    params = route.calls.last.request.url.params
    assert params["user_status"] == "active"
    assert params["user_email_like"] == "@example.com"
    assert params["user_fname_like"] == "Ad"
    assert params["user_lname_like"] == "Love"
    assert params["show_inactive"] == "Yes"
    assert params["per_page"] == "150"


@pytest.mark.parametrize(
    "call,method,path,model",
    [
        (lambda u: u.agencies(5), "GET", "/users/5/agencies", AgencyMini),
        (lambda u: u.benchmarks(5), "GET", "/users/5/benchmarks", BenchmarkMini),
        (lambda u: u.causes(5), "GET", "/users/5/causes", Cause),
        (lambda u: u.extras(5), "GET", "/users/5/extras", Extra),
        (lambda u: u.hours(5), "GET", "/users/5/hours", Hour),
        (lambda u: u.interests(5), "GET", "/users/5/interests", Interest),
        (
            lambda u: u.qualifications(5),
            "GET",
            "/users/5/qualifications",
            UserQualification,
        ),
        (
            lambda u: u.registration_answers(5),
            "GET",
            "/users/5/registrationQuestions",
            RegistrationAnswer,
        ),
        (lambda u: u.responses(5), "GET", "/users/5/responses", UserResponse),
        (lambda u: u.tracks(5), "GET", "/users/5/tracks", TrackMini),
        (lambda u: u.tags(5), "GET", "/users/5/tags", Tag),
    ],
)
def test_sublists(client, api, call, method, path, model):
    route = api.request(method, path).respond(json={"data": [{"id": "1"}]})
    rows = call(Users(client))
    assert route.called
    assert isinstance(rows[0], model)


@pytest.mark.parametrize(
    "call,method,path",
    [
        (lambda u: u.add_agency(5, 2), "POST", "/users/5/agencies/2"),
        (lambda u: u.remove_agency(5, 2), "DELETE", "/users/5/agencies/2"),
        (lambda u: u.remove_benchmark(5, 3), "DELETE", "/users/5/benchmarks/3"),
        (lambda u: u.add_cause(5, 4), "POST", "/users/5/causes/4"),
        (lambda u: u.remove_cause(5, 4), "DELETE", "/users/5/causes/4"),
        (lambda u: u.add_interest(5, 6), "POST", "/users/5/interests/6"),
        (lambda u: u.remove_interest(5, 6), "DELETE", "/users/5/interests/6"),
        (lambda u: u.remove_tag(5, 7), "DELETE", "/users/5/tags/7"),
        (lambda u: u.send_welcome_email(5), "GET", "/users/5/welcomeEmail"),
    ],
)
def test_relationship_writes(client, api, call, method, path):
    route = api.request(method, path).respond(status_code=204)
    call(Users(client))
    assert route.called


def test_send_welcome_email_respects_read_only(api):
    """GET .../welcomeEmail sends mail, so it must honor read-only mode too."""
    read_only_client = GalaxyClient(api_key="k", base_url=BASE, read_only=True)
    with pytest.raises(ReadOnlyError):
        Users(read_only_client).send_welcome_email(5)
    assert not api.calls


def test_singletons(client, api):
    api.get("/users/5/oneclick").respond(
        json={"data": {"link": "https://x/oneclick/abc/", "expires": "2022-01-14"}}
    )
    one = Users(client).oneclick(5)
    assert isinstance(one, UserOneclick) and one.link.endswith("/abc/")

    api.get("/users/5/optouts").respond(
        json={"data": {"id": "5", "optout_areas": ["blast"]}}
    )
    outs = Users(client).optouts(5)
    assert isinstance(outs, UserOptouts) and outs.optout_areas == ["blast"]


def test_extras_subset_and_body(client, api):
    route = api.get("/users/5/extras").respond(
        json={"data": [{"key": "Language", "value": "Spanish"}]}
    )
    rows = Users(client).extras(5, subset="profile")
    assert rows[0].value == "Spanish"
    assert route.calls.last.request.url.params["subset"] == "profile"

    post = api.post("/users/5/extras").respond(status_code=201)
    body = {"extras": [{"key": "Language", "value": "Spanish"}]}
    Users(client).set_extras(5, body, subset="profile")
    assert json.loads(post.calls.last.request.content) == body
    assert post.calls.last.request.url.params["subset"] == "profile"

    # the bare list form is wrapped in the same envelope
    Users(client).set_extras(
        5, [{"key": "Language", "value": "Spanish"}], subset="profile"
    )
    assert json.loads(post.calls.last.request.content) == body
    assert post.calls.last.request.url.params["subset"] == "profile"


def test_extras_lone_object_is_wrapped(client, api):
    api.get("/users/5/extras").respond(json={"data": {"key": "k", "value": "v"}})
    rows = Users(client).extras(5)
    assert [r.key for r in rows] == ["k"]


def test_extras_404_is_empty(client, api):
    api.get("/users/5/extras").respond(status_code=404)
    assert Users(client).extras(5) == []


def test_sublist_404_is_empty(client, api):
    api.get("/users/5/hours").respond(status_code=404)
    assert Users(client).hours(5) == []


def test_add_tags_body(client, api):
    route = api.post("/users/5/tags").respond(status_code=201)
    Users(client).add_tags(5, ["Tag 1", "Tag 2"])
    assert json.loads(route.calls.last.request.content) == {"tags": ["Tag 1", "Tag 2"]}


def test_optout_bodies(client, api):
    post = api.post("/users/5/optouts").respond(status_code=201)
    Users(client).add_optout(5, optout_areas=["blast"])
    assert json.loads(post.calls.last.request.content) == {"optout_areas": ["blast"]}

    delete = api.delete("/users/5/optouts").respond(status_code=204)
    Users(client).remove_optout(5, optout_areas=["blast"])
    assert json.loads(delete.calls.last.request.content) == {"optout_areas": ["blast"]}


def test_set_registration_answers_body(client, api):
    route = api.post("/users/5/registrationQuestions").respond(status_code=201)
    answers = [{"question_id": "431255", "answer": ["First answer"]}]
    Users(client).set_registration_answers(5, answers)
    assert json.loads(route.calls.last.request.content) == {"answers": answers}


def test_client_attaches_namespace(client):
    assert isinstance(client.users, Users)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def test_cli_list_json(api, cli_env):
    api.get("/users").respond(json={"data": [USER_ROW]})
    result = runner.invoke(app, ["--json", "users", "list", "--status", "active"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["user_email"] == "ada@example.com"


def test_cli_list_status_repeatable(api, cli_env):
    route = api.get("/users").respond(json={"data": [USER_ROW]})
    result = runner.invoke(
        app,
        ["users", "list", "--status", "active", "--status", "pending"],
    )
    assert result.exit_code == 0, result.output
    assert route.calls.last.request.url.params.get_list("user_status") == [
        "active",
        "pending",
    ]


def test_cli_list_passes_filters(api, cli_env):
    route = api.get("/users").respond(json={"data": [USER_ROW]})
    result = runner.invoke(
        app,
        [
            "users",
            "list",
            "--email-like",
            "@example.com",
            "--fname",
            "Ada",
            "--show-inactive",
            "--per-page",
            "10",
        ],
    )
    assert result.exit_code == 0, result.output
    params = route.calls.last.request.url.params
    assert params["user_email_like"] == "@example.com"
    assert params["user_fname"] == "Ada"
    assert params["show_inactive"] == "Yes"
    assert params["per_page"] == "10"


def test_cli_get(api, cli_env):
    api.get("/users/5").respond(json={"data": USER_ROW})
    result = runner.invoke(app, ["users", "get", "5"])
    assert result.exit_code == 0, result.output
    assert "ada@example.com" in result.output


def test_cli_create_declined_makes_no_request(api, cli_env):
    # No route is registered on purpose: a request would not merely fail the
    # `api.calls` assertion, it would have nothing to answer it.
    result = runner.invoke(app, ["users", "create", "--email", "a@b.c"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls


def test_cli_create_confirmed(api, cli_env):
    route = api.post("/users").respond(json={"data": USER_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "users",
            "create",
            "--fname",
            "Ada",
            "--lname",
            "Lovelace",
            "--email",
            "a@b.c",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "user_fname": "Ada",
        "user_lname": "Lovelace",
        "user_email": "a@b.c",
    }


def test_cli_update_merges_data(api, cli_env):
    route = api.put("/users/5").respond(json={"data": USER_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "users",
            "update",
            "5",
            "--fname",
            "Ada",
            "--data",
            '{"user_city":"X"}',
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "user_fname": "Ada",
        "user_city": "X",
    }


def test_cli_delete_declined_makes_no_request(api, cli_env):
    result = runner.invoke(app, ["users", "delete", "5"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls


def test_cli_delete_confirmed(api, cli_env):
    route = api.delete("/users/5").respond(status_code=204)
    result = runner.invoke(app, ["users", "delete", "5"], input="y\n")
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_remove_tag_confirmed(api, cli_env):
    route = api.delete("/users/5/tags/7").respond(status_code=204)
    result = runner.invoke(app, ["--yes", "users", "remove-tag", "5", "7"])
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_welcome_email_prompts(api, cli_env):
    declined = runner.invoke(app, ["users", "welcome-email", "5"], input="n\n")
    assert declined.exit_code != 0
    assert not api.calls


def test_cli_welcome_email_confirmed(api, cli_env):
    route = api.get("/users/5/welcomeEmail").respond(status_code=201)
    result = runner.invoke(app, ["--yes", "users", "welcome-email", "5"])
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_add_agency(api, cli_env):
    route = api.post("/users/5/agencies/2").respond(status_code=200)
    result = runner.invoke(app, ["--yes", "users", "add-agency", "5", "2"])
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_add_tags(api, cli_env):
    route = api.post("/users/5/tags").respond(status_code=201)
    result = runner.invoke(app, ["--yes", "users", "add-tags", "5", "Tag 1", "Tag 2"])
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {"tags": ["Tag 1", "Tag 2"]}


def test_cli_remove_tag_declined(api, cli_env):
    result = runner.invoke(app, ["users", "remove-tag", "5", "7"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls


def test_cli_set_extras(api, cli_env):
    route = api.post("/users/5/extras").respond(status_code=201)
    body = '{"extras": [{"key": "Language", "value": "Spanish"}]}'
    result = runner.invoke(
        app,
        ["--yes", "users", "set-extras", "5", "--data", body, "--subset", "profile"],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == json.loads(body)
    assert route.calls.last.request.url.params["subset"] == "profile"


def test_cli_add_and_remove_optout(api, cli_env):
    post = api.post("/users/5/optouts").respond(status_code=201)
    body = '{"optout_areas": ["blast"]}'
    assert (
        runner.invoke(
            app, ["--yes", "users", "add-optout", "5", "--data", body]
        ).exit_code
        == 0
    )
    assert json.loads(post.calls.last.request.content) == {"optout_areas": ["blast"]}

    delete = api.delete("/users/5/optouts").respond(status_code=204)
    assert (
        runner.invoke(
            app, ["--yes", "users", "remove-optout", "5", "--data", body]
        ).exit_code
        == 0
    )
    assert delete.called


def test_cli_set_registration_questions(api, cli_env):
    route = api.post("/users/5/registrationQuestions").respond(status_code=201)
    body = '{"answers": [{"question_id": "1", "answer": ["blue"]}]}'
    result = runner.invoke(
        app, ["--yes", "users", "set-registration-questions", "5", "--data", body]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == json.loads(body)


def test_cli_set_registration_questions_requires_answers(api, cli_env):
    result = runner.invoke(
        app, ["--yes", "users", "set-registration-questions", "5", "--data", "{}"]
    )
    assert result.exit_code != 0
    assert not api.calls


@pytest.mark.parametrize(
    "args,path,payload",
    [
        (["agencies", "5"], "/users/5/agencies", {"data": [{"id": "1"}]}),
        (["benchmarks", "5"], "/users/5/benchmarks", {"data": [{"id": "1"}]}),
        (["causes", "5"], "/users/5/causes", {"data": [{"id": "1"}]}),
        (["extras", "5"], "/users/5/extras", {"data": [{"key": "k"}]}),
        (["hours", "5"], "/users/5/hours", {"data": [{"id": "1"}]}),
        (["interests", "5"], "/users/5/interests", {"data": [{"id": "1"}]}),
        (["qualifications", "5"], "/users/5/qualifications", {"data": [{"id": "1"}]}),
        (
            ["registration-questions", "5"],
            "/users/5/registrationQuestions",
            {"data": [{"question": "q"}]},
        ),
        (["responses", "5"], "/users/5/responses", {"data": [{"id": "1"}]}),
        (["tracks", "5"], "/users/5/tracks", {"data": [{"id": "1"}]}),
        (["tags", "5"], "/users/5/tags", {"data": [{"id": "1"}]}),
        (
            ["oneclick", "5"],
            "/users/5/oneclick",
            {"data": {"link": "https://x/oneclick/abc/"}},
        ),
        (["optouts", "5"], "/users/5/optouts", {"data": {"id": "5"}}),
    ],
)
def test_cli_read_commands(api, cli_env, args, path, payload):
    route = api.get(path).respond(json=payload)
    result = runner.invoke(app, ["users", *args])
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_remove_commands(api, cli_env):
    for args, method, path in [
        (["remove-agency", "5", "2"], "DELETE", "/users/5/agencies/2"),
        (["remove-benchmark", "5", "3"], "DELETE", "/users/5/benchmarks/3"),
        (["add-cause", "5", "4"], "POST", "/users/5/causes/4"),
        (["remove-cause", "5", "4"], "DELETE", "/users/5/causes/4"),
        (["add-interest", "5", "6"], "POST", "/users/5/interests/6"),
        (["remove-interest", "5", "6"], "DELETE", "/users/5/interests/6"),
    ]:
        route = api.request(method, path).respond(status_code=204)
        result = runner.invoke(app, ["--yes", "users", *args])
        assert result.exit_code == 0, result.output
        assert route.called


def test_cli_help_lists_every_command():
    out = runner.invoke(app, ["users", "--help"]).output
    for command in (
        "list",
        "get",
        "create",
        "update",
        "delete",
        "agencies",
        "add-agency",
        "remove-agency",
        "benchmarks",
        "remove-benchmark",
        "causes",
        "add-cause",
        "remove-cause",
        "extras",
        "set-extras",
        "hours",
        "interests",
        "add-interest",
        "remove-interest",
        "welcome-email",
        "oneclick",
        "optouts",
        "add-optout",
        "remove-optout",
        "qualifications",
        "registration-questions",
        "set-registration-questions",
        "responses",
        "tracks",
        "tags",
        "add-tags",
        "remove-tag",
    ):
        assert command in out
