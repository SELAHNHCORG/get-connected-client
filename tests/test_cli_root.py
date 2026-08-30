import json

import pytest
import typer
from pydantic import BaseModel, ValidationError
from typer.testing import CliRunner

import galaxy_digital_cli
from galaxy_digital_cli.cli import app
from galaxy_digital_cli.cli import main as root_callback
from galaxy_digital_cli.cli._confirm import confirm_write
from galaxy_digital_cli.cli._output import console
from galaxy_digital_cli.cli._state import _merge_fields, handle_errors
from galaxy_digital_cli.exceptions import GalaxyError, NotFoundError

runner = CliRunner()


# A throwaway app that reuses the real root callback, so ctx.obj is a real
# State built from the real global options. Resource commands do not exist
# yet (Task 13), so this stands in for them.
demo_app = typer.Typer()
demo_app.callback()(root_callback)


@demo_app.command("boom")
@handle_errors
def demo_boom() -> None:
    """Always fails with a GalaxyError."""
    raise NotFoundError(404, "no such thing")


@demo_app.command("write")
@handle_errors
def demo_write(ctx: typer.Context) -> None:
    """Confirms, then pretends to write."""
    confirm_write(ctx.obj, "delete the thing", {"id": 1})
    console.print("WROTE")


class _StrictRow(BaseModel):
    id: int


@demo_app.command("bad-payload")
@handle_errors
def demo_bad_payload() -> None:
    """Always fails the way a malformed API payload would."""
    _StrictRow.model_validate({"id": "not-a-number"})


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert galaxy_digital_cli.__version__ in result.output


def test_help_lists_global_options_and_config():
    out = runner.invoke(app, ["--help"]).output
    for flag in (
        "--api-key",
        "--token",
        "--url",
        "--read-only",
        "--json",
        "--yes",
        "--debug",
    ):
        assert flag in out
    assert "config" in out


def test_config_show_redacts_api_key():
    """The autouse _isolate_env fixture exports GALAXY_API_KEY=test-key."""
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "test-key" not in result.output
    assert "…-key" in result.output


def test_config_show_reports_sources():
    """api_key comes from the env (fixture); url falls through to the default."""
    lines = runner.invoke(app, ["config", "show"]).output.splitlines()
    api_key_row = next(line for line in lines if "api_key" in line)
    url_row = next(line for line in lines if "url" in line)
    assert "env" in api_key_row
    assert "default" in url_row


def test_config_show_json():
    out = runner.invoke(app, ["--json", "config", "show"]).output
    rows = {row["setting"]: row for row in json.loads(out)}
    assert rows["api_key"]["value"] == "…-key"
    assert rows["api_key"]["source"] == "env"
    # no session token in the mocked environment
    assert rows["token"]["value"] == "(not set)"
    assert rows["token"]["source"] == "default"
    assert rows["url"]["value"] == "https://api.galaxydigital.com/api"
    assert rows["url"]["source"] == "default"
    assert rows["read_only"]["value"] is False
    assert rows["read_only"]["source"] == "default"


def test_config_show_short_api_key_fully_redacted(monkeypatch):
    monkeypatch.setenv("GALAXY_API_KEY", "abc")
    out = runner.invoke(app, ["config", "show"]).output
    assert "abc" not in out
    assert "…redacted" in out


def test_config_show_without_api_key(monkeypatch):
    monkeypatch.delenv("GALAXY_API_KEY", raising=False)
    out = runner.invoke(app, ["--json", "config", "show"]).output
    rows = {row["setting"]: row for row in json.loads(out)}
    assert rows["api_key"]["value"] == "(not set)"
    assert rows["api_key"]["source"] == "default"


def test_config_show_reflects_env_overrides(monkeypatch):
    monkeypatch.setenv("GALAXY_API_URL", "ca")
    monkeypatch.setenv("GALAXY_READ_ONLY", "1")
    out = runner.invoke(app, ["--json", "config", "show"]).output
    rows = {row["setting"]: row for row in json.loads(out)}
    assert rows["url"]["value"] == "https://ca.volunteerapi.com/api"
    assert rows["url"]["source"] == "env"
    assert rows["read_only"]["value"] is True
    assert rows["read_only"]["source"] == "env"


def test_config_show_reports_flag_source_for_api_key():
    result = runner.invoke(app, ["--api-key", "flagkey9876", "config", "show"])
    assert result.exit_code == 0
    assert "flagkey9876" not in result.output
    assert "…9876" in result.output
    lines = result.output.splitlines()
    api_key_row = next(line for line in lines if "api_key" in line)
    assert "flag" in api_key_row


def test_config_show_token_from_env_is_redacted(monkeypatch):
    monkeypatch.setenv("GALAXY_API_TOKEN", "eyJhbGciOiJIUzI1NiJ9-secret-9876")
    out = runner.invoke(app, ["--json", "config", "show"]).output
    rows = {row["setting"]: row for row in json.loads(out)}
    assert rows["token"]["value"] == "…9876"
    assert rows["token"]["source"] == "env"
    assert "secret" not in out


def test_config_show_short_token_fully_redacted(monkeypatch):
    monkeypatch.setenv("GALAXY_API_TOKEN", "abc")
    out = runner.invoke(app, ["config", "show"]).output
    assert "abc" not in out
    assert "…redacted" in out


def test_config_show_reports_flag_source_for_token():
    result = runner.invoke(app, ["--token", "flagtoken4321", "config", "show"])
    assert result.exit_code == 0
    assert "flagtoken4321" not in result.output
    assert "…4321" in result.output
    token_row = next(line for line in result.output.splitlines() if "token" in line)
    assert "flag" in token_row


def test_token_flag_reaches_the_client():
    """The global --token is what the lazily-built client authenticates with."""
    from galaxy_digital_cli.cli._state import State
    from galaxy_digital_cli.config import load_settings

    state = State(settings=load_settings(api_key="k", token="tok"))
    with state.client as client:
        assert client.token == "tok"
        assert client.http.headers["Authorization"] == "Bearer tok"


def test_config_show_reports_flag_source_for_url():
    out = runner.invoke(app, ["--url", "us2", "config", "show"]).output
    lines = out.splitlines()
    url_row = next(line for line in lines if "url" in line)
    assert "volunteerapi.com" in url_row
    assert "flag" in url_row


def test_config_show_flag_url_beats_env(monkeypatch):
    monkeypatch.setenv("GALAXY_API_URL", "ca")
    out = runner.invoke(app, ["--url", "us2", "--json", "config", "show"]).output
    rows = {row["setting"]: row for row in json.loads(out)}
    assert rows["url"]["value"] == "https://www.volunteerapi.com/api"
    assert rows["url"]["source"] == "flag"


def test_config_show_reports_flag_source_for_read_only():
    out = runner.invoke(app, ["--read-only", "--json", "config", "show"]).output
    rows = {row["setting"]: row for row in json.loads(out)}
    assert rows["read_only"]["value"] is True
    assert rows["read_only"]["source"] == "flag"


def test_galaxy_error_is_clean():
    result = runner.invoke(demo_app, ["boom"])
    assert result.exit_code == 1
    assert "error:" in result.stderr
    assert "no such thing" in result.stderr
    assert "Traceback" not in result.output
    assert "Traceback" not in result.stderr


def test_galaxy_error_with_debug_reraises():
    result = runner.invoke(demo_app, ["--debug", "boom"])
    assert result.exit_code != 0
    assert isinstance(result.exception, GalaxyError)


def test_validation_error_is_clean():
    """A payload our models reject is the server's problem, not a traceback."""
    result = runner.invoke(demo_app, ["bad-payload"])
    assert result.exit_code == 1
    assert "error:" in result.stderr
    assert "Traceback" not in result.output
    assert "Traceback" not in result.stderr


def test_validation_error_with_debug_reraises():
    result = runner.invoke(demo_app, ["--debug", "bad-payload"])
    assert result.exit_code != 0
    assert isinstance(result.exception, ValidationError)


def test_output_result_reports_empty_writes(capsys):
    """A write that returns nothing still emits parseable JSON under --json."""
    from galaxy_digital_cli.cli._output import output_result
    from galaxy_digital_cli.cli._state import State
    from galaxy_digital_cli.config import Settings

    state = State(settings=Settings(api_key=None, url="x", read_only=False))
    output_result(state, None)
    assert "done" in capsys.readouterr().out

    state.json_output = True
    output_result(state, None)
    assert json.loads(capsys.readouterr().out) == {"ok": True}

    # a real payload still renders as a record
    output_result(state, {"id": 1})
    assert json.loads(capsys.readouterr().out) == {"id": 1}


def test_confirm_declined_aborts():
    result = runner.invoke(demo_app, ["write"], input="n\n")
    assert result.exit_code != 0
    assert "WROTE" not in result.output


def test_confirm_accepted_runs():
    result = runner.invoke(demo_app, ["write"], input="y\n")
    assert result.exit_code == 0
    assert "WROTE" in result.output


def test_yes_skips_confirmation():
    result = runner.invoke(demo_app, ["--yes", "write"])
    assert result.exit_code == 0
    assert "WROTE" in result.output
    assert "Proceed?" not in result.output


def test_confirm_write_without_payload(monkeypatch, capsys):
    from galaxy_digital_cli.cli._state import State
    from galaxy_digital_cli.config import Settings

    state = State(settings=Settings(api_key=None, url="x", read_only=False))
    monkeypatch.setattr(typer, "confirm", lambda *args, **kwargs: True)
    confirm_write(state, "no payload here")
    assert "no payload here" in capsys.readouterr().out


def test_json_output_flag(monkeypatch):
    monkeypatch.setenv("GALAXY_API_URL", "us2")
    out = runner.invoke(app, ["--json", "config", "show"]).output
    assert '"url"' in out and "volunteerapi.com" in out


def test_state_client_is_lazy_and_configured():
    from galaxy_digital_cli.cli._state import State
    from galaxy_digital_cli.config import load_settings

    state = State(settings=load_settings(api_key="k", url="ca", read_only=True))
    assert state._client is None
    client = state.client
    assert client is state.client
    assert client.read_only is True
    assert client.base_url == "https://ca.volunteerapi.com/api"


def test_merge_fields():
    assert _merge_fields(None, a=1, b=None) == {"a": 1}
    assert _merge_fields('{"b": 2}', a=1) == {"a": 1, "b": 2}
    assert _merge_fields('{"a": 9}', a=1) == {"a": 9}
    with pytest.raises(typer.BadParameter):
        _merge_fields("{not json}")
    with pytest.raises(typer.BadParameter):
        _merge_fields("[1, 2]")


def test_output_helpers(capsys):
    from galaxy_digital_cli.cli._output import output, output_one
    from galaxy_digital_cli.cli._state import State
    from galaxy_digital_cli.config import Settings

    state = State(settings=Settings(api_key=None, url="x", read_only=False))
    output(state, [{"id": 1, "name": "a"}], ["id", "name"], title="Rows")
    captured = capsys.readouterr().out
    assert "Rows" in captured and "name" in captured

    output_one(state, {"id": 1, "name": "a"})
    assert "name" in capsys.readouterr().out

    state.json_output = True
    output(state, [{"id": 1}], ["id"])
    assert '"id"' in capsys.readouterr().out
    output_one(state, {"id": 1})
    assert '"id"' in capsys.readouterr().out


def test_missing_api_key_is_clean(monkeypatch):
    """No API key anywhere: MissingAPIKeyError should exit 1, no traceback.

    Deferred here from Task 7 because no resource command existed yet to
    exercise the lazily-built client -- ``galaxy causes list`` (Task 13) is
    the first read that actually needs one.
    """
    monkeypatch.delenv("GALAXY_API_KEY", raising=False)
    result = runner.invoke(app, ["causes", "list"])
    assert result.exit_code == 1
    assert "Traceback" not in result.output


def test_cli_reference_docs_render_from_the_live_app():
    """``doc/source/cli.rst`` renders its command reference from the live app.

    Used to be a drift-guard that asserted every registered command name
    was mentioned somewhere in the hand-maintained ``cli.rst`` tables (see
    git history for the old per-command membership check). Now that the
    reference is generated at doc-build time by
    ``sphinxcontrib-typer`` ``.. typer::`` directives, it cannot drift from
    the app -- there is nothing to enumerate and compare. What remains
    worth guarding is that the directives still point at the real app
    import path, so a rename of ``galaxy_digital_cli.cli.app`` breaks this
    test loudly instead of silently producing an empty/broken doc build.
    """
    import importlib
    import pathlib

    from typer.main import get_command

    cli_rst = (
        pathlib.Path(__file__).resolve().parent.parent / "doc" / "source" / "cli.rst"
    ).read_text()
    # the exact import path every `.. typer::` directive below resolves
    # against; if `app` is ever renamed or moved this fails before a doc
    # build would silently render nothing (or fail on its own, less clearly).
    assert getattr(importlib.import_module("galaxy_digital_cli.cli"), "app") is app
    assert ".. typer:: galaxy_digital_cli.cli:app" in cli_rst
    directive_count = cli_rst.count(".. typer:: galaxy_digital_cli.cli:app")
    # one directive per registered sub-app
    root = get_command(app)
    sub_apps = [
        name for name, group in root.commands.items() if hasattr(group, "commands")
    ]
    assert directive_count == len(sub_apps)


def test_output_accepts_models_and_scalars(capsys):
    from galaxy_digital_cli.cli._output import output
    from galaxy_digital_cli.cli._state import State
    from galaxy_digital_cli.config import Settings

    class Row(BaseModel):
        id: int
        name: str

    state = State(settings=Settings(api_key=None, url="x", read_only=False))
    output(state, [Row(id=7, name="seven")], ["id", "name"])
    assert "seven" in capsys.readouterr().out

    output(state, ["scalar"], ["value"])
    assert "scalar" in capsys.readouterr().out
