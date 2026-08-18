"""Tests for settings resolution and config file helpers."""

import os
import stat

import pytest

from galaxy_digital_cli import config

# POSIX permission bits are not meaningful on Windows: chmod(0o600) leaves the
# file world-readable per NTFS semantics, so the 0o600 assertions only run on
# POSIX platforms.
requires_posix_perms = pytest.mark.skipif(
    os.name == "nt", reason="POSIX permission bits are not enforced on Windows"
)


def test_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(tmp_path / "none.toml"))
    for var in ("GALAXY_API_KEY", "GALAXY_API_URL", "GALAXY_READ_ONLY"):
        monkeypatch.delenv(var, raising=False)
    s = config.load_settings()
    assert s.api_key is None
    assert s.url == config.SERVERS["us1"]
    assert s.read_only is False


def test_file_then_env_then_kwargs(monkeypatch, tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text('api_key = "from-file"\nurl = "ca"\nread_only = true\n')
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(cfg))
    monkeypatch.delenv("GALAXY_API_KEY", raising=False)
    monkeypatch.delenv("GALAXY_API_URL", raising=False)
    monkeypatch.delenv("GALAXY_READ_ONLY", raising=False)
    s = config.load_settings()
    assert s.api_key == "from-file"
    assert s.url == config.SERVERS["ca"]
    assert s.read_only is True

    monkeypatch.setenv("GALAXY_API_KEY", "from-env")
    assert config.load_settings().api_key == "from-env"
    assert config.load_settings(api_key="from-kwarg").api_key == "from-kwarg"


def test_read_only_env_values(monkeypatch, tmp_path):
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(tmp_path / "none.toml"))
    monkeypatch.setenv("GALAXY_READ_ONLY", "yes")
    assert config.load_settings().read_only is True
    monkeypatch.setenv("GALAXY_READ_ONLY", "0")
    assert config.load_settings().read_only is False


def test_save_config_roundtrip(monkeypatch, tmp_path):
    cfg = tmp_path / "sub" / "config.toml"
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(cfg))
    config.save_config({"api_key": "k"})
    assert cfg.exists()
    assert config.read_config()["api_key"] == "k"


@requires_posix_perms
def test_save_config_permissions(monkeypatch, tmp_path):
    cfg = tmp_path / "sub" / "config.toml"
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(cfg))
    config.save_config({"api_key": "k"})
    assert stat.S_IMODE(os.stat(cfg).st_mode) == 0o600


def test_read_only_kwarg_overrides_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(tmp_path / "none.toml"))
    monkeypatch.setenv("GALAXY_READ_ONLY", "yes")
    assert config.load_settings(read_only=False).read_only is False


def test_save_config_replaces_contents(monkeypatch, tmp_path):
    cfg = tmp_path / "config.toml"
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(cfg))
    config.save_config({"api_key": "k", "url": "ca"})
    config.save_config({"api_key": "k2"})
    assert config.read_config() == {"api_key": "k2"}


@requires_posix_perms
def test_save_config_tightens_existing_perms(monkeypatch, tmp_path):
    cfg = tmp_path / "config.toml"
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(cfg))
    cfg.write_text("")
    cfg.chmod(0o644)
    config.save_config({"api_key": "k"})
    assert stat.S_IMODE(os.stat(cfg).st_mode) == 0o600


def test_parse_bool():
    assert config.parse_bool("Yes") is True
    assert config.parse_bool("off") is False
