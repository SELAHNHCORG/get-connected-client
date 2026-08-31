# Galaxy Digital API Client & CLI — Design

**Date:** 2026-08-17
**Status:** Approved

## Goal

A typed Python client library and a typer-based CLI for the Galaxy Digital
"Get Connected" API (v1.9.2), with full coverage of the 66 endpoints in the
published OpenAPI 3.0 spec (`https://api.galaxydigital.com/docs/api.yml`).
The user's API key targets a **production** instance: the library must support
writes, but accidental writes must be structurally impossible to trigger
without explicit opt-in, and write tests only run with the user in the loop.

## API Facts (from the spec)

- OpenAPI 3.0, 66 paths, ~15 resource groups: users, agencies, needs, events,
  hours, responses, teams, groups, qualifications, benchmarks, clusters,
  causes, interests, impacts, tags, registration questions.
- Servers: US1 `https://api.galaxydigital.com/api` (default),
  US2 `https://www.volunteerapi.com/api`, CA `https://ca.volunteerapi.com/api`.
- Auth: API key sent in the `Authorization` header (spec's "Bearer" apiKey
  scheme). `/users/login` and `/users/authenticate` exist for user-level auth.
- Responses wrap payloads in a `{"data": ...}` envelope.
- List endpoints paginate with `per_page` (max 150) and `since_id`, plus
  `since_created` / `since_updated` / `show_inactive` filters.

## Architecture

Hand-written sync client (httpx) with pydantic v2 models. No code generation:
66 endpoints is small enough to maintain by hand, and we control ergonomics.

```
src/get_connected_client/
├── __init__.py          # exports GalaxyClient, exceptions, __version__
├── client.py            # GalaxyClient: transport, auth, retries, pagination
├── config.py            # settings resolution: env vars > config file > defaults
├── exceptions.py        # GalaxyError, AuthError, NotFoundError,
│                        # ValidationFailedError, ReadOnlyError, RateLimitError
├── models/              # pydantic models per resource (extra="allow")
└── resources/
    ├── base.py          # shared list/get/create/update/delete plumbing
    ├── users.py needs.py hours.py events.py agencies.py responses.py
    ├── teams.py groups.py qualifications.py benchmarks.py clusters.py
    └── misc.py          # causes, interests, impacts (read-only lookups)
src/get_connected_client/cli/   # typer app; one sub-app per resource
```

### Client core

- `GalaxyClient(api_key=..., base_url=US1, read_only=False, timeout=30)`;
  usable as a context manager; lazily-created `httpx.Client`.
- Resource namespaces: `client.users`, `client.needs`, `client.hours`, … each
  exposing `list()`, `get(id)`, `create(...)`, `update(id, ...)`,
  `delete(id)`, and the sub-resource operations from the spec
  (e.g. `client.users.tags(id)`, `client.needs.add_shift(id, ...)`).
- `list()` returns a generator that auto-paginates using `per_page`/`since_id`
  until the server returns an empty page.
- The `{"data": ...}` envelope is unwrapped in one place; payloads validate
  into pydantic models with `extra="allow"` (the spec's schemas are loose;
  unknown fields must survive round-trips).
- Errors: 401 → `AuthError`, 404 → `NotFoundError`, 422 →
  `ValidationFailedError`, 429 → `RateLimitError`; 429/5xx retried with
  bounded exponential backoff.

### Write safety

- All requests funnel through one transport method; if the method is
  POST/PUT/DELETE and the client is read-only, `ReadOnlyError` raises
  **before any request is sent**. Single choke point, not per-method checks.
- `GALAXY_READ_ONLY=1` (any truthy value) forces read-only regardless of
  constructor arguments.
- CLI write commands print the exact payload/target and require interactive
  confirmation; `--yes` bypasses for scripting.

### Configuration

Resolution order (highest wins):

1. CLI flags (`--api-key`, `--url`, `--read-only`)
2. Env vars: `GALAXY_API_KEY`, `GALAXY_API_URL`, `GALAXY_READ_ONLY`
3. Config file `~/.config/galaxy-digital/config.toml` (via platformdirs):
   `api_key`, `url`, `read_only`
4. Defaults (US1 server, writes enabled at the library level)

`galaxy config` subcommands view/set the config file (key stored with 0600
perms; value redacted when displayed).

### CLI

- Entry point `galaxy` (typer + rich).
- One sub-app per resource: `galaxy users list --per-page 50`,
  `galaxy needs get 123`, `galaxy hours create --user-id … --hours …`,
  `galaxy users tags 42`, etc. Full endpoint coverage.
- Output: rich tables for humans (sensible column subset per resource);
  `--json` emits raw API JSON for scripting.
- Global options on the app callback: `--api-key`, `--url`, `--read-only`,
  `--json`, `--yes`.

## Error Handling

- Library raises the typed exception hierarchy; never sys.exit.
- CLI catches `GalaxyError` at the top level and prints a concise message to
  stderr with a non-zero exit code (readable failure, no tracebacks unless
  `--debug`).

## Testing

- **Unit tests (CI-safe):** all HTTP mocked with `respx`. Cover transport
  (auth header, envelope unwrap, pagination loop, retry, error mapping,
  read-only choke point), each resource's URL/method/params, and CLI commands
  via `typer.testing.CliRunner` with a mocked client. No network, ever.
- **Live read tests (opt-in):** `-m live`, skipped unless `GALAXY_API_KEY` is
  set AND the marker is explicitly selected. GET-only smoke tests.
- **Live write tests (user in the loop):** `-m live_write`, additionally
  require `GALAXY_LIVE_WRITE_ACK=I-UNDERSTAND-THIS-WRITES-TO-PROD`. Never run
  in CI; only run together with the user.
- Markers registered in pyproject (`--strict-markers` already on); default
  test run deselects `live`/`live_write`.

## Docs / Repo

- Vendor the spec as `doc/api.yml` (reference for future spec-drift checks).
- Sphinx docs in `doc/source/` per the existing scaffold: quickstart,
  configuration, CLI reference, API reference (autodoc).
- New runtime deps: `httpx`, `pydantic>=2`, `typer`, `rich`, `platformdirs`;
  test dep: `respx`. `[project.scripts] galaxy = "get_connected_client.cli:app"`.

## Out of Scope (YAGNI)

- Async client (can be added later without breaking the sync API).
- User-level login/token flows beyond exposing `/users/login` and
  `/users/authenticate` as plain client methods.
- Caching, bulk import/export tooling, spec-driven code generation.
