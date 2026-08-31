"""Tests for the build-time version source in ``_version.py``."""

import re
from datetime import datetime

from get_connected_client._version import get_version


def _expected_dev() -> str:
    now = datetime.now().astimezone()
    return f"{now.year}.{now.month}.{now.day}.dev0"


def test_package_version_env_wins(monkeypatch):
    monkeypatch.setenv("PACKAGE_VERSION", "2026.9.1")
    assert get_version() == "2026.9.1"


def test_dev_version_when_env_unset(monkeypatch):
    monkeypatch.delenv("PACKAGE_VERSION", raising=False)
    # computed before and after the call so a midnight rollover mid-test
    # cannot produce a flake
    before = _expected_dev()
    version = get_version()
    after = _expected_dev()
    assert version in {before, after}
    assert re.fullmatch(r"\d{4}\.\d{1,2}\.\d{1,2}\.dev0", version)


def test_empty_package_version_treated_as_unset(monkeypatch):
    monkeypatch.setenv("PACKAGE_VERSION", "")
    before = _expected_dev()
    version = get_version()
    after = _expected_dev()
    assert version in {before, after}
