# get-connected-client
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PyPI version](https://badge.fury.io/py/get-connected-client.svg)](https://pypi.python.org/pypi/get-connected-client/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/get-connected-client.svg)](https://pypi.python.org/pypi/get-connected-client/)
[![PyPI status](https://img.shields.io/pypi/status/get-connected-client.svg)](https://pypi.python.org/pypi/get-connected-client)
[![PyPI - Types](https://img.shields.io/pypi/types/get-connected-client.svg)](https://pypi.python.org/pypi/get-connected-client)
[![Documentation Status](https://readthedocs.org/projects/get-connected-client/badge/?version=latest)](http://get-connected-client.readthedocs.io/en/latest/)
[![Code Cov](https://codecov.io/gh/SELAHNHCORG/get-connected-client/branch/main/graph/badge.svg?token=0IZOKN2DYL)](https://codecov.io/gh/SELAHNHCORG/get-connected-client)
[![Test Status](https://github.com/SELAHNHCORG/get-connected-client/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/SELAHNHCORG/get-connected-client/actions/workflows/test.yml?query=branch:main)
[![Lint Status](https://github.com/SELAHNHCORG/get-connected-client/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/SELAHNHCORG/get-connected-client/actions/workflows/lint.yml?query=branch:main)
[![CodeQL](https://github.com/SELAHNHCORG/get-connected-client/actions/workflows/github-code-scanning/codeql/badge.svg?branch=main)](https://github.com/SELAHNHCORG/get-connected-client/actions/workflows/github-code-scanning/codeql?query=branch:main)
[![Zizmor](https://github.com/SELAHNHCORG/get-connected-client/actions/workflows/zizmor.yml/badge.svg?branch=main)](https://docs.zizmor.sh/)
[![Bandit](https://github.com/SELAHNHCORG/get-connected-client/actions/workflows/bandit.yml/badge.svg?branch=main)](https://bandit.readthedocs.io)

A typed Python client, with an optional command line interface, for [Galaxy Digital's](https://www.galaxydigital.com/volunteer-management-software-for-social-service-organizations) [Get
Connected API](https://api.galaxydigital.com/docs/). It provides a typed, synchronous `GalaxyClient` covering
all 66 documented API paths through one namespace per resource
(`users`, `agencies`, `needs`, `events`, `hours`, `responses`, `teams`,
`groups`, `qualifications`, `benchmarks`, `clusters`, `lookups`, `auth`).
The optional `cli` extra adds a `galaxy` command that mirrors it with one
sub-app apiece:

```
config  users  agencies  needs  events  hours  responses  teams  groups
qualifications  benchmarks  clusters  causes  interests  impacts
registration-questions  auth  reports
```

`config` reports the resolved settings and has no library
counterpart; conversely the library's `client.lookups` namespace is split
on the CLI into the `causes`, `interests`, `impacts` and
`registration-questions` sub-apps. `reports` is the other odd one out: it
mirrors no endpoint, aggregating records the API returns into answers it
will not compute for you.

## Installation

The library alone -- `httpx` and `pydantic`, nothing else:

```bash
pip install get-connected-client
```

The `galaxy` command line tool is optional; it lives behind the `cli` extra:

```bash
pip install "get-connected-client[cli]"
```

The `galaxy` entry point is always installed, but without the extra it exits
with a message telling you to install it. The CLI examples below need the
extra.

## Quick Start

Two credentials are involved, and they are not interchangeable:

- the **site API key** (a UUID from your Galaxy Digital site) identifies
  the site when you log in. It cannot authenticate requests -- the API
  answers 401 for it, with or without a `Bearer ` prefix.
- the **session token** returned by logging in is what every request is
  actually authenticated with, as `Authorization: Bearer <token>`. It is a
  JWT and lives about a year.

### CLI

```bash
export GALAXY_API_KEY=YOUR_SITE_KEY          # step 1: the site key

eval "$(galaxy auth login --email you@example.org --export)"   # step 2

galaxy config show               # step 3: both credentials, redacted
galaxy users list --per-page 10
galaxy --json needs get 123
```

`galaxy auth login --export` prints exactly one line --
`export GALAXY_API_TOKEN='<token>'` -- on stdout and nothing else, so
`eval` can adopt it into the current shell. The password is prompted for
on stderr. Without `--export` the command prints a table (the token in
full, wrapped, never truncated), and `--json` gives you the raw token for
scripting:

```bash
GALAXY_API_TOKEN=$(galaxy --json auth login --email you@example.org | jq -r .token)
```

Put `GALAXY_API_KEY` in your shell profile (`~/.bashrc`, `~/.zshrc`, ...)
and re-run the `eval` line whenever the token expires -- nothing is
persisted to disk by the CLI.

`--json` emits raw JSON instead of a formatted table, for scripting. It
is a root option, so it goes before the sub-app name.

### Reports

`galaxy reports` answers questions the API has no endpoint for. The
attendance report ranks a program's volunteers by how many of its sessions
they turned up to, highest first:

```bash
galaxy reports attendance --program "hollywood" --year 2026
```

Attendance comes from hour records (two entries on one day count as one
program attended). Pin exact needs with `--need-id` instead of a title,
narrow by `--status`, and use `--start`/`--end` for a period that is not a
whole calendar year. Reports only read, so `--read-only` never blocks them.

### Library

```python
from get_connected_client import GalaxyClient

# the site key alone gets you exactly one thing: a token
with GalaxyClient(api_key="SITE-KEY") as client:
    client.login("you@example.org", "hunter2")  # adopts the token
    for user in client.users.list(per_page=50):
        print(user.id, user.user_email)

# or start from a token you already have
with GalaxyClient(token="eyJ...") as client:
    need = client.needs.get(123)
    print(need.need_title)
```

`client.login()` stores the returned token on the client and rebuilds its
HTTP transport around it, so every later call is authenticated. Both
credentials can also come from the environment (`GALAXY_API_KEY`,
`GALAXY_API_TOKEN`), in which case `GalaxyClient()` needs no arguments.

## Configuration

The **CLI** resolves settings with this precedence, highest first:

1. **Explicit arguments** -- the CLI flags `--api-key`, `--token`, `--url`
   and `--read-only`.
2. **Environment variables** -- `GALAXY_API_KEY`, `GALAXY_API_TOKEN`,
   `GALAXY_API_URL`, `GALAXY_READ_ONLY`.
3. **Defaults** -- server `us1`, `read_only` off, no credentials.

There is no config file: nothing is written to disk, so a plaintext key or
token never lands in one. `galaxy config show` prints what the chain above
resolved (key and token redacted to their last four characters) and
whether each value came from a flag, the environment, or the default.

### Library behavior

`GalaxyClient` does *not* implement that chain. It takes explicit
arguments and falls back to `GALAXY_API_KEY` and `GALAXY_API_TOKEN` for
the two credentials only. `GALAXY_API_URL` is the CLI's doing, not the
client's, so `base_url` defaults to `us1` no matter what the CLI would
have resolved. (`GALAXY_READ_ONLY` is the one other env var the client
does honor, and only in one direction: it can turn read-only on, never
off.)

```python
from get_connected_client import GalaxyClient

# explicit arguments; base_url accepts the same aliases as --url
GalaxyClient(token="eyJ...", base_url="us2")

# both omitted -> GALAXY_API_TOKEN / GALAXY_API_KEY; the server stays us1
GalaxyClient()
```

Library callers who want the CLI's full resolution can ask for it
explicitly:

```python
from get_connected_client import GalaxyClient
from get_connected_client.config import load_settings

s = load_settings()
client = GalaxyClient(
    api_key=s.api_key, token=s.token, base_url=s.url, read_only=s.read_only
)
```

See the full configuration reference in the documentation for env var
details and server aliases (`us1`/`us2`/`ca`).

## Write Safety

The only Galaxy Digital account available for development and testing of
this project is a production account, so avoiding accidental writes is a
core design constraint, not an afterthought:

- **Read-only modes.** Writes can be blocked outright three ways, and any
  one of them is enough: the `GalaxyClient(read_only=True)` constructor
  flag, the CLI's `--read-only` flag, or the `GALAXY_READ_ONLY`
  environment variable. The guard is
  enforced before any request reaches the network, and a second time as
  an `httpx` request hook as a backstop. Four commands the API models as
  reads are blocked by `--read-only` too, because each one has a real
  side effect: `galaxy auth login` and `galaxy auth authenticate` mint a
  session token or a login link, `galaxy users welcome-email` puts mail
  in someone's inbox, and `galaxy users oneclick` hands out a
  passwordless login link.
- **Confirm prompts.** Every CLI write shows exactly what is about to be
  sent and asks for confirmation before it fires. Pass `--yes`/`-y` to
  skip the prompt in scripts.
- **Opt-in live tests.** The test suite talks only to mocked HTTP by
  default. Two pytest markers exist for exercising the real API and are
  never run in CI or by `just test`:
  - `live` -- read-only smoke tests against production. Requires
    `GALAXY_API_TOKEN` (the site key cannot authenticate) and is run
    explicitly: `uv run pytest -m live`.
  - `live_write` -- writes to production. Requires both
    `GALAXY_API_TOKEN` and an explicit acknowledgment env var:
    ```bash
    GALAXY_LIVE_WRITE_ACK=I-UNDERSTAND-THIS-WRITES-TO-PROD uv run pytest -m live_write
    ```

## Documentation

Full documentation is available at [get-connected-client.readthedocs.io](https://get-connected-client.readthedocs.io).

## Development

```bash
git clone https://github.com/SELAHNHCORG/get-connected-client.git
cd get-connected-client
just setup
just install
just test
```

`just test` runs the mocked-HTTP suite only (the default `pytest` marker
selection excludes `live` and `live_write`). See [Write Safety](#write-safety)
above before ever running the live markers yourself -- they hit a real
production account.

`doc/api.yml` is the vendored copy of Galaxy Digital's published OpenAPI spec
and the source of truth the test suite checks path coverage against. A weekly
GitHub Action diffs it against the live spec and opens an issue labelled
`api-drift` when upstream changes.

## Contributing

Contributions are welcome -- open an issue or pull request on GitHub.
