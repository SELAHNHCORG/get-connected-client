"""Settings resolution: explicit args > env vars > config file > defaults."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from platformdirs import user_config_path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # pyright: ignore[reportMissingImports]

US1 = "https://api.galaxydigital.com/api"
SERVERS = {
    "us1": US1,
    "us2": "https://www.volunteerapi.com/api",
    "ca": "https://ca.volunteerapi.com/api",
}

_TRUTHY = {"1", "true", "yes", "on"}


def env_read_only() -> bool | None:
    """Read the GALAXY_READ_ONLY env var as a tri-state boolean."""
    raw = os.environ.get("GALAXY_READ_ONLY")
    if raw is None or raw.strip() == "":
        return None
    return raw.strip().lower() in _TRUTHY


def resolve_url(url: str) -> str:
    """Resolve a server alias (us1/us2/ca) to its full URL, or pass through."""
    return SERVERS.get(url.strip().lower(), url).rstrip("/")


def config_file() -> Path:
    """Return the path to the config file, honoring GALAXY_CONFIG_FILE."""
    override = os.environ.get("GALAXY_CONFIG_FILE")
    if override:
        return Path(override)
    return user_config_path("galaxy-digital") / "config.toml"


def read_config() -> dict[str, Any]:
    """Read the TOML config file, returning an empty dict if absent."""
    path = config_file()
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def save_config(values: dict[str, Any]) -> Path:
    """Write *exactly* ``values`` to the config file, replacing its contents.

    Callers that want to update a single key must merge first::

        cfg = read_config()
        cfg["api_key"] = "..."
        save_config(cfg)
    """
    import tomlkit

    path = config_file()
    doc = tomlkit.document()
    for key, value in values.items():
        doc[key] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)  # tighten even if the file pre-existed with looser perms
    path.write_text(tomlkit.dumps(doc))
    return path


@dataclass
class Settings:
    """Resolved settings for the Galaxy Digital API client."""

    api_key: str | None
    url: str
    read_only: bool


def load_settings(
    api_key: str | None = None,
    url: str | None = None,
    read_only: bool | None = None,
) -> Settings:
    """Resolve settings with precedence: kwargs > env vars > config file > defaults."""
    file_cfg = read_config()
    resolved_key = (
        api_key or os.environ.get("GALAXY_API_KEY") or file_cfg.get("api_key")
    )
    resolved_url = url or os.environ.get("GALAXY_API_URL") or file_cfg.get("url") or US1
    if read_only is None:
        read_only = env_read_only()
    if read_only is None:
        read_only = bool(file_cfg.get("read_only", False))
    return Settings(
        api_key=resolved_key or None,
        url=resolve_url(resolved_url),
        read_only=read_only,
    )
