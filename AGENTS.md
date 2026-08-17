# AGENTS.md

## What This Repo Is

A [cookiecutter](https://cookiecutter.readthedocs.io/) GitHub template for bootstrapping new Python package repositories. It is the framework-agnostic sibling of [django-app-template](https://github.com/bckohan/django-app-template) and shares its tooling and workflow patterns, modeled after [django-enum](https://github.com/django-commons/django-enum) and [django-typer](https://github.com/django-commons/django-typer).

When a new repo is created from this template, `.github/workflows/bootstrap.yml` is triggered manually via workflow_dispatch (Actions → Bootstrap Repository → Run workflow). It derives all values from the GitHub API, renders the cookiecutter template in-place, and opens a PR.

**Bootstrap requires a `BOOTSTRAP_TOKEN` repo secret** — a fine-grained PAT scoped to the repo with **Contents**, **Pull requests**, and **Workflows** read/write permissions. `GITHUB_TOKEN` cannot push `.github/workflows/` files (a hard GitHub restriction, not fixable via the `permissions` block). The workflow falls back to `github.token` if the secret is absent, which will fail for workflow files.

## Repo Structure

- `cookiecutter.json` — template variables and `_copy_without_render` list
- `.github/workflows/bootstrap.yml` — one-shot bootstrap workflow
- `{{cookiecutter.project_slug}}/` — cookiecutter template directory

Everything inside `{{cookiecutter.project_slug}}/` is rendered by cookiecutter; the outer repo is the template scaffolding itself.

## Jinja2 Conflict Rules

**Workflow `.yml` files** are listed in `_copy_without_render` in `cookiecutter.json` so they are copied verbatim — this preserves `${{ }}` GitHub Actions syntax without Jinja2 trying to expand it.

**`justfile`** uses this workaround at the top:
```
{%- set lb = '{{' -%}
{%- set rb = '}}' -%}
```
All just `{{ VAR }}` syntax is written as `{{ lb }}VAR{{ rb }}`.

When adding new files to the template that use `{{ }}` syntax (just recipes, shell scripts, etc.), apply the same workarounds or add the file to `_copy_without_render`.

## Auto-Derived Variables

The bootstrap workflow derives these from GitHub — do not prompt for them:
- `project_slug` ← repository name
- `package_name` ← repo name with `-` → `_`
- `github_owner` ← `github.repository_owner`
- `author_name` ← GitHub API `/users/$owner` (fallback: login)
- `author_email` ← GitHub API (fallback: `owner@users.noreply.github.com`)
- `year` ← `date +%Y`

## Testing the Template

Smoke test — renders using default `cookiecutter.json` values:
```bash
rm -rf /tmp/cc-test && uvx --with pyfiglet cookiecutter . --no-input --output-dir /tmp/cc-test
```
Output lands at `/tmp/cc-test/my-python-package/`.

## Template Project Tooling (inside `{{cookiecutter.project_slug}}/`)

The generated project uses `just` as a task runner, `uv` for dependency management, and `hatchling` as the build backend.

### Setup
```bash
just setup        # create venv + install pre-commit hooks
just install      # install all dev dependencies via uv
```

### Tests
```bash
just test                     # run tests (project venv, fast)
just test-all                 # run all tests in an isolated environment
just test-all -p 3.13         # run all tests against python 3.13
just test tests/test_foo.py   # run a specific file
just coverage                 # generate coverage report
```

### Linting / Formatting
```bash
just fix          # auto-fix lint + format (ruff)
just check        # run all static checks without modifying files
just prek         # run pre-commit hooks
```

### Type Checking
```bash
just check-types  # runs both mypy and pyright
```

### Docs
```bash
just docs         # build Sphinx HTML and open in browser
just docs-live    # live-reload dev server
just check-docs   # lint docs with doc8
```

## Test Strategy

CI tests the full matrix of supported Python versions on Linux, plus the oldest and newest Python on Windows and macOS. Lower dependency bounds are tested with `uv`'s `--resolution lowest-direct` on the oldest supported Python; all other runs use the highest resolution.

## Expected LSP Noise

`just-lsp`, Pylance, and cSpell report false positives on template files because they parse Jinja2 syntax as real source code. This is harmless.
