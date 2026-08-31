# Contributing

Contributions are encouraged! Please use the issue page to submit feature requests or
bug reports. Issues with attached PRs will be given priority and have a much higher
likelihood of acceptance. Please also open an issue and associate it with any submitted
PRs. Before PRs can be merged all added code test coverage must be 100%.

We are actively seeking additional maintainers. If you're interested, please open an
issue or [contact me](https://github.com/bckohan).

## ⚠️ The API is production

The only Galaxy Digital account available for development and testing is a
**production** account. Everything about this project's testing story flows from that:

- Unit tests mock all HTTP with [respx](https://lundberg.github.io/respx/) — they never
  touch the network and are always safe to run.
- Live tests are opt-in markers that are **never run in CI** and must never be run
  casually. `-m live` runs read-only smoke tests (requires `GALAXY_API_TOKEN`);
  `-m live_write` performs reversible writes and additionally requires
  `GALAXY_LIVE_WRITE_ACK=I-UNDERSTAND-THIS-WRITES-TO-PROD`.
- New code paths that write to the API must go through `GalaxyClient.request` (the
  read-only choke point) and, in the CLI, must be gated by `confirm_write`.

## Installation

### Install Just

We provide a platform independent justfile with recipes for all the development tasks.
You should [install just](https://just.systems/man/en/installation.html) if it is not on
your system already.

`get-connected-client` uses [uv](https://docs.astral.sh/uv) for environment, package,
and dependency management. `just setup` will install the necessary build tooling if you
do not already have it:

```sh
just setup <python version>
```

**This will also install prek.** If you wish to submit code that does not pass
pre-commit checks you can disable [prek](https://prek.j178.dev) by running:

```sh
just run prek uninstall
```

### Install the Dev environment

To install all development dependencies run the `install` recipe:

```sh
just install
```

Note that the `galaxy` CLI and its `typer`/`rich` dependencies live in the optional
`cli` extra, so development environments must sync with `--all-extras` — `just install`
does this by default.

## Documentation

`get-connected-client` documentation is generated using
[Sphinx](https://www.sphinx-doc.org) with the [furo](https://github.com/pradyunsg/furo)
theme. The CLI reference is rendered directly from the live typer app with
[sphinxcontrib-typer](https://sphinxcontrib-typer.readthedocs.io/), so it never needs
manual updating. Any new feature PRs must provide updated documentation for the features
added. To build the docs run doc8 to check for formatting issues then run Sphinx:

```sh
just docs  # builds docs
just check-docs  # lint the docs
just check-docs-links  # check for broken links in the docs
```

Run the docs with auto rebuild using:

```sh
just docs-live
```

## Static Analysis

`get-connected-client` uses [ruff](https://docs.astral.sh/ruff/) for Python linting,
header import standardization and code formatting. [mypy](http://mypy-lang.org/) and
[pyright](https://github.com/microsoft/pyright) are used for static type checking.
[bandit](https://bandit.readthedocs.io) and [zizmor](https://docs.zizmor.sh) provide
security analysis of the source and CI workflows respectively. Before any PR is
accepted the following must be run, and static analysis tools should not produce any
errors or warnings. Disabling certain errors or warnings where justified is acceptable:

To fix formatting and linting problems that are fixable run:

```sh
just fix
```

To run all static analysis without automated fixing you can run:

```sh
just check
```

## Running Tests

`get-connected-client` is set up to use [pytest](https://docs.pytest.org) to run unit
tests. All the tests are housed in `tests`. Before a PR is accepted, all tests must be
passing and the code coverage must be at 100%. A small number of exempted error handling
branches are acceptable.

To run the full suite:

```shell
just test
```

To run a single test, or group of tests in a class:

```shell
just test <path_to_tests_file>::ClassName::FunctionName
```

The default run deselects the `live` and `live_write` markers — see
[the API is production](#%EF%B8%8F-the-api-is-production) before ever selecting them
explicitly.

The vendored OpenAPI spec at `doc/api.yml` is the source of truth for API coverage:
tests parse it directly and fail if any documented path is left uncovered. A weekly
[api-drift workflow](.github/workflows/api-drift.yml) compares it against the live
published spec and opens an `api-drift` issue when upstream changes.

### Debugging tests

To debug a test use the `debug-test` recipe:

```shell
just debug-test <path_to_tests_file>::ClassName::FunctionName
```

This will set a breakpoint at the start of the test.

## Versioning

`get-connected-client` uses automated [CalVer](https://calver.org) versioning of the
form `YYYY.M.D` (with a trailing `.serial` for multiple same-day releases). Between
releases, builds are stamped `YYYY.M.D.devN`. `just print-version` reports the version
of the current checkout; the build reads it via the `PACKAGE_VERSION` environment
variable.

## Issuing Releases

Releases are cut from `main` with no version argument — the version is computed from
today's date. The release recipe verifies the working tree, signs and pushes a tag,
which triggers the release workflow (build → TestPyPI → PyPI → GitHub release). You
must have
[git tag signing enabled](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits).

```sh
just release
```

## Just Recipes

Run just with no recipe to see a list of all available commands:

```sh
just
```

```sh
install-uv                   # install the uv package manager
setup python="python"        # setup the venv and pre-commit hooks
install-prek                 # install git pre-commit hooks
install *OPTS="--all-extras" # update and install development dependencies
check-types-mypy *ENV        # run static type checking with mypy
check-types-pyright *ENV     # run static type checking with pyright
check-types *ENV             # run all static type checking
check-types-isolated *ENV    # run all static type checking in an isolated environment
check-package                # run package checks
clean-docs                   # remove doc build artifacts
clean-env                    # remove the virtual environment
clean-git-ignored            # remove all git ignored files
clean                        # remove all non-repository artifacts
build-docs-html              # build html documentation
build-docs                   # build the docs
build VERSION=""             # build docs and package at the current (or given) version
open-docs                    # open the html documentation
docs                         # build and open the documentation
docs-live                    # serve the documentation with auto-reload
check-docs-links             # check documentation links for broken links
check-docs *ENV              # lint the documentation
fetch-refs LIB               # fetch intersphinx references for the given package
check-lint *ENV              # lint the code
check-format *ENV            # check if the code needs formatting
check-readme *ENV            # check that the readme renders
sort-imports *ENV            # sort the python imports
format *ENV                  # format the code and sort imports
format-workflows             # format the github workflow files
lint *ENV                    # sort imports and fix linting issues
fix *ENV                     # fix formatting, linting issues and import sorting
bandit                       # run bandit static security analysis
zizmor                       # run zizmor security analysis of CI
check *ENV                   # run all static checks
check-all *ENV               # run all checks including documentation link checking (slow)
test-all *ENV                # run all tests in an isolated environment
test *TESTS                  # run specific tests (project venv)
debug-test *TESTS            # debug a test
prek                         # run the pre-commit checks
coverage-erase               # erase any coverage data
coverage                     # generate the test coverage report
run +ARGS                    # run the command in the virtual environment
print-version                # print the version: the exact tag at HEAD, else YYYY.M.D.devN
validate_version VERSION     # validate a version tag: PEP 440 normalized and at HEAD
release                      # CalVer-release: verify, sign a tag and push it
```
