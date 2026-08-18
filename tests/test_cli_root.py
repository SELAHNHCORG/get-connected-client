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
    for flag in ("--api-key", "--url", "--read-only", "--json", "--yes", "--debug"):
        assert flag in out
    assert "config" in out


def test_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(tmp_path / "c.toml"))
    assert runner.invoke(app, ["config", "set", "api_key", "secret1234"]).exit_code == 0
    shown = runner.invoke(app, ["config", "show"])
    assert "secret1234" not in shown.output
    assert "1234" in shown.output
    assert str(tmp_path / "c.toml") in runner.invoke(app, ["config", "path"]).output
    assert runner.invoke(app, ["config", "unset", "api_key"]).exit_code == 0
    assert "api_key" not in runner.invoke(app, ["config", "show"]).output


def test_config_set_rejects_unknown_key(tmp_path, monkeypatch):
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(tmp_path / "c.toml"))
    assert runner.invoke(app, ["config", "set", "bogus", "x"]).exit_code != 0


def test_config_set_short_api_key_fully_redacted(tmp_path, monkeypatch):
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(tmp_path / "c.toml"))
    assert runner.invoke(app, ["config", "set", "api_key", "abc"]).exit_code == 0
    out = runner.invoke(app, ["config", "show"]).output
    assert "abc" not in out
    assert "…abc" not in out
    assert "…redacted" in out


def test_config_set_preserves_other_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(tmp_path / "c.toml"))
    runner.invoke(app, ["config", "set", "url", "ca"])
    runner.invoke(app, ["config", "set", "api_key", "k123456"])
    out = runner.invoke(app, ["config", "show"]).output
    assert "url" in out and "3456" in out


def test_config_set_read_only_parses_bool(tmp_path, monkeypatch):
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(tmp_path / "c.toml"))
    assert runner.invoke(app, ["config", "set", "read_only", "yes"]).exit_code == 0
    from galaxy_digital_cli.config import read_config

    assert read_config()["read_only"] is True
    runner.invoke(app, ["config", "set", "read_only", "off"])
    assert read_config()["read_only"] is False


def test_config_unset_missing_key_is_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(tmp_path / "c.toml"))
    assert runner.invoke(app, ["config", "unset", "api_key"]).exit_code == 0


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


def test_json_output_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(tmp_path / "c.toml"))
    runner.invoke(app, ["config", "set", "url", "us2"])
    out = runner.invoke(app, ["--json", "config", "show"]).output
    assert '"url"' in out and "us2" in out


def test_state_client_is_lazy_and_configured(monkeypatch):
    monkeypatch.setenv("GALAXY_CONFIG_FILE", "/nonexistent/none.toml")
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


def test_missing_api_key_is_clean(monkeypatch, tmp_path):
    """No API key, no config: MissingAPIKeyError should exit 1, no traceback.

    Deferred here from Task 7 because no resource command existed yet to
    exercise the lazily-built client -- ``galaxy causes list`` (Task 13) is
    the first read that actually needs one.
    """
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(tmp_path / "config.toml"))
    monkeypatch.delenv("GALAXY_API_KEY", raising=False)
    result = runner.invoke(app, ["causes", "list"])
    assert result.exit_code == 1
    assert "Traceback" not in result.output


def test_cli_reference_docs_list_every_command():
    """Every registered CLI command must be mentioned in doc/source/cli.rst."""
    import pathlib

    from typer.main import get_command

    cli_rst = (
        pathlib.Path(__file__).resolve().parent.parent / "doc" / "source" / "cli.rst"
    ).read_text()
    root = get_command(app)
    missing = []
    for group_name, group in root.commands.items():
        if not hasattr(group, "commands"):
            continue
        for command_name in group.commands:
            if command_name not in cli_rst:
                missing.append(f"{group_name} {command_name}")
    assert not missing, f"commands absent from doc/source/cli.rst: {missing}"


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
