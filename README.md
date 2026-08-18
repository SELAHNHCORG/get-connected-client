# galaxy-digital-cli
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code Cov](https://codecov.io/gh/SELAHNHCORG/galaxy-digital-cli/branch/main/graph/badge.svg?token=0IZOKN2DYL)](https://codecov.io/gh/SELAHNHCORG/galaxy-digital-cli)
[![Test Status](https://github.com/SELAHNHCORG/galaxy-digital-cli/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/SELAHNHCORG/galaxy-digital-cli/actions/workflows/test.yml?query=branch:main)
[![Lint Status](https://github.com/SELAHNHCORG/galaxy-digital-cli/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/SELAHNHCORG/galaxy-digital-cli/actions/workflows/lint.yml?query=branch:main)
[![CodeQL](https://github.com/SELAHNHCORG/galaxy-digital-cli/actions/workflows/github-code-scanning/codeql/badge.svg?branch=main)](https://github.com/SELAHNHCORG/galaxy-digital-cli/actions/workflows/github-code-scanning/codeql?query=branch:main)
[![Zizmor](https://github.com/SELAHNHCORG/galaxy-digital-cli/actions/workflows/zizmor.yml/badge.svg?branch=main)](https://docs.zizmor.sh/)
[![Bandit](https://github.com/SELAHNHCORG/galaxy-digital-cli/actions/workflows/bandit.yml/badge.svg?branch=main)](https://bandit.readthedocs.io)

A Python library and command line interface to Galaxy Digital's Get
Connected API. It provides a typed, synchronous `GalaxyClient` covering
all 66 documented API paths through one namespace per resource
(`users`, `agencies`, `needs`, `events`, `hours`, `responses`, `teams`,
`groups`, `qualifications`, `benchmarks`, `clusters`, `lookups`, `auth`),
plus a `galaxy` command that mirrors it with one sub-app apiece:

```
config  users  agencies  needs  events  hours  responses  teams  groups
qualifications  benchmarks  clusters  causes  interests  impacts
registration-questions  auth
```

`config` manages the persisted settings file and has no library
counterpart; conversely the library's `client.lookups` namespace is split
on the CLI into the `causes`, `interests`, `impacts` and
`registration-questions` sub-apps.

## Installation

```bash
pip install galaxy-digital-cli
```

## Quick Start

### Library

```python
from galaxy_digital_cli import GalaxyClient

with GalaxyClient(api_key="...") as client:
    for user in client.users.list(per_page=50):
        print(user.id, user.user_email)

    need = client.needs.get(123)
    print(need.need_title)
```

The API key can also come from the `GALAXY_API_KEY` environment variable,
in which case `GalaxyClient()` needs no arguments.

### CLI

```bash
galaxy config set api_key YOUR_API_KEY
galaxy config set url us1        # us1 (default), us2, or ca

galaxy users list --per-page 10
galaxy --json needs get 123
```

`--json` emits raw JSON instead of a formatted table, for scripting. It
is a root option, so it goes before the sub-app name.

## Configuration

The **CLI** resolves settings with this precedence, highest first:

1. **Explicit arguments** -- the CLI flags `--api-key`, `--url` and
   `--read-only`.
2. **Environment variables** -- `GALAXY_API_KEY`, `GALAXY_API_URL`,
   `GALAXY_READ_ONLY`.
3. **Config file** -- `~/.config/galaxy-digital/config.toml` by default,
   or wherever `GALAXY_CONFIG_FILE` points. Managed with `galaxy config
   set/unset/show/path`; written at mode `0600` since it may hold a
   plaintext API key.
4. **Defaults** -- server `us1`, `read_only` off, no API key.

### Library behavior

`GalaxyClient` does *not* implement that chain. It takes explicit
arguments and falls back to `GALAXY_API_KEY` for the key only.
`GALAXY_API_URL` and the config file are the CLI's doing, not the
client's, so `base_url` defaults to `us1` no matter what the CLI would
have resolved. (`GALAXY_READ_ONLY` is the one env var the client does
honor, and only in one direction: it can turn read-only on, never off.)

```python
from galaxy_digital_cli import GalaxyClient

# explicit arguments; base_url accepts the same aliases as --url
GalaxyClient(api_key="...", base_url="us2")

# api_key omitted -> GALAXY_API_KEY; the server stays us1
GalaxyClient()
```

Library callers who want the CLI's full resolution can ask for it
explicitly:

```python
from galaxy_digital_cli import GalaxyClient
from galaxy_digital_cli.config import load_settings

s = load_settings()
client = GalaxyClient(api_key=s.api_key, base_url=s.url, read_only=s.read_only)
```

See the full configuration reference in the documentation for env var
details, server aliases (`us1`/`us2`/`ca`), and the config file schema.

## Write Safety

The only Galaxy Digital account available for development and testing of
this project is a production account, so avoiding accidental writes is a
core design constraint, not an afterthought:

- **Read-only modes.** Writes can be blocked outright three ways, and any
  one of them is enough: the `GalaxyClient(read_only=True)` constructor
  flag, the CLI's `--read-only` flag (or `galaxy config set read_only
  true`), or the `GALAXY_READ_ONLY` environment variable. The guard is
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
    `GALAXY_API_KEY` and is run explicitly: `uv run pytest -m live`.
  - `live_write` -- writes to production. Requires both
    `GALAXY_API_KEY` and an explicit acknowledgment env var:
    ```bash
    GALAXY_LIVE_WRITE_ACK=I-UNDERSTAND-THIS-WRITES-TO-PROD uv run pytest -m live_write
    ```

## Documentation

Full documentation is available at [galaxy-digital-cli.readthedocs.io](https://galaxy-digital-cli.readthedocs.io).

## Development

```bash
git clone https://github.com/SELAHNHCORG/galaxy-digital-cli.git
cd galaxy-digital-cli
just setup
just install
just test
```

`just test` runs the mocked-HTTP suite only (the default `pytest` marker
selection excludes `live` and `live_write`). See [Write Safety](#write-safety)
above before ever running the live markers yourself -- they hit a real
production account.

## Contributing

Contributions are welcome -- open an issue or pull request on GitHub.
