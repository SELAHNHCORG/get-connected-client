"""Qualifications, benchmarks, clusters, lookups and auth -- the final
resource vertical -- plus a global spec-coverage guard.

Every write in this file is mocked with respx. Nothing here may ever reach
the production API.
"""

import inspect
import json
import shlex
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from get_connected_cli.cli import app
from get_connected_cli.exceptions import ReadOnlyError
from get_connected_cli.models.auth import LoginResult
from get_connected_cli.models.benchmarks import Benchmark
from get_connected_cli.models.common import Cause, Cluster, Impact, Interest, Question
from get_connected_cli.models.qualifications import Qualification, QualificationUser
from get_connected_cli.models.users import User, UserOneclick
from get_connected_cli.resources.auth import Auth
from get_connected_cli.resources.benchmarks import Benchmarks
from get_connected_cli.resources.misc import Clusters, Lookups
from get_connected_cli.resources.qualifications import Qualifications

from .test_agencies import _COVERED_AGENCIES_PATHS
from .test_events_hours import _COVERED_EVENTS_PATHS, _COVERED_HOURS_PATHS
from .test_needs import _COVERED_NEEDS_PATHS
from .test_responses_teams_groups import (
    _COVERED_GROUPS_PATHS,
    _COVERED_RESPONSES_PATHS,
    _COVERED_TEAMS_PATHS,
)
from .test_users import _COVERED_USERS_PATHS

runner = CliRunner()

QUALIFICATION_ROW = {
    "id": "11",
    "domain_id": "1",
    "qualification_title": "Background Check",
    "qualification_status": "active",
    "qualification_type": "select",
}

QUALIFICATION_USER_ROW = {
    "id": "4",
    "domain_id": "1",
    "user_fname": "Mary",
    "user_lname": "Smith",
    "user_email": "mary@example.com",
    "status": "active",
    "expires": "2025-01-01",
}

BENCHMARK_ROW = {
    "id": "5",
    "benchmark_status": "active",
    "benchmark_title": "10 Hours",
    "benchmark_hours": "10",
}

CLUSTER_ROW = {"id": "2", "name": "Downtown"}

CAUSE_ROW = {"id": "1", "name": "Environment"}
INTEREST_ROW = {"id": "1", "name": "Tutoring"}
IMPACT_ROW = {"id": "1", "impact_name": "Education"}
QUESTION_ROW = {"id": "1", "q_label": "Why volunteer?", "q_type": "text"}

LOGIN_ROW = {
    "user": {"id": "4", "user_fname": "Mary", "user_email": "mary@example.com"},
    "token": "abc123",
    "expires": "2025-01-01 12:00:00",
}

ONECLICK_ROW = {
    "link": "https://volunteer.example.com/users/oneclick/xyz/",
    "expires": "2025-01-01 12:00:00",
    "now": "2025-01-01 11:00:00",
}


@pytest.fixture
def cli_env(monkeypatch):
    """Point the CLI's lazily-built client at the respx mock."""
    monkeypatch.setenv("GALAXY_API_URL", "https://api.test/api")


# --------------------------------------------------------------------------
# models
# --------------------------------------------------------------------------


def test_qualification_model_fields():
    qual = Qualification.model_validate(QUALIFICATION_ROW)
    assert qual.id == 11
    assert qual.qualification_title == "Background Check"
    assert len(Qualification.model_fields) == 15


def test_qualification_user_model_fields():
    user = QualificationUser.model_validate(QUALIFICATION_USER_ROW)
    assert user.id == 4
    assert user.user_fname == "Mary"
    assert len(QualificationUser.model_fields) == 7


def test_benchmark_model_fields():
    bm = Benchmark.model_validate(BENCHMARK_ROW)
    assert bm.id == 5
    assert bm.benchmark_title == "10 Hours"
    assert len(Benchmark.model_fields) == 12
    assert "update_at" in Benchmark.model_fields
    assert "updated_at" not in Benchmark.model_fields


def test_login_result_nested_user_parses():
    result = LoginResult.model_validate(LOGIN_ROW)
    assert result.token == "abc123"
    assert result.expires == "2025-01-01 12:00:00"
    assert isinstance(result.user, User)
    assert result.user.id == 4
    assert result.user.user_fname == "Mary"


def test_login_result_user_may_be_absent():
    result = LoginResult.model_validate({"token": "abc123"})
    assert result.user is None


# --------------------------------------------------------------------------
# resource: qualifications -- URL + verb mapping
# --------------------------------------------------------------------------


def test_qualifications_crud(client, api):
    api.get("/qualifications/11").respond(json={"data": QUALIFICATION_ROW})
    assert Qualifications(client).get(11).qualification_title == "Background Check"

    created = api.post("/qualifications").respond(json={"data": QUALIFICATION_ROW})
    assert (
        Qualifications(client)
        .create(qualification_title="Background Check", qualification_status="active")
        .id
        == 11
    )
    assert json.loads(created.calls.last.request.content) == {
        "qualification_title": "Background Check",
        "qualification_status": "active",
    }

    updated = api.put("/qualifications/11").respond(json={})
    Qualifications(client).update(11, qualification_status="inactive")
    assert json.loads(updated.calls.last.request.content) == {
        "qualification_status": "inactive"
    }

    removed = api.delete("/qualifications/11").respond(status_code=204)
    Qualifications(client).delete(11)
    assert removed.called


def test_qualifications_list_show_inactive_is_sent(client, api):
    route = api.get("/qualifications").respond(json={"data": [QUALIFICATION_ROW]})
    rows = list(Qualifications(client).list(show_inactive=True))
    assert isinstance(rows[0], Qualification)
    assert route.calls.last.request.url.params["show_inactive"] == "Yes"


def test_qualifications_users(client, api):
    api.get("/qualifications/11/users").respond(json={"data": [QUALIFICATION_USER_ROW]})
    users = Qualifications(client).users(11)
    assert isinstance(users[0], QualificationUser)
    assert users[0].user_fname == "Mary"


def test_qualifications_users_404_is_empty(client, api):
    api.get("/qualifications/11/users").respond(status_code=404)
    assert Qualifications(client).users(11) == []


def test_client_attaches_qualifications_namespace(client):
    assert isinstance(client.qualifications, Qualifications)


def test_qualifications_covers_every_spec_operation():
    """Keep the class docstring's "6 operations" claim from going stale."""
    endpoints = {
        name
        for name, member in inspect.getmembers(Qualifications, inspect.isfunction)
        if not name.startswith("_") and name != "url"
    }
    assert len(endpoints) == 6


_COVERED_QUALIFICATIONS_PATHS = {
    "/qualifications",
    "/qualifications/{id}",
    "/qualifications/{id}/users",
}


def test_qualifications_covers_every_spec_path():
    """Guard the class docstring's "3 of 3 paths" claim against spec drift."""
    spec_path = Path(__file__).resolve().parent.parent / "doc" / "api.yml"
    spec = yaml.safe_load(spec_path.read_text())
    spec_qual_paths = {
        path
        for path in spec["paths"]
        if path == "/qualifications" or path.startswith("/qualifications/")
    }
    assert _COVERED_QUALIFICATIONS_PATHS <= spec_qual_paths, (
        "a covered path no longer exists in the spec"
    )
    assert spec_qual_paths - _COVERED_QUALIFICATIONS_PATHS == set()


# --------------------------------------------------------------------------
# resource: benchmarks -- URL + verb mapping
# --------------------------------------------------------------------------


def test_benchmarks_crud(client, api):
    api.get("/benchmarks/5").respond(json={"data": BENCHMARK_ROW})
    assert Benchmarks(client).get(5).benchmark_title == "10 Hours"

    created = api.post("/benchmarks").respond(json={"data": BENCHMARK_ROW})
    assert (
        Benchmarks(client).create(benchmark_title="10 Hours", benchmark_hours="10").id
        == 5
    )
    assert json.loads(created.calls.last.request.content) == {
        "benchmark_title": "10 Hours",
        "benchmark_hours": "10",
    }

    updated = api.put("/benchmarks/5").respond(json={})
    Benchmarks(client).update(5, benchmark_status="inactive")
    assert json.loads(updated.calls.last.request.content) == {
        "benchmark_status": "inactive"
    }

    removed = api.delete("/benchmarks/5").respond(status_code=204)
    Benchmarks(client).delete(5)
    assert removed.called


def test_benchmarks_list_show_inactive_is_sent(client, api):
    route = api.get("/benchmarks").respond(json={"data": [BENCHMARK_ROW]})
    rows = list(Benchmarks(client).list(show_inactive=True))
    assert isinstance(rows[0], Benchmark)
    assert route.calls.last.request.url.params["show_inactive"] == "Yes"


def test_benchmarks_users(client, api):
    user_row = {"id": "4", "domain_id": "1", "user_fname": "Mary"}
    api.get("/benchmarks/5/users").respond(json={"data": [user_row]})
    users = Benchmarks(client).users(5)
    assert users[0].user_fname == "Mary"


def test_benchmarks_users_404_is_empty(client, api):
    api.get("/benchmarks/5/users").respond(status_code=404)
    assert Benchmarks(client).users(5) == []


def test_client_attaches_benchmarks_namespace(client):
    assert isinstance(client.benchmarks, Benchmarks)


def test_benchmarks_covers_every_spec_operation():
    """Keep the class docstring's "6 operations" claim from going stale."""
    endpoints = {
        name
        for name, member in inspect.getmembers(Benchmarks, inspect.isfunction)
        if not name.startswith("_") and name != "url"
    }
    assert len(endpoints) == 6


_COVERED_BENCHMARKS_PATHS = {
    "/benchmarks",
    "/benchmarks/{id}",
    "/benchmarks/{id}/users",
}


def test_benchmarks_covers_every_spec_path():
    """Guard the class docstring's "3 of 3 paths" claim against spec drift."""
    spec_path = Path(__file__).resolve().parent.parent / "doc" / "api.yml"
    spec = yaml.safe_load(spec_path.read_text())
    spec_bm_paths = {
        path
        for path in spec["paths"]
        if path == "/benchmarks" or path.startswith("/benchmarks/")
    }
    assert _COVERED_BENCHMARKS_PATHS <= spec_bm_paths, (
        "a covered path no longer exists in the spec"
    )
    assert spec_bm_paths - _COVERED_BENCHMARKS_PATHS == set()


# --------------------------------------------------------------------------
# resource: clusters -- URL + verb mapping, and no get/update
# --------------------------------------------------------------------------


def test_clusters_list_create_delete(client, api):
    route = api.get("/clusters").respond(json={"data": [CLUSTER_ROW]})
    rows = list(Clusters(client).list())
    assert isinstance(rows[0], Cluster)
    assert route.called

    created = api.post("/clusters").respond(json={"data": CLUSTER_ROW})
    assert Clusters(client).create(name="Downtown").id == 2
    assert json.loads(created.calls.last.request.content) == {"name": "Downtown"}

    removed = api.delete("/clusters/2").respond(status_code=204)
    Clusters(client).delete(2)
    assert removed.called


def test_clusters_has_no_get_or_update():
    """The spec defines no ``GET/PUT /clusters/{id}``."""
    assert not hasattr(Clusters, "get")
    assert not hasattr(Clusters, "update")


def test_client_clusters_has_no_get_or_update(client):
    assert not hasattr(client.clusters, "get")
    assert not hasattr(client.clusters, "update")


def test_client_attaches_clusters_namespace(client):
    assert isinstance(client.clusters, Clusters)


def test_clusters_covers_every_spec_operation():
    endpoints = {
        name
        for name, member in inspect.getmembers(Clusters, inspect.isfunction)
        if not name.startswith("_") and name != "url"
    }
    assert len(endpoints) == 3


_COVERED_CLUSTERS_PATHS = {"/clusters", "/clusters/{id}"}


def test_clusters_covers_every_spec_path():
    spec_path = Path(__file__).resolve().parent.parent / "doc" / "api.yml"
    spec = yaml.safe_load(spec_path.read_text())
    spec_cluster_paths = {
        path
        for path in spec["paths"]
        if path == "/clusters" or path.startswith("/clusters/")
    }
    assert _COVERED_CLUSTERS_PATHS <= spec_cluster_paths, (
        "a covered path no longer exists in the spec"
    )
    assert spec_cluster_paths - _COVERED_CLUSTERS_PATHS == set()


# --------------------------------------------------------------------------
# resource: lookups -- causes, interests, impacts, registration questions
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method,path,row,model",
    [
        ("causes", "/causes", CAUSE_ROW, Cause),
        ("interests", "/interests", INTEREST_ROW, Interest),
        ("impacts", "/impacts", IMPACT_ROW, Impact),
        (
            "registration_questions",
            "/questions/registration",
            QUESTION_ROW,
            Question,
        ),
    ],
)
def test_lookups_get(client, api, method, path, row, model):
    route = api.get(path).respond(json={"data": [row]})
    rows = getattr(Lookups(client), method)()
    assert route.called
    assert isinstance(rows[0], model)


@pytest.mark.parametrize(
    "method,path",
    [
        ("causes", "/causes"),
        ("interests", "/interests"),
        ("impacts", "/impacts"),
        ("registration_questions", "/questions/registration"),
    ],
)
def test_lookups_404_is_empty(client, api, method, path):
    api.get(path).respond(status_code=404)
    assert getattr(Lookups(client), method)() == []


def test_client_attaches_lookups_namespace(client):
    assert isinstance(client.lookups, Lookups)


def test_lookups_covers_every_spec_operation():
    endpoints = {
        name
        for name, member in inspect.getmembers(Lookups, inspect.isfunction)
        if not name.startswith("_") and name != "url"
    }
    assert len(endpoints) == 4


_COVERED_LOOKUPS_PATHS = {
    "/causes",
    "/interests",
    "/impacts",
    "/questions/registration",
}


def test_lookups_covers_every_spec_path():
    spec_path = Path(__file__).resolve().parent.parent / "doc" / "api.yml"
    spec = yaml.safe_load(spec_path.read_text())
    spec_lookup_paths = {
        path
        for path in spec["paths"]
        if path in {"/causes", "/interests", "/impacts"}
        or path == "/questions/registration"
    }
    assert _COVERED_LOOKUPS_PATHS <= spec_lookup_paths, (
        "a covered path no longer exists in the spec"
    )
    assert spec_lookup_paths - _COVERED_LOOKUPS_PATHS == set()


# --------------------------------------------------------------------------
# resource: auth -- login / authenticate
# --------------------------------------------------------------------------


def test_auth_login_body_and_parse(client, api):
    route = api.post("/users/login").respond(json={"data": LOGIN_ROW})
    result = Auth(client).login("mary@example.com", "hunter2", key="site-key")
    assert isinstance(result, LoginResult)
    assert result.token == "abc123"
    assert result.user.user_fname == "Mary"
    assert json.loads(route.calls.last.request.content) == {
        "user_email": "mary@example.com",
        "user_password": "hunter2",
        "key": "site-key",
    }


def test_auth_login_without_data_returns_raw_payload(client, api):
    """When the API answers without a ``data`` object, ``login`` falls back
    to returning the raw payload, mirroring ``CreateMixin.create``."""
    api.post("/users/login").respond(json={"message": "ok"})
    result = Auth(client).login("mary@example.com", "hunter2")
    assert result == {"message": "ok"}


def test_auth_login_key_defaults_to_client_api_key(client, api):
    """``key`` is the site key's whole purpose, so it defaults to it."""
    route = api.post("/users/login").respond(json={"data": LOGIN_ROW})
    Auth(client).login("mary@example.com", "hunter2")
    assert json.loads(route.calls.last.request.content) == {
        "user_email": "mary@example.com",
        "user_password": "hunter2",
        "key": "test-key",
    }


def test_auth_login_without_any_key_raises(monkeypatch, api):
    from get_connected_cli.client import GalaxyClient
    from get_connected_cli.exceptions import MissingAPIKeyError

    monkeypatch.delenv("GALAXY_API_KEY", raising=False)
    with GalaxyClient(base_url="https://api.test/api", token="tok") as c:
        with pytest.raises(MissingAPIKeyError):
            Auth(c).login("mary@example.com", "hunter2")
    assert not api.calls


def test_auth_authenticate_body_and_parse(client, api):
    route = api.post("/users/authenticate").respond(json={"data": [ONECLICK_ROW]})
    result = Auth(client).authenticate("mary@example.com", "hunter2")
    assert isinstance(result, list)
    assert isinstance(result[0], UserOneclick)
    assert result[0].link == ONECLICK_ROW["link"]
    assert json.loads(route.calls.last.request.content) == {
        "user_email": "mary@example.com",
        "user_password": "hunter2",
    }


def test_auth_login_blocked_in_read_only(api):
    from get_connected_cli.client import GalaxyClient

    with GalaxyClient(
        api_key="test-key", base_url="https://api.test/api", read_only=True
    ) as ro_client:
        with pytest.raises(ReadOnlyError):
            Auth(ro_client).login("mary@example.com", "hunter2")
    assert not api.calls


def test_auth_authenticate_blocked_in_read_only(api):
    from get_connected_cli.client import GalaxyClient

    with GalaxyClient(
        api_key="test-key", base_url="https://api.test/api", read_only=True
    ) as ro_client:
        with pytest.raises(ReadOnlyError):
            Auth(ro_client).authenticate("mary@example.com", "hunter2")
    assert not api.calls


def test_client_attaches_auth_namespace(client):
    assert isinstance(client.auth, Auth)


def test_auth_covers_every_spec_operation():
    endpoints = {
        name
        for name, member in inspect.getmembers(Auth, inspect.isfunction)
        if not name.startswith("_") and name != "url"
    }
    assert len(endpoints) == 2


def test_auth_covers_login_and_authenticate_paths():
    """The pair excluded from ``Users``'s coverage guard is covered here."""
    spec_path = Path(__file__).resolve().parent.parent / "doc" / "api.yml"
    spec = yaml.safe_load(spec_path.read_text())
    assert {"/users/login", "/users/authenticate"} <= set(spec["paths"])


# --------------------------------------------------------------------------
# global spec coverage: the whole client, 100% of doc/api.yml
# --------------------------------------------------------------------------

# Every path this vertical adds on top of the six prior verticals
# (agencies, needs, events, hours, responses, teams, groups) and users.
_COVERED_BY_THIS_VERTICAL = (
    _COVERED_QUALIFICATIONS_PATHS
    | _COVERED_BENCHMARKS_PATHS
    | _COVERED_CLUSTERS_PATHS
    | _COVERED_LOOKUPS_PATHS
    | {"/users/login", "/users/authenticate"}
)

# The paths every other vertical's own spec-guard test already asserts it
# covers, imported directly from each file's ``_COVERED_*_PATHS`` constant
# so there is a single source of truth per vertical.
_COVERED_BY_OTHER_VERTICALS = (
    _COVERED_AGENCIES_PATHS
    | _COVERED_NEEDS_PATHS
    | _COVERED_EVENTS_PATHS
    | _COVERED_HOURS_PATHS
    | _COVERED_RESPONSES_PATHS
    | _COVERED_TEAMS_PATHS
    | _COVERED_GROUPS_PATHS
    | _COVERED_USERS_PATHS
)


def test_full_api_spec_coverage():
    """The whole client now covers every one of the spec's 66 paths.

    This is the capstone guard for the project: it parses ``doc/api.yml``
    directly and asserts the union of every vertical's covered-path set --
    six prior verticals (hardcoded above, mirroring each file's own
    ``_COVERED_*_PATHS``) plus this one -- equals the full set of paths the
    spec declares. If the spec ever grows a new path, this fails until some
    namespace claims it.
    """
    spec_path = Path(__file__).resolve().parent.parent / "doc" / "api.yml"
    spec = yaml.safe_load(spec_path.read_text())
    all_spec_paths = set(spec["paths"])
    all_covered = _COVERED_BY_OTHER_VERTICALS | _COVERED_BY_THIS_VERTICAL
    assert all_covered <= all_spec_paths, "a covered path no longer exists in the spec"
    assert all_spec_paths - all_covered == set(), (
        "spec paths with no covering namespace"
    )
    assert len(all_spec_paths) == 66


# --------------------------------------------------------------------------
# CLI -- qualifications
# --------------------------------------------------------------------------


def test_cli_qualifications_list_json(api, cli_env):
    api.get("/qualifications").respond(json={"data": [QUALIFICATION_ROW]})
    result = runner.invoke(app, ["--json", "qualifications", "list"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["qualification_title"] == "Background Check"


def test_cli_qualifications_get(api, cli_env):
    api.get("/qualifications/11").respond(json={"data": QUALIFICATION_ROW})
    result = runner.invoke(app, ["qualifications", "get", "11"])
    assert result.exit_code == 0, result.output
    assert "Background Check" in result.output


def test_cli_qualifications_create_declined_makes_no_request(api, cli_env):
    result = runner.invoke(
        app,
        ["qualifications", "create", "--title", "Background Check"],
        input="n\n",
    )
    assert result.exit_code != 0
    assert not api.calls


def test_cli_qualifications_create_confirmed(api, cli_env):
    route = api.post("/qualifications").respond(json={"data": QUALIFICATION_ROW})
    result = runner.invoke(
        app,
        ["--yes", "qualifications", "create", "--title", "Background Check"],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "qualification_title": "Background Check"
    }


def test_cli_qualifications_update_merges_data(api, cli_env):
    route = api.put("/qualifications/11").respond(json={"data": QUALIFICATION_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "qualifications",
            "update",
            "11",
            "--data",
            '{"qualification_status":"inactive"}',
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "qualification_status": "inactive"
    }


def test_cli_qualifications_delete_declined_makes_no_request(api, cli_env):
    result = runner.invoke(app, ["qualifications", "delete", "11"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls


def test_cli_qualifications_delete_confirmed(api, cli_env):
    route = api.delete("/qualifications/11").respond(status_code=204)
    result = runner.invoke(app, ["qualifications", "delete", "11"], input="y\n")
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_qualifications_users(api, cli_env):
    api.get("/qualifications/11/users").respond(json={"data": [QUALIFICATION_USER_ROW]})
    result = runner.invoke(app, ["qualifications", "users", "11"])
    assert result.exit_code == 0, result.output
    assert "Mary" in result.output


def test_cli_qualifications_help_lists_every_command():
    out = runner.invoke(app, ["qualifications", "--help"]).output
    for command in ("list", "get", "create", "update", "delete", "users"):
        assert command in out


# --------------------------------------------------------------------------
# CLI -- benchmarks
# --------------------------------------------------------------------------


def test_cli_benchmarks_list_json(api, cli_env):
    api.get("/benchmarks").respond(json={"data": [BENCHMARK_ROW]})
    result = runner.invoke(app, ["--json", "benchmarks", "list"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["benchmark_title"] == "10 Hours"


def test_cli_benchmarks_get(api, cli_env):
    api.get("/benchmarks/5").respond(json={"data": BENCHMARK_ROW})
    result = runner.invoke(app, ["benchmarks", "get", "5"])
    assert result.exit_code == 0, result.output
    assert "10 Hours" in result.output


def test_cli_benchmarks_create_confirmed(api, cli_env):
    route = api.post("/benchmarks").respond(json={"data": BENCHMARK_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "benchmarks",
            "create",
            "--title",
            "10 Hours",
            "--hours",
            "10",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "benchmark_title": "10 Hours",
        "benchmark_hours": "10",
    }


def test_cli_benchmarks_update_merges_data(api, cli_env):
    route = api.put("/benchmarks/5").respond(json={"data": BENCHMARK_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "benchmarks",
            "update",
            "5",
            "--data",
            '{"benchmark_status":"inactive"}',
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "benchmark_status": "inactive"
    }


def test_cli_benchmarks_delete_declined_makes_no_request(api, cli_env):
    result = runner.invoke(app, ["benchmarks", "delete", "5"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls


def test_cli_benchmarks_delete_confirmed(api, cli_env):
    route = api.delete("/benchmarks/5").respond(status_code=204)
    result = runner.invoke(app, ["benchmarks", "delete", "5"], input="y\n")
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_benchmarks_users(api, cli_env):
    user_row = {"id": "4", "user_fname": "Mary", "user_email": "mary@example.com"}
    api.get("/benchmarks/5/users").respond(json={"data": [user_row]})
    result = runner.invoke(app, ["benchmarks", "users", "5"])
    assert result.exit_code == 0, result.output
    assert "Mary" in result.output


def test_cli_benchmarks_help_lists_every_command():
    out = runner.invoke(app, ["benchmarks", "--help"]).output
    for command in ("list", "get", "create", "update", "delete", "users"):
        assert command in out


# --------------------------------------------------------------------------
# CLI -- clusters
# --------------------------------------------------------------------------


def test_cli_clusters_list_json(api, cli_env):
    api.get("/clusters").respond(json={"data": [CLUSTER_ROW]})
    result = runner.invoke(app, ["--json", "clusters", "list"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["name"] == "Downtown"


def test_cli_clusters_create_declined_makes_no_request(api, cli_env):
    result = runner.invoke(
        app, ["clusters", "create", "--name", "Downtown"], input="n\n"
    )
    assert result.exit_code != 0
    assert not api.calls


def test_cli_clusters_create_confirmed(api, cli_env):
    route = api.post("/clusters").respond(json={"data": CLUSTER_ROW})
    result = runner.invoke(app, ["--yes", "clusters", "create", "--name", "Downtown"])
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {"name": "Downtown"}


def test_cli_clusters_delete_confirmed(api, cli_env):
    route = api.delete("/clusters/2").respond(status_code=204)
    result = runner.invoke(app, ["clusters", "delete", "2"], input="y\n")
    assert result.exit_code == 0, result.output
    assert route.called


def test_cli_clusters_help_lists_every_command():
    out = runner.invoke(app, ["clusters", "--help"]).output
    for command in ("list", "create", "delete"):
        assert command in out
    assert "update" not in out


# --------------------------------------------------------------------------
# CLI -- lookups: causes, interests, impacts, registration-questions
# --------------------------------------------------------------------------


def test_cli_causes_list_json(api, cli_env):
    api.get("/causes").respond(json={"data": [CAUSE_ROW]})
    result = runner.invoke(app, ["--json", "causes", "list"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["name"] == "Environment"


def test_cli_interests_list_json(api, cli_env):
    api.get("/interests").respond(json={"data": [INTEREST_ROW]})
    result = runner.invoke(app, ["--json", "interests", "list"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["name"] == "Tutoring"


def test_cli_impacts_list_json(api, cli_env):
    api.get("/impacts").respond(json={"data": [IMPACT_ROW]})
    result = runner.invoke(app, ["--json", "impacts", "list"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["impact_name"] == "Education"


def test_cli_registration_questions_list_json(api, cli_env):
    api.get("/questions/registration").respond(json={"data": [QUESTION_ROW]})
    result = runner.invoke(app, ["--json", "registration-questions", "list"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["q_label"] == "Why volunteer?"


# --------------------------------------------------------------------------
# CLI -- auth
# --------------------------------------------------------------------------


def test_cli_auth_login_hidden_prompt(api, cli_env):
    route = api.post("/users/login").respond(json={"data": LOGIN_ROW})
    result = runner.invoke(
        app,
        ["auth", "login", "--email", "mary@example.com"],
        input="hunter2\n",
    )
    assert result.exit_code == 0, result.output
    assert "hunter2" not in result.output
    assert "abc123" in result.output
    assert json.loads(route.calls.last.request.content) == {
        "user_email": "mary@example.com",
        "user_password": "hunter2",
        "key": "test-key",
    }


def test_cli_auth_login_prompt_is_not_on_stdout(api, cli_env):
    """The password prompt is stderr's business: stdout is for the payload."""
    api.post("/users/login").respond(json={"data": LOGIN_ROW})
    result = runner.invoke(
        app,
        ["auth", "login", "--email", "mary@example.com"],
        input="hunter2\n",
    )
    assert result.exit_code == 0, result.output
    assert "Password" not in result.stdout
    assert "Password" in result.stderr


def test_cli_auth_login_export_emits_only_the_export_line(api, cli_env):
    """``eval "$(galaxy auth login ... --export)"`` must see one line and
    nothing else on stdout -- the hint and any status text go to stderr.

    ``--password`` is passed rather than prompted because click's CliRunner
    fakes hidden input by writing a newline to *stdout*, which would be an
    artifact of the test harness, not of the command (real ``getpass``
    writes to the tty/stderr).
    """
    api.post("/users/login").respond(
        json={"data": {**LOGIN_ROW, "token": "tok123"}},
    )
    result = runner.invoke(
        app,
        [
            "auth",
            "login",
            "--email",
            "mary@example.com",
            "--password",
            "hunter2",
            "--export",
        ],
    )
    assert result.exit_code == 0, result.output
    # shlex.quote leaves an ordinary token like a JWT unquoted -- it is
    # base64url + dots, none of which are shell metacharacters.
    assert result.stdout == "export GALAXY_API_TOKEN=tok123\n"


def test_cli_auth_login_export_quotes_a_hostile_token(api, cli_env):
    """A token containing a shell metacharacter (here, a single quote) must
    come out safely quoted, so ``eval "$(galaxy auth login ... --export)"``
    can never be tricked into running anything beyond the assignment
    itself. A real JWT (base64url + dots) would never need this, but a
    hostile or unexpected token must not be able to break out of the eval.
    """
    hostile = "tok'; rm -rf /;'123"
    api.post("/users/login").respond(json={"data": {**LOGIN_ROW, "token": hostile}})
    result = runner.invoke(
        app,
        [
            "auth",
            "login",
            "--email",
            "mary@example.com",
            "--password",
            "hunter2",
            "--export",
        ],
    )
    assert result.exit_code == 0, result.output
    assert result.stdout == f"export GALAXY_API_TOKEN={shlex.quote(hostile)}\n"
    # sanity: the naive `'{token}'` form this replaces would have let the
    # embedded quote close the string early -- confirm we did not do that.
    assert result.stdout != f"export GALAXY_API_TOKEN='{hostile}'\n"


def test_cli_auth_login_export_without_token_fails(api, cli_env):
    api.post("/users/login").respond(json={"message": "ok"})
    result = runner.invoke(
        app,
        ["auth", "login", "--email", "m@e.com", "--password", "p", "--export"],
    )
    assert result.exit_code == 1
    assert result.stdout == ""


def test_cli_auth_login_table_shows_the_whole_token(api, cli_env):
    """Long tokens must wrap, never be truncated to an ellipsis: the value
    on screen is the value the operator copies."""
    long_token = "eyJ" + "x" * 300
    api.post("/users/login").respond(
        json={"data": {**LOGIN_ROW, "token": long_token}},
    )
    result = runner.invoke(
        app,
        ["auth", "login", "--email", "mary@example.com", "--password", "hunter2"],
    )
    assert result.exit_code == 0, result.output
    # the table wraps, so join the rendered lines back up before looking
    assert long_token in "".join(
        part.strip() for part in result.stdout.replace("│", "").splitlines()
    )
    assert "eval" in result.stderr


def test_cli_auth_login_key_flag_overrides_settings(api, cli_env):
    route = api.post("/users/login").respond(json={"data": LOGIN_ROW})
    result = runner.invoke(
        app,
        [
            "auth",
            "login",
            "--email",
            "mary@example.com",
            "--password",
            "hunter2",
            "--key",
            "other-site",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content)["key"] == "other-site"


def test_cli_auth_login_key_alone_works_standalone(monkeypatch, api, cli_env):
    """``--key`` alone must be enough to log in, with no GALAXY_API_KEY or
    GALAXY_API_TOKEN in the environment at all.

    ``State.client`` used to be built from ``settings.api_key`` before
    ``--key`` was ever folded in, so a clean-env, ``--key``-only login
    raised ``MissingAPIKeyError`` before the key was ever used.
    """
    # The autouse _isolate_env fixture sets GALAXY_API_KEY=test-key; undo
    # that here so --key is truly the only credential in play.
    monkeypatch.delenv("GALAXY_API_KEY", raising=False)
    monkeypatch.delenv("GALAXY_API_TOKEN", raising=False)
    route = api.post("/users/login").respond(
        json={"data": {**LOGIN_ROW, "token": "tok123"}}
    )
    result = runner.invoke(
        app,
        [
            "auth",
            "login",
            "--email",
            "mary@example.com",
            "--password",
            "hunter2",
            "--key",
            "sitekey",
            "--export",
        ],
    )
    assert result.exit_code == 0, result.output
    assert result.stdout == "export GALAXY_API_TOKEN=tok123\n"
    assert json.loads(route.calls.last.request.content)["key"] == "sitekey"


def test_cli_auth_login_json_carries_the_full_token(api, cli_env):
    api.post("/users/login").respond(json={"data": {**LOGIN_ROW, "token": "tok123"}})
    result = runner.invoke(
        app,
        [
            "--json",
            "auth",
            "login",
            "--email",
            "mary@example.com",
            "--password",
            "hunter2",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["token"] == "tok123"


def test_cli_auth_login_blocked_read_only(api, cli_env, monkeypatch):
    monkeypatch.setenv("GALAXY_READ_ONLY", "1")
    result = runner.invoke(
        app,
        ["auth", "login", "--email", "mary@example.com"],
        input="hunter2\n",
    )
    assert result.exit_code == 1
    assert not api.calls


def test_cli_auth_authenticate(api, cli_env):
    route = api.post("/users/authenticate").respond(json={"data": [ONECLICK_ROW]})
    result = runner.invoke(
        app,
        ["auth", "authenticate", "--email", "mary@example.com"],
        input="hunter2\n",
    )
    assert result.exit_code == 0, result.output
    assert "hunter2" not in result.output
    assert route.called


def test_cli_auth_help_lists_every_command():
    out = runner.invoke(app, ["auth", "--help"]).output
    for command in ("login", "authenticate"):
        assert command in out


# --------------------------------------------------------------------------
# namespaces
# --------------------------------------------------------------------------


def test_namespaces_attached(client):
    assert isinstance(client.qualifications, Qualifications)
    assert isinstance(client.benchmarks, Benchmarks)
    assert isinstance(client.clusters, Clusters)
    assert isinstance(client.lookups, Lookups)
    assert isinstance(client.auth, Auth)
