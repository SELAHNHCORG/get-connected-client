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
all 66 documented API paths (users, agencies, needs, events, hours,
responses, teams, groups, qualifications, benchmarks, clusters, lookups,
and auth), plus a `galaxy` command that mirrors it one sub-app per
resource.

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
galaxy needs get 123 --json
```

`--json` emits raw JSON instead of a formatted table, for scripting.

## Configuration

Settings resolve with this precedence, highest first:

1. **Explicit arguments** -- CLI flags (`--api-key`, `--url`,
   `--read-only`) or `GalaxyClient(...)` keyword arguments.
2. **Environment variables** -- `GALAXY_API_KEY`, `GALAXY_API_URL`,
   `GALAXY_READ_ONLY`.
3. **Config file** -- `~/.config/galaxy-digital/config.toml` by default,
   or wherever `GALAXY_CONFIG_FILE` points. Managed with `galaxy config
   set/unset/show/path`; written at mode `0600` since it may hold a
   plaintext API key.
4. **Defaults** -- server `us1`, `read_only` off, no API key.

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
  an `httpx` request hook as a backstop. `galaxy auth login` and `galaxy
  auth authenticate` are blocked by `--read-only` too, since minting a
  session token or login link is a side effect worth gating like any
  other write.
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

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md).
