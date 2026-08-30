# Galaxy Digital API Client & CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A typed sync Python client (httpx + pydantic v2) and typer/rich CLI covering all 66 endpoints of the Galaxy Digital "Get Connected" API v1.9.2, with a single read-only choke point protecting the production instance.

**Architecture:** Hand-written client with per-resource namespaces (`client.users`, `client.needs`, …) built on shared CRUD mixins; all HTTP funnels through `GalaxyClient.request()` which enforces read-only mode before any write leaves the machine. The CLI is one typer sub-app per resource; unit tests mock HTTP with respx; live tests are opt-in markers.

**Tech Stack:** Python ≥3.10, httpx, pydantic v2, typer, rich, platformdirs, tomlkit (+tomli on 3.10), pytest + respx, uv/just/hatchling scaffold (already present).

**Spec:** `docs/superpowers/specs/2026-08-17-galaxy-digital-api-cli-design.md`. The OpenAPI spec is vendored at `doc/api.yml` (Task 1) — it is the authority for every path, query param, request body, and schema field. A digest of every endpoint appears in the resource tasks below.

**Conventions locked for all tasks:**

- Auth: raw API key sent as the `Authorization` header (the spec's apiKey scheme named `Authorization`). Live smoke test (Task 14) confirms; if the server wants a `Bearer ` prefix, fix in `GalaxyClient.http` only.
- Responses arrive as `{"data": ...}`; unwrap in `client._unwrap` only.
- List endpoints: `per_page` (max 150) + `since_id` auto-pagination; the API signals "no results" with **404**, which pagination treats as an empty page, and `_get_list` treats as `[]`.
- Models: pydantic v2, `extra="allow"`. Field typing rule: `id`, `domain_id`, `*_id` → `int | None`; booleans/ints where the spec says so; nested objects → their model; everything else `str | None`. Every field defaults to `None`. Field names copied verbatim from the schema in `doc/api.yml` (e.g. `user_fname`, not `first_name`).
- CLI: `galaxy <resource> <verb>`; write commands call `confirm_write()` (prompts with payload unless `--yes`); output via `output()` (rich table or `--json`).
- Commit after every task with a conventional message.

---

## File Structure

```
doc/api.yml                                  # vendored OpenAPI spec (Task 1)
src/get_connected_cli/
├── __init__.py            # existing banner + exports GalaxyClient, exceptions (Task 16)
├── exceptions.py          # Task 2
├── config.py              # Task 4
├── client.py              # Task 5
├── models/
│   ├── __init__.py        # re-exports all models
│   ├── base.py            # GalaxyModel (Task 3)
│   ├── common.py          # mini/lookup models shared across resources (Task 3)
│   ├── users.py agencies.py needs.py events.py hours.py responses.py
│   ├── teams.py groups.py qualifications.py benchmarks.py auth.py   # Tasks 8–13
├── resources/
│   ├── __init__.py
│   ├── base.py            # Resource + CRUD mixins (Task 6)
│   ├── users.py agencies.py needs.py events.py hours.py responses.py
│   ├── teams.py groups.py qualifications.py benchmarks.py misc.py auth.py  # Tasks 8–13
└── cli/
    ├── __init__.py        # typer app, global callback (Task 7)
    ├── _state.py _output.py _confirm.py      # Task 7
    ├── config_cmds.py     # galaxy config … (Task 7)
    ├── users.py agencies.py needs.py events.py hours.py responses.py
    ├── teams.py groups.py qualifications.py benchmarks.py misc.py auth.py  # Tasks 8–13
tests/
├── conftest.py            # existing + client/respx/runner fixtures (Task 5)
├── test_exceptions.py test_config.py test_client.py test_resources_base.py
├── test_cli_root.py test_users.py test_agencies.py test_needs.py
├── test_events_hours.py test_responses_teams_groups.py test_quals_benchmarks_misc.py
└── live/
    ├── __init__.py test_live_read.py test_live_write.py   # Task 14
doc/source/                # Sphinx (Task 15)
```

---

### Task 1: Project setup & dependencies

**Goal:** Runtime/test dependencies installed, spec vendored, markers registered, CLI entry point stubbed so `galaxy --help` runs.

**Files:**
- Modify: `pyproject.toml`
- Create: `doc/api.yml` (copy of https://api.galaxydigital.com/docs/api.yml?v=1.9.2)
- Create: `src/get_connected_cli/cli/__init__.py` (minimal stub, replaced in Task 7)
- Delete: `tests/test.py` (scaffold placeholder) → replaced by `tests/test_package.py`

**Acceptance Criteria:**
- [ ] `uv run galaxy --help` prints usage
- [ ] `just test` passes (placeholder package test)
- [ ] `doc/api.yml` committed, `grep "Get Connected" doc/api.yml` matches

**Steps:**

- [ ] **Step 1: pyproject changes.** In `[project]` set `dependencies`:

```toml
dependencies = [
    "httpx>=0.27",
    "pydantic>=2.7",
    "typer>=0.12",
    "rich>=13.0",
    "platformdirs>=4.0",
    "tomlkit>=0.13",
    "tomli>=2.0; python_version < '3.11'",
]
```

Add after `[project.urls]`:

```toml
[project.scripts]
galaxy = "get_connected_cli.cli:app"
```

Add `"respx>=0.21"` to the `test` dependency group. In `[tool.pytest.ini_options]` add:

```toml
markers = [
    "live: hits the real production API (read-only); requires GALAXY_API_KEY",
    "live_write: WRITES to the production API; requires GALAXY_LIVE_WRITE_ACK",
]
```

and append `'-m "not live and not live_write"'` to `addopts`.

- [ ] **Step 2: vendor the spec.**

```bash
curl -sL 'https://api.galaxydigital.com/docs/api.yml?v=1.9.2' -o doc/api.yml
```

- [ ] **Step 3: CLI stub.** `src/get_connected_cli/cli/__init__.py`:

```python
import typer

app = typer.Typer(help="CLI for the Galaxy Digital Get Connected API.")


@app.callback()
def main() -> None:
    """Galaxy Digital API command line interface."""
```

- [ ] **Step 4: replace placeholder test.** Delete `tests/test.py`; create `tests/test_package.py`:

```python
import get_connected_cli


def test_version():
    assert get_connected_cli.__title__ == "get-connected-cli"
```

- [ ] **Step 5: install & verify.** Run: `uv sync --all-groups && uv run galaxy --help && just test` → help text prints, tests pass.

- [ ] **Step 6: Commit.** `git add -A && git commit -m "feat: add runtime deps, CLI entry point, vendored API spec"`

---

### Task 2: Exceptions

**Goal:** Typed exception hierarchy the whole library raises.

**Files:**
- Create: `src/get_connected_cli/exceptions.py`
- Test: `tests/test_exceptions.py`

**Acceptance Criteria:**
- [ ] `GalaxyHTTPError` carries `status_code` and `detail`; subclass chosen by status
- [ ] `for_status()` maps 401/403→`AuthError`, 404→`NotFoundError`, 422→`ValidationFailedError`, 429→`RateLimitError`, else `GalaxyHTTPError`

**Verify:** `just test tests/test_exceptions.py` → PASS

**Steps:**

- [ ] **Step 1: failing tests** (`tests/test_exceptions.py`):

```python
import pytest
from get_connected_cli import exceptions as exc


@pytest.mark.parametrize(
    "status,klass",
    [
        (401, exc.AuthError),
        (403, exc.AuthError),
        (404, exc.NotFoundError),
        (422, exc.ValidationFailedError),
        (429, exc.RateLimitError),
        (500, exc.GalaxyHTTPError),
    ],
)
def test_for_status(status, klass):
    e = exc.GalaxyHTTPError.for_status(status, "boom")
    assert isinstance(e, klass)
    assert e.status_code == status
    assert "boom" in str(e)


def test_hierarchy():
    assert issubclass(exc.GalaxyHTTPError, exc.GalaxyError)
    assert issubclass(exc.ReadOnlyError, exc.GalaxyError)
    assert issubclass(exc.MissingAPIKeyError, exc.GalaxyError)
```

- [ ] **Step 2:** Run `just test tests/test_exceptions.py` → FAIL (module missing).

- [ ] **Step 3: implement** `src/get_connected_cli/exceptions.py`:

```python
"""Exception hierarchy for the Galaxy Digital API client."""

from __future__ import annotations


class GalaxyError(Exception):
    """Base for all errors raised by this library."""


class MissingAPIKeyError(GalaxyError):
    """No API key was provided or discoverable."""


class ReadOnlyError(GalaxyError):
    """A write was attempted while the client is in read-only mode."""


class GalaxyHTTPError(GalaxyError):
    """An HTTP-level error response from the API."""

    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}" if detail else f"HTTP {status_code}")

    @classmethod
    def for_status(cls, status_code: int, detail: str = "") -> "GalaxyHTTPError":
        klass = {
            401: AuthError,
            403: AuthError,
            404: NotFoundError,
            422: ValidationFailedError,
            429: RateLimitError,
        }.get(status_code, GalaxyHTTPError)
        return klass(status_code, detail)


class AuthError(GalaxyHTTPError):
    """401/403 — bad or missing credentials."""


class NotFoundError(GalaxyHTTPError):
    """404 — the API also uses this for empty list results."""


class ValidationFailedError(GalaxyHTTPError):
    """422 — the API rejected the payload."""


class RateLimitError(GalaxyHTTPError):
    """429 — too many requests."""
```

- [ ] **Step 4:** `just test tests/test_exceptions.py` → PASS.
- [ ] **Step 5: Commit.** `git commit -am "feat: exception hierarchy"`

---

### Task 3: Model base & common models

**Goal:** `GalaxyModel` base (extra-preserving) plus the small shared models used by many resources.

**Files:**
- Create: `src/get_connected_cli/models/__init__.py`, `models/base.py`, `models/common.py`
- Test: `tests/test_models_common.py`

**Acceptance Criteria:**
- [ ] Unknown fields survive `model_dump()` round-trip
- [ ] String ids coerce to int (`{"id": "5"}` → `id == 5`)
- [ ] All models importable from `get_connected_cli.models`

**Verify:** `just test tests/test_models_common.py` → PASS

**Steps:**

- [ ] **Step 1: failing tests** (`tests/test_models_common.py`):

```python
from get_connected_cli import models


def test_extra_fields_survive():
    tag = models.Tag.model_validate({"id": "7", "name": "vip", "brand_new_field": "x"})
    assert tag.id == 7
    assert tag.model_dump()["brand_new_field"] == "x"


def test_common_models_exist():
    for name in [
        "Tag", "Cause", "Cluster", "Interest", "Impact", "Category",
        "Extra", "Question", "Shift", "TrackMini", "UserMini", "AgencyMini",
        "NeedMini", "GroupMini", "InitiativeMini", "TeamMini",
    ]:
        assert hasattr(models, name)


def test_user_mini_fields():
    u = models.UserMini.model_validate(
        {"id": 1, "domain_id": 2, "user_fname": "A", "user_lname": "B",
         "user_email": "a@b.co"}
    )
    assert u.user_email == "a@b.co"
```

- [ ] **Step 2:** run → FAIL. **Step 3: implement.**

`models/base.py`:

```python
"""Base model preserving unknown fields (the API schema is loose)."""

from pydantic import BaseModel, ConfigDict


class GalaxyModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
```

`models/common.py` — one class per spec schema, fields verbatim from `doc/api.yml`:

```python
from __future__ import annotations

from .base import GalaxyModel


class Tag(GalaxyModel):          # tagObject
    id: int | None = None
    name: str | None = None


class Cause(GalaxyModel):        # causeObject
    id: int | None = None
    name: str | None = None


class Cluster(GalaxyModel):      # clusterObject
    id: int | None = None
    name: str | None = None


class Interest(GalaxyModel):     # interestObject
    id: int | None = None
    name: str | None = None


class Impact(GalaxyModel):       # impactObject
    id: int | None = None
    impact_name: str | None = None


class Category(GalaxyModel):     # categoryObject
    id: int | None = None
    name: str | None = None


class Extra(GalaxyModel):        # extraObject
    key: str | None = None
    value: str | None = None


class Question(GalaxyModel):     # questionObject
    id: int | None = None
    q_type: str | None = None
    q_label: str | None = None
    q_options: str | None = None
    q_area: str | None = None
    q_area_id: int | None = None
    q_status: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class Shift(GalaxyModel):        # shiftObject
    id: int | None = None
    start: str | None = None
    end: str | None = None
    duration: str | None = None
    slots: int | None = None


class TrackMini(GalaxyModel):    # trackMiniObject
    id: int | None = None
    name: str | None = None
    created_at: str | None = None


class UserMini(GalaxyModel):     # userMiniObject
    id: int | None = None
    domain_id: int | None = None
    user_fname: str | None = None
    user_lname: str | None = None
    user_email: str | None = None


class AgencyMini(GalaxyModel):   # agencyMiniObject
    id: int | None = None
    domain_id: int | None = None
    agency_name: str | None = None


class NeedMini(GalaxyModel):     # needMiniObject
    id: int | None = None
    domain_id: int | None = None
    need_title: str | None = None


class GroupMini(GalaxyModel):    # groupMiniObject
    id: int | None = None
    domain_id: int | None = None
    group_title: str | None = None


class InitiativeMini(GalaxyModel):  # initiativeMiniObject
    id: int | None = None
    domain_id: int | None = None
    init_title: str | None = None


class TeamMini(GalaxyModel):     # teamMiniObject
    id: int | None = None
    domain_id: int | None = None
    team_name: str | None = None
```

`models/__init__.py`:

```python
from .base import GalaxyModel
from .common import (
    AgencyMini, Category, Cause, Cluster, Extra, GroupMini, Impact,
    InitiativeMini, Interest, NeedMini, Question, Shift, Tag, TeamMini,
    TrackMini, UserMini,
)

__all__ = [
    "GalaxyModel", "AgencyMini", "Category", "Cause", "Cluster", "Extra",
    "GroupMini", "Impact", "InitiativeMini", "Interest", "NeedMini",
    "Question", "Shift", "Tag", "TeamMini", "TrackMini", "UserMini",
]
```

(Resource tasks 8–13 append their models to this `__init__`.)

- [ ] **Step 4:** `just test tests/test_models_common.py` → PASS.
- [ ] **Step 5: Commit.** `git commit -am "feat: pydantic model base and shared mini models"`

---

### Task 4: Configuration

**Goal:** Settings resolution: explicit args > env vars > config file > defaults; config file helpers used later by `galaxy config`.

**Files:**
- Create: `src/get_connected_cli/config.py`
- Test: `tests/test_config.py`

**Acceptance Criteria:**
- [ ] `load_settings()` precedence: kwargs > `GALAXY_API_KEY`/`GALAXY_API_URL`/`GALAXY_READ_ONLY` > TOML file > defaults (US1 url, read_only False)
- [ ] `GALAXY_CONFIG_FILE` env var overrides the platformdirs path (this is how tests isolate)
- [ ] `save_config()` writes TOML with 0600 permissions
- [ ] Server aliases `us1`/`us2`/`ca` resolve to full URLs

**Verify:** `just test tests/test_config.py` → PASS

**Steps:**

- [ ] **Step 1: failing tests** (`tests/test_config.py`):

```python
import os
import stat
from get_connected_cli import config


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


def test_save_config_permissions(monkeypatch, tmp_path):
    cfg = tmp_path / "sub" / "config.toml"
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(cfg))
    config.save_config({"api_key": "k"})
    assert cfg.exists()
    assert stat.S_IMODE(os.stat(cfg).st_mode) == 0o600
    assert config.read_config()["api_key"] == "k"
```

- [ ] **Step 2:** run → FAIL. **Step 3: implement** `src/get_connected_cli/config.py`:

```python
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
    import tomli as tomllib

US1 = "https://api.galaxydigital.com/api"
SERVERS = {
    "us1": US1,
    "us2": "https://www.volunteerapi.com/api",
    "ca": "https://ca.volunteerapi.com/api",
}

_TRUTHY = {"1", "true", "yes", "on"}


def env_read_only() -> bool | None:
    raw = os.environ.get("GALAXY_READ_ONLY")
    if raw is None or raw.strip() == "":
        return None
    return raw.strip().lower() in _TRUTHY


def resolve_url(url: str) -> str:
    return SERVERS.get(url.strip().lower(), url).rstrip("/")


def config_file() -> Path:
    override = os.environ.get("GALAXY_CONFIG_FILE")
    if override:
        return Path(override)
    return user_config_path("galaxy-digital") / "config.toml"


def read_config() -> dict[str, Any]:
    path = config_file()
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def save_config(values: dict[str, Any]) -> Path:
    import tomlkit

    path = config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = tomlkit.document()
    for key, value in values.items():
        doc[key] = value
    path.write_text(tomlkit.dumps(doc))
    path.chmod(0o600)
    return path


@dataclass
class Settings:
    api_key: str | None
    url: str
    read_only: bool


def load_settings(
    api_key: str | None = None,
    url: str | None = None,
    read_only: bool | None = None,
) -> Settings:
    file_cfg = read_config()
    resolved_key = api_key or os.environ.get("GALAXY_API_KEY") or file_cfg.get("api_key")
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
```

- [ ] **Step 4:** `just test tests/test_config.py` → PASS.
- [ ] **Step 5: Commit.** `git commit -am "feat: settings resolution and config file helpers"`

---

### Task 5: Client transport

**Goal:** `GalaxyClient` — auth header, read-only choke point, envelope unwrap, retries, pagination, error mapping. Plus shared test fixtures.

**Files:**
- Create: `src/get_connected_cli/client.py`
- Modify: `tests/conftest.py` (append fixtures)
- Test: `tests/test_client.py`

**Acceptance Criteria:**
- [ ] Requests carry `Authorization: <key>`; missing key raises `MissingAPIKeyError`
- [ ] POST/PUT/DELETE with `read_only=True` **or** `GALAXY_READ_ONLY=1` raise `ReadOnlyError` and no request is sent
- [ ] 401→`AuthError`, 404→`NotFoundError`, 422→`ValidationFailedError`; 429 and 5xx retried up to `retries` times with backoff then raise
- [ ] `paginate()` follows `since_id` until a short page; a 404 mid-stream ends iteration quietly
- [ ] Works as a context manager

**Verify:** `just test tests/test_client.py` → PASS

**Steps:**

- [ ] **Step 1: fixtures.** Append to `tests/conftest.py`:

```python
import pytest


BASE = "https://api.test/api"


@pytest.fixture
def client():
    from get_connected_cli.client import GalaxyClient

    with GalaxyClient(api_key="test-key", base_url=BASE) as c:
        yield c


@pytest.fixture
def api(client):
    import respx

    with respx.mock(base_url=BASE) as router:
        yield router


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(tmp_path / "config.toml"))
    monkeypatch.delenv("GALAXY_READ_ONLY", raising=False)
    monkeypatch.delenv("GALAXY_API_URL", raising=False)
    monkeypatch.setenv("GALAXY_API_KEY", "test-key")
```

- [ ] **Step 2: failing tests** (`tests/test_client.py`):

```python
import httpx
import pytest
import respx

from get_connected_cli import exceptions as exc
from get_connected_cli.client import GalaxyClient

from .conftest import BASE


def test_missing_key(monkeypatch):
    monkeypatch.delenv("GALAXY_API_KEY", raising=False)
    with pytest.raises(exc.MissingAPIKeyError):
        GalaxyClient(api_key=None, base_url=BASE)


def test_auth_header_and_unwrap(client, api):
    route = api.get("/causes").respond(json={"data": [{"id": 1, "name": "x"}]})
    assert client.get_data("/causes") == [{"id": 1, "name": "x"}]
    assert route.calls.last.request.headers["Authorization"] == "test-key"


def test_server_alias():
    c = GalaxyClient(api_key="k", base_url="ca")
    assert c.base_url == "https://ca.volunteerapi.com/api"


@pytest.mark.parametrize("status,klass", [(401, exc.AuthError), (404, exc.NotFoundError), (422, exc.ValidationFailedError)])
def test_error_mapping(client, api, status, klass):
    api.get("/users/9").respond(status_code=status, json={"error": "nope"})
    with pytest.raises(klass):
        client.get_data("/users/9")


def test_read_only_blocks_before_request(api):
    client = GalaxyClient(api_key="k", base_url=BASE, read_only=True)
    with pytest.raises(exc.ReadOnlyError):
        client.request("POST", "/users", json={"user_fname": "x"})
    assert not api.calls  # nothing hit the wire


def test_env_read_only_overrides(monkeypatch, client, api):
    monkeypatch.setenv("GALAXY_READ_ONLY", "1")
    with pytest.raises(exc.ReadOnlyError):
        client.request("DELETE", "/users/1")
    assert not api.calls


def test_retry_then_success(client, api, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    route = api.get("/causes")
    route.side_effect = [
        httpx.Response(500),
        httpx.Response(429),
        httpx.Response(200, json={"data": []}),
    ]
    assert client.get_data("/causes") == []
    assert route.call_count == 3


def test_retry_exhausted(api, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    client = GalaxyClient(api_key="k", base_url=BASE, retries=1)
    api.get("/causes").respond(status_code=500)
    with pytest.raises(exc.GalaxyHTTPError):
        client.get_data("/causes")


def test_paginate(client, api):
    page1 = {"data": [{"id": i} for i in range(1, 4)]}
    page2 = {"data": [{"id": 4}]}
    route = api.get("/hours")
    route.side_effect = [httpx.Response(200, json=page1), httpx.Response(200, json=page2)]
    rows = list(client.paginate("/hours", per_page=3))
    assert [r["id"] for r in rows] == [1, 2, 3, 4]
    assert route.calls[1].request.url.params["since_id"] == "3"


def test_paginate_404_is_empty(client, api):
    api.get("/hours").respond(status_code=404)
    assert list(client.paginate("/hours")) == []
```

- [ ] **Step 3:** run → FAIL. **Step 4: implement** `src/get_connected_cli/client.py`:

```python
"""Sync HTTP client for the Galaxy Digital Get Connected API."""

from __future__ import annotations

import os
import time
from typing import Any, Iterator

import httpx

from .config import US1, env_read_only, resolve_url
from .exceptions import (
    GalaxyHTTPError,
    MissingAPIKeyError,
    NotFoundError,
    ReadOnlyError,
)

_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
MAX_PER_PAGE = 150


def _unwrap(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


class GalaxyClient:
    """Entry point to the API. All requests funnel through :meth:`request`,
    which enforces read-only mode before anything reaches the network."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = US1,
        *,
        read_only: bool = False,
        timeout: float = 30.0,
        retries: int = 3,
    ):
        self.api_key = api_key or os.environ.get("GALAXY_API_KEY") or ""
        if not self.api_key:
            raise MissingAPIKeyError(
                "No API key: pass api_key= or set GALAXY_API_KEY"
            )
        self.base_url = resolve_url(base_url)
        self.read_only = read_only
        self.timeout = timeout
        self.retries = retries
        self._http: httpx.Client | None = None
        # resource namespaces attached in Tasks 6-13, e.g.:
        # self.users = Users(self)

    @property
    def http(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Authorization": self.api_key,
                    "Accept": "application/json",
                },
            )
        return self._http

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None

    def __enter__(self) -> "GalaxyClient":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        method = method.upper()
        if method in _WRITE_METHODS and (self.read_only or env_read_only()):
            raise ReadOnlyError(f"{method} {path} blocked: read-only mode is on")
        attempt = 0
        while True:
            response = self.http.request(method, path, params=params, json=json)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < self.retries:
                    time.sleep(0.5 * 2**attempt)
                    attempt += 1
                    continue
            break
        if response.status_code >= 400:
            raise GalaxyHTTPError.for_status(response.status_code, response.text[:500])
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return None

    def get_data(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return _unwrap(self.request("GET", path, params=params))

    def paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        per_page: int = MAX_PER_PAGE,
    ) -> Iterator[dict[str, Any]]:
        """Iterate all rows of a list endpoint via per_page/since_id paging.

        The API answers 404 for "no results", so that ends iteration.
        """
        base = {k: v for k, v in (params or {}).items() if v is not None}
        base.setdefault("per_page", per_page)
        since_id = base.pop("since_id", None)
        while True:
            query = dict(base)
            if since_id is not None:
                query["since_id"] = since_id
            try:
                rows = _unwrap(self.request("GET", path, params=query))
            except NotFoundError:
                return
            if not rows:
                return
            if not isinstance(rows, list):
                rows = [rows]
            yield from rows
            if len(rows) < int(query["per_page"]):
                return
            ids = [int(r["id"]) for r in rows if isinstance(r, dict) and r.get("id") is not None]
            if not ids:
                return
            since_id = max(ids)
```

- [ ] **Step 5:** `just test tests/test_client.py` → PASS.
- [ ] **Step 6: Commit.** `git commit -am "feat: GalaxyClient transport with read-only choke point"`

---

### Task 6: Resource base plumbing

**Goal:** `Resource` base class + CRUD mixins so each resource module is declarative.

**Files:**
- Create: `src/get_connected_cli/resources/__init__.py` (empty), `resources/base.py`
- Test: `tests/test_resources_base.py`

**Acceptance Criteria:**
- [ ] A resource subclass gets `list/get/create/update/delete` from mixins using `path`/`model`
- [ ] `list()` yields parsed models; `show_inactive=True` sends `"Yes"`
- [ ] `_get_list()` returns `[]` on 404; `create/update` parse a returned `data` dict, else return raw payload

**Verify:** `just test tests/test_resources_base.py` → PASS

**Steps:**

- [ ] **Step 1: failing tests** (`tests/test_resources_base.py`):

```python
from get_connected_cli.models.common import Tag
from get_connected_cli.resources.base import (
    CreateMixin, DeleteMixin, GetMixin, ListMixin, Resource, UpdateMixin,
)


class Widgets(ListMixin, GetMixin, CreateMixin, UpdateMixin, DeleteMixin, Resource):
    path = "/widgets"
    model = Tag


def test_list_parses_and_filters(client, api):
    route = api.get("/widgets").respond(
        json={"data": [{"id": 1, "name": "a"}]}
    )
    rows = list(Widgets(client).list(show_inactive=True, since_created="2024-01-01"))
    assert isinstance(rows[0], Tag) and rows[0].name == "a"
    params = route.calls.last.request.url.params
    assert params["show_inactive"] == "Yes"
    assert params["since_created"] == "2024-01-01"


def test_get(client, api):
    api.get("/widgets/5").respond(json={"data": {"id": 5, "name": "w"}})
    assert Widgets(client).get(5).id == 5


def test_create_update_delete(client, api):
    api.post("/widgets").respond(json={"data": {"id": 9, "name": "n"}})
    made = Widgets(client).create(name="n")
    assert made.id == 9
    api.put("/widgets/9").respond(json={})
    assert Widgets(client).update(9, name="m") == {}
    route = api.delete("/widgets/9").respond(json={})
    Widgets(client).delete(9)
    assert route.called


def test_sublist_404_empty(client, api):
    api.get("/widgets/1/things").respond(status_code=404)
    assert Widgets(client)._get_list("/widgets/1/things", Tag) == []
```

- [ ] **Step 2:** run → FAIL. **Step 3: implement** `resources/base.py`:

```python
"""Declarative plumbing shared by all resource namespaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Iterator

from ..exceptions import NotFoundError
from ..models.base import GalaxyModel

if TYPE_CHECKING:
    from ..client import GalaxyClient


class Resource:
    path: ClassVar[str]
    model: ClassVar[type[GalaxyModel]]

    def __init__(self, client: "GalaxyClient"):
        self._client = client

    def _url(self, *parts: Any) -> str:
        return "/".join([self.path, *[str(p) for p in parts]])

    def _parse(self, payload: Any, model: type[GalaxyModel] | None = None) -> Any:
        model = model or self.model
        if isinstance(payload, dict):
            return model.model_validate(payload)
        return payload

    def _get_one(self, url: str, model: type[GalaxyModel] | None = None) -> Any:
        return self._parse(self._client.get_data(url), model)

    def _get_list(self, url: str, model: type[GalaxyModel] | None = None) -> list[Any]:
        model = model or self.model
        try:
            rows = self._client.get_data(url) or []
        except NotFoundError:
            return []
        if not isinstance(rows, list):
            rows = [rows]
        return [model.model_validate(r) if isinstance(r, dict) else r for r in rows]


class ListMixin(Resource):
    def list(
        self,
        *,
        per_page: int = 150,
        since_id: int | None = None,
        since_created: str | None = None,
        since_updated: str | None = None,
        show_inactive: bool | None = None,
        **filters: Any,
    ) -> Iterator[GalaxyModel]:
        params: dict[str, Any] = {
            "since_id": since_id,
            "since_created": since_created,
            "since_updated": since_updated,
            **filters,
        }
        if show_inactive is not None:
            params["show_inactive"] = "Yes" if show_inactive else "No"
        for row in self._client.paginate(self.path, params, per_page=per_page):
            yield self.model.model_validate(row)


class GetMixin(Resource):
    def get(self, id: int) -> GalaxyModel:
        return self._get_one(self._url(id))


class CreateMixin(Resource):
    def create(self, **fields: Any) -> Any:
        payload = self._client.request("POST", self.path, json=fields)
        data = payload.get("data") if isinstance(payload, dict) else None
        return self._parse(data) if isinstance(data, dict) else payload


class UpdateMixin(Resource):
    def update(self, id: int, **fields: Any) -> Any:
        payload = self._client.request("PUT", self._url(id), json=fields)
        data = payload.get("data") if isinstance(payload, dict) else None
        return self._parse(data) if isinstance(data, dict) else payload


class DeleteMixin(Resource):
    def delete(self, id: int) -> None:
        self._client.request("DELETE", self._url(id))
```

- [ ] **Step 4:** run → PASS. **Step 5: Commit.** `git commit -am "feat: resource base and CRUD mixins"`

---

### Task 7: CLI skeleton, output, confirmation, config commands

**Goal:** Real typer app with global options, rich/JSON output helper, write-confirmation helper, `galaxy config` commands, top-level error handling.

**Files:**
- Modify: `src/get_connected_cli/cli/__init__.py` (replace stub)
- Create: `cli/_state.py`, `cli/_output.py`, `cli/_confirm.py`, `cli/config_cmds.py`
- Test: `tests/test_cli_root.py`

**Acceptance Criteria:**
- [ ] `galaxy --version` prints the package version
- [ ] Global options: `--api-key`, `--url`, `--read-only`, `--json`, `--yes`, `--debug`
- [ ] `galaxy config set/show/path/unset` manage the TOML file; `show` redacts the key to last 4 chars
- [ ] `GalaxyError` exits code 1 with a stderr message, no traceback (unless `--debug`)
- [ ] Declining a `confirm_write` prompt aborts with exit code 1; `--yes` skips the prompt

**Verify:** `just test tests/test_cli_root.py` → PASS

**Steps:**

- [ ] **Step 1: failing tests** (`tests/test_cli_root.py`):

```python
import json

from typer.testing import CliRunner

import get_connected_cli
from get_connected_cli.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert get_connected_cli.__version__ in result.output


def test_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("GALAXY_CONFIG_FILE", str(tmp_path / "c.toml"))
    assert runner.invoke(app, ["config", "set", "api_key", "secret1234"]).exit_code == 0
    shown = runner.invoke(app, ["config", "show"])
    assert "secret1234" not in shown.output
    assert "1234" in shown.output
    assert str(tmp_path / "c.toml") in runner.invoke(app, ["config", "path"]).output
    assert runner.invoke(app, ["config", "unset", "api_key"]).exit_code == 0
    assert "api_key" not in runner.invoke(app, ["config", "show"]).output


def test_galaxy_error_is_clean(monkeypatch):
    # no API key anywhere -> MissingAPIKeyError -> clean exit 1
    monkeypatch.delenv("GALAXY_API_KEY", raising=False)
    result = runner.invoke(app, ["causes", "list"])
    assert result.exit_code == 1
    assert "Traceback" not in result.output
```

Note: `causes list` lands in Task 13; until then replace that last test's command with any wired command and revisit — simplest is to add the test in Task 13 instead if it can't pass yet. Acceptable to defer ONLY that third test.

- [ ] **Step 2:** run → FAIL. **Step 3: implement.**

`cli/_state.py`:

```python
"""Per-invocation CLI state built by the root callback."""

from __future__ import annotations

from dataclasses import dataclass

from ..client import GalaxyClient
from ..config import Settings


@dataclass
class State:
    settings: Settings
    json_output: bool = False
    assume_yes: bool = False
    debug: bool = False
    _client: GalaxyClient | None = None

    @property
    def client(self) -> GalaxyClient:
        if self._client is None:
            self._client = GalaxyClient(
                api_key=self.settings.api_key,
                base_url=self.settings.url,
                read_only=self.settings.read_only,
            )
        return self._client
```

`cli/_output.py`:

```python
"""Render rows as a rich table or raw JSON."""

from __future__ import annotations

import json
from typing import Any, Iterable, Sequence

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)


def _to_dict(row: Any) -> dict:
    if isinstance(row, BaseModel):
        return row.model_dump()
    return row if isinstance(row, dict) else {"value": row}


def output(state, rows: Iterable[Any], columns: Sequence[str], title: str = "") -> None:
    data = [_to_dict(r) for r in rows]
    if state.json_output:
        console.print_json(json.dumps(data, default=str))
        return
    table = Table(title=title or None)
    for col in columns:
        table.add_column(col)
    for item in data:
        table.add_row(*[str(item.get(c, "")) for c in columns])
    console.print(table)


def output_one(state, row: Any) -> None:
    item = _to_dict(row)
    if state.json_output:
        console.print_json(json.dumps(item, default=str))
        return
    table = Table(show_header=False)
    table.add_column("field", style="bold")
    table.add_column("value")
    for key, value in item.items():
        table.add_row(key, str(value))
    console.print(table)
```

`cli/_confirm.py`:

```python
"""Interactive gate in front of every CLI write against production."""

from __future__ import annotations

import json
from typing import Any

import typer

from ._output import console


def confirm_write(state, description: str, payload: Any = None) -> None:
    """Show what is about to be written and require consent (unless --yes)."""
    if state.assume_yes:
        return
    console.print(f"[bold red]About to write to the API:[/] {description}")
    if payload:
        console.print_json(json.dumps(payload, default=str))
    if not typer.confirm("Proceed?"):
        raise typer.Abort()
```

`cli/config_cmds.py`:

```python
"""galaxy config — manage the config file."""

from __future__ import annotations

import typer

from .. import config
from ._output import console

config_app = typer.Typer(help="View and edit the config file.")

_BOOL_KEYS = {"read_only"}
_VALID_KEYS = {"api_key", "url", "read_only"}


@config_app.command()
def path() -> None:
    """Print the config file location."""
    console.print(str(config.config_file()))


@config_app.command()
def show() -> None:
    """Show config values (API key redacted)."""
    for key, value in config.read_config().items():
        if key == "api_key" and isinstance(value, str) and value:
            value = "…" + value[-4:]
        console.print(f"{key} = {value}")


@config_app.command("set")
def set_(key: str, value: str) -> None:
    """Set KEY to VALUE in the config file."""
    if key not in _VALID_KEYS:
        raise typer.BadParameter(f"key must be one of {sorted(_VALID_KEYS)}")
    current = config.read_config()
    current[key] = value.lower() in {"1", "true", "yes", "on"} if key in _BOOL_KEYS else value
    config.save_config(current)
    console.print(f"wrote {config.config_file()}")


@config_app.command()
def unset(key: str) -> None:
    """Remove KEY from the config file."""
    current = config.read_config()
    current.pop(key, None)
    config.save_config(current)
```

`cli/__init__.py` (replace stub):

```python
"""Typer application for the galaxy command."""

from __future__ import annotations

from typing import Optional

import typer

import get_connected_cli

from ..config import load_settings
from ..exceptions import GalaxyError
from ._output import err_console
from ._state import State
from .config_cmds import config_app

app = typer.Typer(
    help="CLI for the Galaxy Digital Get Connected API.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)
app.add_typer(config_app, name="config")
# Resource sub-apps registered in Tasks 8-13:
# app.add_typer(users_app, name="users")


def _version(value: bool) -> None:
    if value:
        typer.echo(get_connected_cli.__version__)
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key (or GALAXY_API_KEY)."),
    url: Optional[str] = typer.Option(None, "--url", help="Server URL or alias us1/us2/ca."),
    read_only: bool = typer.Option(False, "--read-only", help="Block all writes."),
    json_output: bool = typer.Option(False, "--json", help="Emit raw JSON."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip write confirmations."),
    debug: bool = typer.Option(False, "--debug", help="Show tracebacks."),
    version: bool = typer.Option(False, "--version", callback=_version, is_eager=True),
) -> None:
    """Galaxy Digital API command line interface."""
    ctx.obj = State(
        settings=load_settings(api_key=api_key, url=url, read_only=read_only or None),
        json_output=json_output,
        assume_yes=yes,
        debug=debug,
    )


def run() -> None:  # used only if a console entry needs error wrapping
    app()
```

Error handling: typer surfaces exceptions; to satisfy "clean exit 1 on GalaxyError", wrap command bodies via a decorator in `cli/_state.py`:

```python
def handle_errors(fn):
    """Decorator for CLI commands: GalaxyError -> stderr + exit 1."""
    import functools

    import typer

    from ..exceptions import GalaxyError
    from ._output import err_console

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except GalaxyError as error:
            ctx = None
            err_console.print(f"[red]error:[/] {error}")
            raise typer.Exit(code=1) from error

    return wrapper
```

Every resource command in Tasks 8–13 is decorated `@handle_errors` (below `@<app>.command(...)`). If `--debug` is set, commands may simply re-raise: check `ctx.obj.debug` is unnecessary — typer prints the traceback when the exception propagates; keep it simple: `handle_errors` re-raises when `typer.get_current_context().obj.debug` is true.

- [ ] **Step 4:** run tests → PASS (defer only the `causes list` test if needed).
- [ ] **Step 5: Commit.** `git commit -am "feat: CLI skeleton, output/confirm helpers, config commands"`

---

## Resource tasks (8–13) — shared recipe

Each resource task follows the same TDD recipe; every task below lists its complete endpoint table, models, resource class code, and CLI commands.

1. Write tests first (respx for resource methods; CliRunner for CLI): for every method assert URL, HTTP verb, query params/body; for every write CLI command assert it prompts (input `n` → exit 1, no request) and `--yes` sends.
2. Implement the models file (fields verbatim from the named schema in `doc/api.yml`, typing rule from the header), the resource module, the CLI module.
3. Register: models in `models/__init__.py`; resource instance on `GalaxyClient.__init__` (e.g. `self.users = Users(self)`); sub-app in `cli/__init__.py` (`app.add_typer(users_app, name="users")`).
4. `just test tests/<file>` → PASS, then commit `feat: <resource> resource + CLI`.

CLI command naming: `list`, `get`, `create`, `update`, `delete`, plus sub-resource verbs shown per task. Write commands take fields as `--field value` options mirroring the request schema's properties (only the commonly-needed subset as options, plus `--data JSON` accepting arbitrary JSON merged over the options — this keeps full coverage without 30 options per command). `--data` example:

```python
import json as _json

def _merge_fields(data: str | None, **options) -> dict:
    fields = {k: v for k, v in options.items() if v is not None}
    if data:
        fields.update(_json.loads(data))
    return fields
```

Put `_merge_fields` in `cli/_state.py`.

---

### Task 8: Users

**Goal:** Full `/users` coverage — the largest resource (23 endpoints).

**Files:**
- Create: `src/get_connected_cli/models/users.py`, `resources/users.py`, `cli/users.py`
- Modify: `models/__init__.py`, `client.py` (attach), `cli/__init__.py` (register)
- Test: `tests/test_users.py`

**Endpoint table** (all under `/users`):

| Method | Path | Client API | Notes |
|---|---|---|---|
| GET | `/users` | `list(**filters)` | filters: `user_status`, `user_fname`, `user_lname`, `user_email`, `user_fname_like`, `user_lname_like`, `user_email_like` + std list params |
| POST | `/users` | `create(**fields)` | userRequestSchema |
| GET/PUT/DELETE | `/users/{id}` | `get/update/delete` | |
| GET | `/users/{id}/agencies` | `agencies(id)` → `list[AgencyMini]` | |
| POST/DELETE | `/users/{id}/agencies/{agency_id}` | `add_agency(id, agency_id)` / `remove_agency(id, agency_id)` | |
| GET | `/users/{id}/benchmarks` | `benchmarks(id)` → `list[BenchmarkMini]` | BenchmarkMini lands in Task 13; use a local `BenchmarkMini` in `models/users.py`? **No** — declare `BenchmarkMini` in `models/common.py` now (9 fields: `id, benchmark_status, benchmark_title, benchmark_icon, benchmark_hours, benchmark_date_start, benchmark_date_end, created_at, update_at`; hours/int fields int, rest str) |
| DELETE | `/users/{id}/benchmarks/{benchmark_id}` | `remove_benchmark(id, benchmark_id)` | |
| GET | `/users/{id}/causes` | `causes(id)` → `list[Cause]` | |
| POST/DELETE | `/users/{id}/causes/{cause_id}` | `add_cause` / `remove_cause` | |
| GET | `/users/{id}/extras` | `extras(id, subset=None)` → `list[Extra]` | query `subset` |
| POST | `/users/{id}/extras` | `set_extras(id, extras: dict, subset=None)` | body = extras dict |
| GET | `/users/{id}/hours` | `hours(id)` → `list[Hour]` | Hour model lands Task 11 → declare `Hour` in `models/hours.py` **in this task** (20 fields from hourObject; nested `user: UserMini`, `need: NeedMini`, `groups: list[GroupMini]`) and Task 11 reuses it |
| GET | `/users/{id}/interests` | `interests(id)` → `list[Interest]` | |
| POST/DELETE | `/users/{id}/interests/{interest_id}` | `add_interest` / `remove_interest` | |
| GET | `/users/{id}/welcomeEmail` | `send_welcome_email(id)` | GET but has a side effect — CLI treats it as a write (confirm) |
| GET | `/users/{id}/oneclick` | `oneclick(id)` → `UserOneclick` | |
| GET | `/users/{id}/optouts` | `optouts(id)` → `UserOptouts` | |
| POST/DELETE | `/users/{id}/optouts` | `add_optout(id, **body)` / `remove_optout(id, **body)` | DELETE with json body: needs `client.request("DELETE", path, json=...)` — supported |
| GET | `/users/{id}/qualifications` | `qualifications(id)` → `list[UserQualification]` | |
| GET/POST | `/users/{id}/registrationQuestions` | `registration_answers(id)` / `set_registration_answers(id, answers)` | |
| GET | `/users/{id}/responses` | `responses(id)` → `list[UserResponse]` | |
| GET | `/users/{id}/tracks` | `tracks(id)` → `list[TrackMini]` | |
| GET | `/users/{id}/tags` | `tags(id)` → `list[Tag]` | |
| POST | `/users/{id}/tags` | `add_tags(id, tags: list[str])` | body `{"tags": [...]}` per spec (check requestBody in doc/api.yml when implementing) |
| DELETE | `/users/{id}/tags/{tag_id}` | `remove_tag(id, tag_id)` | |

**Models** (`models/users.py`): `User` (userObject, 33 fields — copy every property name from `doc/api.yml`), `UserOneclick` (`link, expires, now`), `UserOptouts` (`id, email, optout_areas, date_added`), `UserQualification` (`id, domain_id, qualification_id, qualification_title, status, expires`), `UserResponse` (`id, need_id, date_start, duration, status, created_at, updated_at`), `RegistrationAnswer` (RegistrationResponseAnswerObject: `type, key, area, question_id, question, answer`).

**Resource class** (`resources/users.py`) — complete:

```python
"""/users resource namespace."""

from __future__ import annotations

from typing import Any

from ..models.common import (
    AgencyMini, BenchmarkMini, Cause, Extra, Interest, Tag, TrackMini,
)
from ..models.hours import Hour
from ..models.users import (
    RegistrationAnswer, User, UserOneclick, UserOptouts, UserQualification,
    UserResponse,
)
from .base import (
    CreateMixin, DeleteMixin, GetMixin, ListMixin, Resource, UpdateMixin,
)


class Users(ListMixin, GetMixin, CreateMixin, UpdateMixin, DeleteMixin, Resource):
    path = "/users"
    model = User

    def agencies(self, id: int) -> list[AgencyMini]:
        return self._get_list(self._url(id, "agencies"), AgencyMini)

    def add_agency(self, id: int, agency_id: int) -> Any:
        return self._client.request("POST", self._url(id, "agencies", agency_id))

    def remove_agency(self, id: int, agency_id: int) -> None:
        self._client.request("DELETE", self._url(id, "agencies", agency_id))

    def benchmarks(self, id: int) -> list[BenchmarkMini]:
        return self._get_list(self._url(id, "benchmarks"), BenchmarkMini)

    def remove_benchmark(self, id: int, benchmark_id: int) -> None:
        self._client.request("DELETE", self._url(id, "benchmarks", benchmark_id))

    def causes(self, id: int) -> list[Cause]:
        return self._get_list(self._url(id, "causes"), Cause)

    def add_cause(self, id: int, cause_id: int) -> Any:
        return self._client.request("POST", self._url(id, "causes", cause_id))

    def remove_cause(self, id: int, cause_id: int) -> None:
        self._client.request("DELETE", self._url(id, "causes", cause_id))

    def extras(self, id: int, subset: str | None = None) -> list[Extra]:
        params = {"subset": subset} if subset else None
        try:
            rows = self._client.get_data(self._url(id, "extras"), params) or []
        except self._client_not_found():
            return []
        return [Extra.model_validate(r) for r in rows]

    def set_extras(self, id: int, extras: dict[str, Any], subset: str | None = None) -> Any:
        params = {"subset": subset} if subset else None
        return self._client.request("POST", self._url(id, "extras"), params=params, json=extras)

    def hours(self, id: int) -> list[Hour]:
        return self._get_list(self._url(id, "hours"), Hour)

    def interests(self, id: int) -> list[Interest]:
        return self._get_list(self._url(id, "interests"), Interest)

    def add_interest(self, id: int, interest_id: int) -> Any:
        return self._client.request("POST", self._url(id, "interests", interest_id))

    def remove_interest(self, id: int, interest_id: int) -> None:
        self._client.request("DELETE", self._url(id, "interests", interest_id))

    def send_welcome_email(self, id: int) -> Any:
        return self._client.request("GET", self._url(id, "welcomeEmail"))

    def oneclick(self, id: int) -> UserOneclick:
        return self._get_one(self._url(id, "oneclick"), UserOneclick)

    def optouts(self, id: int) -> UserOptouts:
        return self._get_one(self._url(id, "optouts"), UserOptouts)

    def add_optout(self, id: int, **body: Any) -> Any:
        return self._client.request("POST", self._url(id, "optouts"), json=body)

    def remove_optout(self, id: int, **body: Any) -> Any:
        return self._client.request("DELETE", self._url(id, "optouts"), json=body)

    def qualifications(self, id: int) -> list[UserQualification]:
        return self._get_list(self._url(id, "qualifications"), UserQualification)

    def registration_answers(self, id: int) -> list[RegistrationAnswer]:
        return self._get_list(self._url(id, "registrationQuestions"), RegistrationAnswer)

    def set_registration_answers(self, id: int, answers: Any) -> Any:
        return self._client.request(
            "POST", self._url(id, "registrationQuestions"), json=answers
        )

    def responses(self, id: int) -> list[UserResponse]:
        return self._get_list(self._url(id, "responses"), UserResponse)

    def tracks(self, id: int) -> list[TrackMini]:
        return self._get_list(self._url(id, "tracks"), TrackMini)

    def tags(self, id: int) -> list[Tag]:
        return self._get_list(self._url(id, "tags"), Tag)

    def add_tags(self, id: int, tags: list[str]) -> Any:
        return self._client.request("POST", self._url(id, "tags"), json={"tags": tags})

    def remove_tag(self, id: int, tag_id: int) -> None:
        self._client.request("DELETE", self._url(id, "tags", tag_id))
```

`_client_not_found()` above is wrong — in `extras`, just reuse the same try/except as `_get_list` uses (`except NotFoundError: return []`, importing `NotFoundError` from `..exceptions`). Implement it that way.

Attach in `GalaxyClient.__init__` (import inside method body or at module top — module top of `client.py` would be circular; import inside `__init__`):

```python
        from .resources.users import Users
        self.users = Users(self)
```

(Each later resource task appends its own import/attach lines here.)

**CLI** (`cli/users.py`): commands `list` (options: `--per-page --since-id --since-created --since-updated --show-inactive --status --fname --lname --email --fname-like --lname-like --email-like`), `get ID`, `create`, `update ID`, `delete ID`, `agencies ID`, `add-agency ID AGENCY_ID`, `remove-agency ID AGENCY_ID`, `benchmarks ID`, `remove-benchmark ID BENCHMARK_ID`, `causes ID`, `add-cause`/`remove-cause ID CAUSE_ID`, `extras ID [--subset]`, `set-extras ID --data JSON`, `hours ID`, `interests ID`, `add-interest`/`remove-interest ID INTEREST_ID`, `welcome-email ID` (confirmed), `oneclick ID`, `optouts ID`, `add-optout ID --data JSON`, `remove-optout ID --data JSON`, `qualifications ID`, `registration-questions ID`, `set-registration-questions ID --data JSON`, `responses ID`, `tracks ID`, `tags ID`, `add-tags ID TAG...`, `remove-tag ID TAG_ID`.

Representative command shapes (repeat the pattern for the rest):

```python
"""galaxy users …"""

from __future__ import annotations

from typing import Optional

import typer

from ._confirm import confirm_write
from ._output import output, output_one
from ._state import _merge_fields, handle_errors

users_app = typer.Typer(help="Manage users.")

LIST_COLUMNS = ["id", "user_fname", "user_lname", "user_email", "user_status"]


@users_app.command("list")
@handle_errors
def list_(
    ctx: typer.Context,
    per_page: int = typer.Option(150, max=150),
    since_id: Optional[int] = None,
    since_created: Optional[str] = None,
    since_updated: Optional[str] = None,
    show_inactive: bool = typer.Option(False, "--show-inactive"),
    status: Optional[str] = typer.Option(None, "--status"),
    email: Optional[str] = typer.Option(None, "--email"),
    email_like: Optional[str] = typer.Option(None, "--email-like"),
    fname: Optional[str] = typer.Option(None, "--fname"),
    fname_like: Optional[str] = typer.Option(None, "--fname-like"),
    lname: Optional[str] = typer.Option(None, "--lname"),
    lname_like: Optional[str] = typer.Option(None, "--lname-like"),
):
    """List users."""
    state = ctx.obj
    rows = state.client.users.list(
        per_page=per_page,
        since_id=since_id,
        since_created=since_created,
        since_updated=since_updated,
        show_inactive=show_inactive or None,
        user_status=status,
        user_email=email,
        user_email_like=email_like,
        user_fname=fname,
        user_fname_like=fname_like,
        user_lname=lname,
        user_lname_like=lname_like,
    )
    output(state, rows, LIST_COLUMNS, title="users")


@users_app.command()
@handle_errors
def get(ctx: typer.Context, id: int):
    """Fetch one user."""
    output_one(ctx.obj, ctx.obj.client.users.get(id))


@users_app.command()
@handle_errors
def create(
    ctx: typer.Context,
    fname: Optional[str] = typer.Option(None, "--fname"),
    lname: Optional[str] = typer.Option(None, "--lname"),
    email: Optional[str] = typer.Option(None, "--email"),
    data: Optional[str] = typer.Option(None, "--data", help="JSON merged over options"),
):
    """Create a user (userRequestSchema fields via --data)."""
    state = ctx.obj
    fields = _merge_fields(data, user_fname=fname, user_lname=lname, user_email=email)
    confirm_write(state, "POST /users", fields)
    output_one(state, state.client.users.create(**fields))


@users_app.command()
@handle_errors
def delete(ctx: typer.Context, id: int):
    """Delete a user."""
    confirm_write(ctx.obj, f"DELETE /users/{id}")
    ctx.obj.client.users.delete(id)
    typer.echo("deleted")
```

**Tests** (`tests/test_users.py`) must cover: every resource method's URL+verb (respx), `list` filter param mapping, `welcome-email` CLI confirms, `create` CLI prompts (input `n` → no request; `--yes` → request sent), `--json` output parses as JSON. Representative test shapes:

```python
import json

from typer.testing import CliRunner

from get_connected_cli.cli import app

runner = CliRunner()


def test_users_list_params(client, api):
    route = api.get("/users").respond(json={"data": [{"id": 1, "user_email": "a@b.c"}]})
    rows = list(client.users.list(user_email_like="a@"))
    assert rows[0].id == 1
    assert route.calls.last.request.url.params["user_email_like"] == "a@"


def test_add_agency(client, api):
    route = api.post("/users/3/agencies/7").respond(json={})
    client.users.add_agency(3, 7)
    assert route.called


def test_cli_create_prompts_and_aborts(api, monkeypatch):
    monkeypatch.setenv("GALAXY_API_URL", "https://api.test/api")
    result = runner.invoke(app, ["users", "create", "--email", "a@b.c"], input="n\n")
    assert result.exit_code != 0
    assert not api.calls


def test_cli_create_yes_sends(api, monkeypatch):
    monkeypatch.setenv("GALAXY_API_URL", "https://api.test/api")
    api.post("/users").respond(json={"data": {"id": 1, "user_email": "a@b.c"}})
    result = runner.invoke(app, ["--yes", "users", "create", "--email", "a@b.c"])
    assert result.exit_code == 0
```

**Verify:** `just test tests/test_users.py` → PASS. **Commit:** `feat: users resource and CLI`

---

### Task 9: Agencies

**Files:** Create `models/agencies.py` (`Agency` ← agencyObject, 36 fields from doc/api.yml), `resources/agencies.py`, `cli/agencies.py`; modify registries; test `tests/test_agencies.py`.

**Endpoints:** standard CRUD on `/agencies` (list params incl. `show_inactive`; body agencyRequestSchema) plus:

| Client API | Endpoint |
|---|---|
| `causes(id)` → `list[Cause]` | GET `/agencies/{id}/causes` |
| `add_cause(id, cause_id)` / `remove_cause(id, cause_id)` | POST/DELETE `/agencies/{id}/causes/{cause_id}` |
| `clusters(id)` → `list[Cluster]` | GET `/agencies/{id}/clusters` |
| `add_cluster(id, cluster_id)` / `remove_cluster(id, cluster_id)` | POST/DELETE `/agencies/{id}/clusters/{cluster_id}` |
| `managers(id)` → `list[UserMini]` | GET `/agencies/{id}/managers` |
| `add_manager(id, user_id)` / `remove_manager(id, user_id)` | POST/DELETE `/agencies/{id}/managers/{user_id}` |
| `tags(id)` → `list[Tag]` | GET `/agencies/{id}/tags` |
| `add_tags(id, tags: list[str])` | POST `/agencies/{id}/tags` (body per doc/api.yml inline schema) |
| `remove_tag(id, tag_id)` | DELETE `/agencies/{id}/tags/{tag_id}` |

**Resource class** — complete:

```python
"""/agencies resource namespace."""

from __future__ import annotations

from typing import Any

from ..models.agencies import Agency
from ..models.common import Cause, Cluster, Tag, UserMini
from .base import (
    CreateMixin, DeleteMixin, GetMixin, ListMixin, Resource, UpdateMixin,
)


class Agencies(ListMixin, GetMixin, CreateMixin, UpdateMixin, DeleteMixin, Resource):
    path = "/agencies"
    model = Agency

    def causes(self, id: int) -> list[Cause]:
        return self._get_list(self._url(id, "causes"), Cause)

    def add_cause(self, id: int, cause_id: int) -> Any:
        return self._client.request("POST", self._url(id, "causes", cause_id))

    def remove_cause(self, id: int, cause_id: int) -> None:
        self._client.request("DELETE", self._url(id, "causes", cause_id))

    def clusters(self, id: int) -> list[Cluster]:
        return self._get_list(self._url(id, "clusters"), Cluster)

    def add_cluster(self, id: int, cluster_id: int) -> Any:
        return self._client.request("POST", self._url(id, "clusters", cluster_id))

    def remove_cluster(self, id: int, cluster_id: int) -> None:
        self._client.request("DELETE", self._url(id, "clusters", cluster_id))

    def managers(self, id: int) -> list[UserMini]:
        return self._get_list(self._url(id, "managers"), UserMini)

    def add_manager(self, id: int, user_id: int) -> Any:
        return self._client.request("POST", self._url(id, "managers", user_id))

    def remove_manager(self, id: int, user_id: int) -> None:
        self._client.request("DELETE", self._url(id, "managers", user_id))

    def tags(self, id: int) -> list[Tag]:
        return self._get_list(self._url(id, "tags"), Tag)

    def add_tags(self, id: int, tags: list[str]) -> Any:
        return self._client.request("POST", self._url(id, "tags"), json={"tags": tags})

    def remove_tag(self, id: int, tag_id: int) -> None:
        self._client.request("DELETE", self._url(id, "tags", tag_id))
```

**CLI:** `galaxy agencies list/get/create/update/delete` (+ `causes/add-cause/remove-cause/clusters/add-cluster/remove-cluster/managers/add-manager/remove-manager/tags/add-tags/remove-tag`) — same shapes as Task 8. `LIST_COLUMNS = ["id", "agency_name", "agency_city", "agency_state"]`.

**Tests:** same categories as Task 8 (method URL/verb; one CLI confirm-abort; one CLI `--yes`).

**Verify:** `just test tests/test_agencies.py` → PASS. **Commit:** `feat: agencies resource and CLI`

---

### Task 10: Needs

**Files:** Create `models/needs.py` (`Need` ← needObject 36 fields; nested `agency: AgencyMini`, `initiative: InitiativeMini`, `groups: list[GroupMini]`; also `shifts: list[Shift]` if present in doc/api.yml), `resources/needs.py`, `cli/needs.py`; registries; test `tests/test_needs.py`.

**Endpoints:** CRUD on `/needs` (list filters: `agency_id`, `need_title`, `need_status` + std; body needRequestSchema) plus:

| Client API | Endpoint |
|---|---|
| `responses(id)` → `list[Response]` | GET `/needs/{id}/responses` — Response model is created in **Task 12**; to avoid ordering pain, declare `Response` in `models/responses.py` **in this task** (responseObject, 17 fields; nested `agency: AgencyMini`, `shift: Shift`, `need: NeedMini`, `user: UserMini`, `initiative: InitiativeMini`, `team: TeamMini`) and Task 12 reuses it |
| `add_shift(id, *, slots, start_date, start_time, duration)` | POST `/needs/{id}/shifts` (shiftRequestSchema) |
| `remove_shift(id, shift_id)` | DELETE `/needs/{id}/shifts/{shift_id}` |
| `add_interest(id, interest_id)` / `remove_interest(id, interest_id)` | POST/DELETE `/needs/{id}/interests/{interest_id}` |
| `add_qualification(id, qualification_id)` / `remove_qualification(id, qualification_id)` | POST/DELETE `/needs/{id}/qualifications/{qualification_id}` |
| `questions(id)` → `list[Question]` | GET `/needs/{id}/questions` |

**Resource class** — complete:

```python
"""/needs resource namespace."""

from __future__ import annotations

from typing import Any

from ..models.common import Question
from ..models.needs import Need
from ..models.responses import Response
from .base import (
    CreateMixin, DeleteMixin, GetMixin, ListMixin, Resource, UpdateMixin,
)


class Needs(ListMixin, GetMixin, CreateMixin, UpdateMixin, DeleteMixin, Resource):
    path = "/needs"
    model = Need

    def responses(self, id: int) -> list[Response]:
        return self._get_list(self._url(id, "responses"), Response)

    def add_shift(
        self, id: int, *, slots: int, start_date: str, start_time: str, duration: str
    ) -> Any:
        return self._client.request(
            "POST",
            self._url(id, "shifts"),
            json={
                "slots": slots,
                "start_date": start_date,
                "start_time": start_time,
                "duration": duration,
            },
        )

    def remove_shift(self, id: int, shift_id: int) -> None:
        self._client.request("DELETE", self._url(id, "shifts", shift_id))

    def add_interest(self, id: int, interest_id: int) -> Any:
        return self._client.request("POST", self._url(id, "interests", interest_id))

    def remove_interest(self, id: int, interest_id: int) -> None:
        self._client.request("DELETE", self._url(id, "interests", interest_id))

    def add_qualification(self, id: int, qualification_id: int) -> Any:
        return self._client.request("POST", self._url(id, "qualifications", qualification_id))

    def remove_qualification(self, id: int, qualification_id: int) -> None:
        self._client.request("DELETE", self._url(id, "qualifications", qualification_id))

    def questions(self, id: int) -> list[Question]:
        return self._get_list(self._url(id, "questions"), Question)
```

**CLI:** `galaxy needs list` (with `--agency-id --title --status` filters), `get/create/update/delete`, `responses ID`, `add-shift ID --slots N --start-date D --start-time T --duration H`, `remove-shift ID SHIFT_ID`, `add-interest/remove-interest`, `add-qualification/remove-qualification`, `questions ID`. `LIST_COLUMNS = ["id", "need_title", "need_status", "need_date_type"]` (confirm exact field names against needObject in doc/api.yml when implementing; substitute any missing column).

**Tests:** method URL/verb coverage incl. `add_shift` body assertion; CLI confirm-abort + `--yes` for `add-shift`.

**Verify:** `just test tests/test_needs.py` → PASS. **Commit:** `feat: needs resource and CLI`

---

### Task 11: Events & Hours

**Files:** Create `models/events.py` (`Event` ← eventObject, 21 fields), `resources/events.py`, `resources/hours.py`, `cli/events.py`, `cli/hours.py`; registries; test `tests/test_events_hours.py`. (`models/hours.py` already exists from Task 8.)

**Endpoints:**
- `/events`: CRUD, list params `per_page, since_id, since_created, since_updated` (no `show_inactive`); body eventRequestSchema.
- `/hours`: CRUD, std list params incl. `show_inactive`; body hourRequestSchema (`hour_hours, hour_miles, hour_start, hour_status, hour_location, hour_contact_name, hour_contact_details, hour_relationship, response_id, user_id, group_ids`).

**Resource classes** — complete:

```python
"""/events resource namespace."""

from ..models.events import Event
from .base import (
    CreateMixin, DeleteMixin, GetMixin, ListMixin, Resource, UpdateMixin,
)


class Events(ListMixin, GetMixin, CreateMixin, UpdateMixin, DeleteMixin, Resource):
    path = "/events"
    model = Event
```

```python
"""/hours resource namespace."""

from ..models.hours import Hour
from .base import (
    CreateMixin, DeleteMixin, GetMixin, ListMixin, Resource, UpdateMixin,
)


class Hours(ListMixin, GetMixin, CreateMixin, UpdateMixin, DeleteMixin, Resource):
    path = "/hours"
    model = Hour
```

**CLI:** `galaxy events list/get/create/update/delete`; `galaxy hours list/get/create/update/delete`. `hours create` gets explicit options `--user-id --response-id --hours --miles --start --status --description` plus `--data`. Events columns: `["id", "event_title", "event_date_start", "event_city"]`; hours columns: `["id", "hour_hours", "hour_date_start", "hour_status"]` (verify names against doc/api.yml; adjust to actual).

**Tests:** CRUD coverage for both via respx; one confirm test for `hours create`.

**Verify:** `just test tests/test_events_hours.py` → PASS. **Commit:** `feat: events and hours resources + CLI`

---

### Task 12: Responses, Teams & Groups

**Files:** Create `models/teams.py` (`Team` ← teamObject: nested `creator: UserMini`, `agency: AgencyMini`, `need: NeedMini`, `members: list[TeamMember]`; `TeamMember` ← teamMembersObject 6 fields), `models/groups.py` (`Group` ← groupObject 24 fields; `GroupUser` ← GroupUserMiniObject 6 fields), `resources/responses.py`, `resources/teams.py`, `resources/groups.py`, `cli/responses.py`, `cli/teams.py`, `cli/groups.py`; registries; test `tests/test_responses_teams_groups.py`. (`models/responses.py` exists from Task 10.)

**Endpoints:**
- `/responses`: full CRUD, std list params; body responseRequestSchema (`need_id, user_id, team_id, schedule_ids, response_note, questions, response_date_added`).
- `/teams`: list/create/get/delete (**no PUT**); body teamRequestSchema; plus POST/DELETE `/teams/{id}/member/{member}` → `add_member(id, member)` / `remove_member(id, member)`.
- `/groups`: full CRUD; body groupRequestSchema; plus POST/DELETE `/groups/{id}/needs/{need_id}` → `add_need/remove_need`; POST/DELETE `/groups/{id}/users/{user_id}` → `add_user/remove_user`.

**Resource classes** — complete:

```python
"""/responses resource namespace."""

from ..models.responses import Response
from .base import (
    CreateMixin, DeleteMixin, GetMixin, ListMixin, Resource, UpdateMixin,
)


class Responses(ListMixin, GetMixin, CreateMixin, UpdateMixin, DeleteMixin, Resource):
    path = "/responses"
    model = Response
```

```python
"""/teams resource namespace."""

from __future__ import annotations

from typing import Any

from ..models.teams import Team
from .base import CreateMixin, DeleteMixin, GetMixin, ListMixin, Resource


class Teams(ListMixin, GetMixin, CreateMixin, DeleteMixin, Resource):
    path = "/teams"
    model = Team

    def add_member(self, id: int, member: int) -> Any:
        return self._client.request("POST", self._url(id, "member", member))

    def remove_member(self, id: int, member: int) -> None:
        self._client.request("DELETE", self._url(id, "member", member))
```

```python
"""/groups resource namespace."""

from __future__ import annotations

from typing import Any

from ..models.groups import Group
from .base import (
    CreateMixin, DeleteMixin, GetMixin, ListMixin, Resource, UpdateMixin,
)


class Groups(ListMixin, GetMixin, CreateMixin, UpdateMixin, DeleteMixin, Resource):
    path = "/groups"
    model = Group

    def add_need(self, id: int, need_id: int) -> Any:
        return self._client.request("POST", self._url(id, "needs", need_id))

    def remove_need(self, id: int, need_id: int) -> None:
        self._client.request("DELETE", self._url(id, "needs", need_id))

    def add_user(self, id: int, user_id: int) -> Any:
        return self._client.request("POST", self._url(id, "users", user_id))

    def remove_user(self, id: int, user_id: int) -> None:
        self._client.request("DELETE", self._url(id, "users", user_id))
```

**CLI:** standard verbs per resource (`teams` has no `update`); `teams add-member/remove-member ID MEMBER`; `groups add-need/remove-need/add-user/remove-user`. Columns — responses: `["id", "response_date_added", "response_status"]`-style (verify against responseObject), teams: `["id", "team_title", "team_status"]`, groups: `["id", "ug_title", "ug_status"]`.

**Tests:** URL/verb coverage; teams lacks update (assert `not hasattr(client.teams, "update")`); one confirm test.

**Verify:** `just test tests/test_responses_teams_groups.py` → PASS. **Commit:** `feat: responses, teams, groups resources + CLI`

---

### Task 13: Qualifications, Benchmarks, Clusters, lookups & auth

**Files:** Create `models/qualifications.py` (`Qualification` ← qualificationObject 15 fields; `QualificationUser` ← qualificationUsersObject 7 fields), `models/benchmarks.py` (`Benchmark` ← benchmarkObject 12 fields), `models/auth.py` (`LoginResult` ← loginObject: `user: User` nested, `token, expires`), `resources/qualifications.py`, `resources/benchmarks.py`, `resources/misc.py`, `resources/auth.py`, `cli/qualifications.py`, `cli/benchmarks.py`, `cli/misc.py`, `cli/auth.py`; registries; test `tests/test_quals_benchmarks_misc.py`.

**Endpoints:**
- `/qualifications`: full CRUD + GET `/qualifications/{id}/users` → `users(id)` → `list[QualificationUser]`.
- `/benchmarks`: full CRUD + GET `/benchmarks/{id}/users` → `users(id)` → `list[UserMini]`.
- `/clusters`: GET list (**no pagination params in spec — still use paginate; harmless**), POST create (body `{"name": ...}`), DELETE `/clusters/{id}`. No get/update.
- Lookups (GET only, no params): `/causes` → `client.causes()`, `/interests` → `client.interests()`, `/impacts` → `client.impacts()`, `/questions/registration` → `client.registration_questions()` — implement in `resources/misc.py` as a `Lookups` resource with those four methods returning `list[Cause] / list[Interest] / list[Impact] / list[Question]`.
- Auth: POST `/users/login` (body `{user_email, user_password, key}`) → `LoginResult`; POST `/users/authenticate` (body `{user_email, user_password}`) → raw data. In `resources/auth.py` as `Auth.login(...)` / `Auth.authenticate(...)`. **These are POSTs but are not treated as writes by the CLI confirm gate** (they mutate nothing); they still pass through the read-only choke point, so document in the CLI help that `--read-only` blocks them.

**Resource classes** — complete:

```python
"""/qualifications and /benchmarks resource namespaces."""
# resources/qualifications.py

from ..models.qualifications import Qualification, QualificationUser
from .base import (
    CreateMixin, DeleteMixin, GetMixin, ListMixin, Resource, UpdateMixin,
)


class Qualifications(ListMixin, GetMixin, CreateMixin, UpdateMixin, DeleteMixin, Resource):
    path = "/qualifications"
    model = Qualification

    def users(self, id: int) -> list[QualificationUser]:
        return self._get_list(self._url(id, "users"), QualificationUser)
```

```python
# resources/benchmarks.py
from ..models.benchmarks import Benchmark
from ..models.common import UserMini
from .base import (
    CreateMixin, DeleteMixin, GetMixin, ListMixin, Resource, UpdateMixin,
)


class Benchmarks(ListMixin, GetMixin, CreateMixin, UpdateMixin, DeleteMixin, Resource):
    path = "/benchmarks"
    model = Benchmark

    def users(self, id: int) -> list[UserMini]:
        return self._get_list(self._url(id, "users"), UserMini)
```

```python
# resources/misc.py
"""Clusters and read-only lookup endpoints."""

from __future__ import annotations

from typing import Any

from ..models.common import Cause, Cluster, Impact, Interest, Question
from .base import CreateMixin, DeleteMixin, ListMixin, Resource


class Clusters(ListMixin, CreateMixin, DeleteMixin, Resource):
    path = "/clusters"
    model = Cluster


class Lookups(Resource):
    path = ""
    model = Cause  # unused

    def causes(self) -> list[Cause]:
        return self._get_list("/causes", Cause)

    def interests(self) -> list[Interest]:
        return self._get_list("/interests", Interest)

    def impacts(self) -> list[Impact]:
        return self._get_list("/impacts", Impact)

    def registration_questions(self) -> list[Question]:
        return self._get_list("/questions/registration", Question)
```

```python
# resources/auth.py
"""Login endpoints (user-level auth)."""

from __future__ import annotations

from typing import Any

from ..models.auth import LoginResult
from .base import Resource


class Auth(Resource):
    path = "/users"
    model = LoginResult

    def login(self, user_email: str, user_password: str, key: str | None = None) -> LoginResult:
        body: dict[str, Any] = {"user_email": user_email, "user_password": user_password}
        if key:
            body["key"] = key
        payload = self._client.request("POST", "/users/login", json=body)
        data = payload.get("data") if isinstance(payload, dict) else payload
        return LoginResult.model_validate(data or {})

    def authenticate(self, user_email: str, user_password: str) -> Any:
        payload = self._client.request(
            "POST",
            "/users/authenticate",
            json={"user_email": user_email, "user_password": user_password},
        )
        return payload.get("data") if isinstance(payload, dict) else payload
```

Attach: `client.qualifications`, `client.benchmarks`, `client.clusters`, `client.lookups`, `client.auth`.

**CLI:** `galaxy qualifications list/get/create/update/delete/users`; `galaxy benchmarks …/users`; `galaxy clusters list/create/delete`; `galaxy causes list`, `galaxy interests list`, `galaxy impacts list`, `galaxy registration-questions list` (four tiny sub-apps in `cli/misc.py`); `galaxy auth login --email --password [--key]` (password via `typer.Option(..., prompt=True, hide_input=True)` when not given), `galaxy auth authenticate --email --password`.

Also add now (deferred from Task 7): the `test_galaxy_error_is_clean` test using `causes list` with no API key.

**Tests:** URL/verb coverage for every method above; lookups return `[]` on 404; login parses `LoginResult`.

**Verify:** `just test tests/test_quals_benchmarks_misc.py tests/test_cli_root.py` → PASS. **Commit:** `feat: qualifications, benchmarks, clusters, lookups, auth + CLI`

---

### Task 14: Live test suites (opt-in)

**Goal:** Read-only live smoke tests behind `-m live`; write tests behind `-m live_write` + ack env var. **Never run `live_write` without the user present.**

**Files:**
- Create: `tests/live/__init__.py`, `tests/live/test_live_read.py`, `tests/live/test_live_write.py`

**Acceptance Criteria:**
- [ ] `just test` (default) collects zero live tests
- [ ] `uv run pytest -m live` skips cleanly when `GALAXY_API_KEY` unset
- [ ] `live_write` tests skip unless `GALAXY_LIVE_WRITE_ACK=I-UNDERSTAND-THIS-WRITES-TO-PROD`

**Steps:**

- [ ] **Step 1:** `tests/live/test_live_read.py`:

```python
"""Read-only smoke tests against the real API. Run: pytest -m live"""

import os

import pytest

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.environ.get("GALAXY_API_KEY"), reason="GALAXY_API_KEY not set"
    ),
]


@pytest.fixture(scope="module")
def live_client():
    from get_connected_cli.client import GalaxyClient

    with GalaxyClient(read_only=True) as c:  # belt and suspenders
        yield c


def test_auth_and_causes(live_client):
    causes = live_client.lookups.causes()
    assert isinstance(causes, list)


def test_list_users_first_page(live_client):
    users = []
    for user in live_client.users.list(per_page=5):
        users.append(user)
        if len(users) >= 5:
            break
    assert users and users[0].id


def test_read_only_client_blocks_writes(live_client):
    from get_connected_cli.exceptions import ReadOnlyError

    with pytest.raises(ReadOnlyError):
        live_client.users.create(user_fname="nope")
```

- [ ] **Step 2:** `tests/live/test_live_write.py`:

```python
"""LIVE WRITE tests — touch production. Only run with the user present:

    GALAXY_LIVE_WRITE_ACK=I-UNDERSTAND-THIS-WRITES-TO-PROD pytest -m live_write

The specific scenarios are agreed with the user at run time; this file
starts with a single reversible round-trip and grows only by explicit
agreement.
"""

import os

import pytest

ACK = "I-UNDERSTAND-THIS-WRITES-TO-PROD"

pytestmark = [
    pytest.mark.live_write,
    pytest.mark.skipif(
        not os.environ.get("GALAXY_API_KEY"), reason="GALAXY_API_KEY not set"
    ),
    pytest.mark.skipif(
        os.environ.get("GALAXY_LIVE_WRITE_ACK") != ACK,
        reason="GALAXY_LIVE_WRITE_ACK not acknowledged",
    ),
]


@pytest.fixture(scope="module")
def live_client():
    from get_connected_cli.client import GalaxyClient

    with GalaxyClient() as c:
        yield c


def test_cluster_round_trip(live_client):
    """Create a throwaway cluster, verify it exists, delete it."""
    made = live_client.clusters.create(name="get-connected-cli-selftest")
    made_id = made.id if hasattr(made, "id") else None
    if made_id is None:
        pytest.skip("API did not return the created cluster id; clean up manually")
    try:
        names = [c.name for c in live_client.clusters.list()]
        assert "get-connected-cli-selftest" in names
    finally:
        live_client.clusters.delete(made_id)
```

- [ ] **Step 3:** Verify default run collects none: `just test 2>&1 | grep -c "live"` and `uv run pytest -m live --collect-only` (skips without key). **Commit:** `test: opt-in live smoke suites`

---

### Task 15: Documentation & README

**Goal:** Sphinx docs (quickstart, configuration, CLI reference, API reference) and a README with install/usage.

**Files:**
- Create/Modify: `doc/source/index.rst`, `doc/source/quickstart.rst`, `doc/source/configuration.rst`, `doc/source/cli.rst`, `doc/source/api.rst` (autodoc for `client`, `exceptions`, `config`, `models`, `resources`)
- Modify: `README.md`

**Acceptance Criteria:**
- [ ] `just docs` builds without errors; `just check-docs` passes
- [ ] README covers: install, `galaxy config set api_key …`, read-only safety model, one library example, one CLI example

**Steps:**

- [ ] **Step 1:** README sections: What/Install (`pip install get-connected-cli`)/Quickstart (library: `with GalaxyClient() as c: for u in c.users.list(): ...`; CLI: `galaxy users list --per-page 10`)/Configuration (env vars + config file + precedence table)/Write safety (read-only modes, `--yes`, `GALAXY_READ_ONLY`)/Development (`just setup`, `just test`, live markers).
- [ ] **Step 2:** Sphinx pages; `api.rst` uses `automodule` for each public module. Match the existing `doc/` scaffold conventions.
- [ ] **Step 3:** `just docs && just check-docs` → build clean. **Commit:** `docs: sphinx docs and README`

---

### Task 16: Public exports & final verification

**Goal:** Clean public API surface; whole-project quality gates pass.

**Files:**
- Modify: `src/get_connected_cli/__init__.py`

**Acceptance Criteria:**
- [ ] `from get_connected_cli import GalaxyClient` works; exceptions importable from top level
- [ ] `just check` passes (ruff, bandit, doc8, readme)
- [ ] `just check-types` passes (mypy + pyright)
- [ ] `just test-all` passes; coverage of `src/get_connected_cli` ≥ 90%

**Steps:**

- [ ] **Step 1:** Append to `src/get_connected_cli/__init__.py` (keep the banner):

```python
from .client import GalaxyClient
from .exceptions import (
    AuthError,
    GalaxyError,
    GalaxyHTTPError,
    MissingAPIKeyError,
    NotFoundError,
    RateLimitError,
    ReadOnlyError,
    ValidationFailedError,
)

__all__ = [
    "GalaxyClient",
    "AuthError",
    "GalaxyError",
    "GalaxyHTTPError",
    "MissingAPIKeyError",
    "NotFoundError",
    "RateLimitError",
    "ReadOnlyError",
    "ValidationFailedError",
]
```

Add a test in `tests/test_package.py` asserting the imports.

- [ ] **Step 2:** `just fix && just check && just check-types` → all green; fix fallout.
- [ ] **Step 3:** `just test-all` → PASS; check coverage report; add tests for any big uncovered branch.
- [ ] **Step 4: Commit.** `git commit -am "feat: public API exports; fix lint/type findings"`

---

## Post-plan checklist

- Live read smoke (`pytest -m live`) — run once with the user's key to confirm the `Authorization` header format and envelope assumptions. **Ask the user before running even read-only calls the first time.**
- Live write round-trip — **only with the user present**, per Task 14.
- `just release` remains untouched; publishing is the user's call.
