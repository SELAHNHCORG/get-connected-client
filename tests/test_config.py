"""Tests for settings resolution: explicit args > env vars > defaults."""

import pytest

from galaxy_digital_cli import config


@pytest.fixture
def no_env(monkeypatch):
    """Start from a clean slate: none of the GALAXY_* vars set."""
    for var in ("GALAXY_API_KEY", "GALAXY_API_URL", "GALAXY_READ_ONLY"):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


def test_defaults(no_env):
    s = config.load_settings()
    assert s.api_key is None
    assert s.url == config.SERVERS["us1"]
    assert s.read_only is False


def test_env_beats_defaults(no_env):
    no_env.setenv("GALAXY_API_KEY", "from-env")
    no_env.setenv("GALAXY_API_URL", "us2")
    no_env.setenv("GALAXY_READ_ONLY", "1")
    s = config.load_settings()
    assert s.api_key == "from-env"
    assert s.url == config.SERVERS["us2"]
    assert s.read_only is True


def test_kwargs_beat_env(no_env):
    no_env.setenv("GALAXY_API_KEY", "from-env")
    no_env.setenv("GALAXY_API_URL", "us2")
    no_env.setenv("GALAXY_READ_ONLY", "1")
    s = config.load_settings(api_key="from-kwarg", url="ca", read_only=False)
    assert s.api_key == "from-kwarg"
    assert s.url == config.SERVERS["ca"]
    assert s.read_only is False


def test_env_url_alias_resolves(no_env):
    """An alias in GALAXY_API_URL goes through resolve_url like a flag does."""
    no_env.setenv("GALAXY_API_URL", "CA")
    assert config.load_settings().url == config.SERVERS["ca"]
    no_env.setenv("GALAXY_API_URL", "https://example.test/api/")
    assert config.load_settings().url == "https://example.test/api"


def test_read_only_env_values(no_env):
    no_env.setenv("GALAXY_READ_ONLY", "yes")
    assert config.load_settings().read_only is True
    no_env.setenv("GALAXY_READ_ONLY", "0")
    assert config.load_settings().read_only is False
    # empty means "no opinion", not false-from-env
    no_env.setenv("GALAXY_READ_ONLY", "  ")
    assert config.env_read_only() is None
    assert config.load_settings().read_only is False


def test_read_only_kwarg_overrides_env(no_env):
    no_env.setenv("GALAXY_READ_ONLY", "yes")
    assert config.load_settings(read_only=False).read_only is False


def test_empty_env_api_key_is_none(no_env):
    no_env.setenv("GALAXY_API_KEY", "")
    assert config.load_settings().api_key is None


def test_parse_bool():
    assert config.parse_bool("Yes") is True
    assert config.parse_bool("off") is False
