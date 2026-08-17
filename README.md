# python-package-template

This is my template for Python packages, based on the tooling and workflow patterns from:

   * [django-enum](https://github.com/django-commons/django-enum)
   * [django-typer](https://github.com/django-commons/django-typer)

It is the framework-agnostic sibling of [django-app-template](https://github.com/bckohan/django-app-template).

The top level goals for this repository organization are to:

   * Test all currently supported versions of Python
   * Support development on Linux/OSX/Windows
   * Have secure release processes
   * Encourage rigorous and linked ([intersphinx](https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html)!) documentation

Key features and design choices, include:

   * Toolchain:
      * [uv](https://docs.astral.sh/uv/)
      * [ruff](https://docs.astral.sh/ruff/)
      * [pytest](https://pytest.org/)
      * [just](https://just.systems/)
      * [prek](https://prek.j178.dev/)
      * [mypy](https://mypy-lang.org/) & [pyright](https://github.com/microsoft/pyright)
      * [Sphinx](https://www.sphinx-doc.org/) & [Furo](https://pradyunsg.me/furo/)
      * [doc8](https://github.com/PyCQA/doc8)
      * [zizmor](https://woodruffw.github.io/zizmor/)
      * [bandit](https://bandit.readthedocs.io/)
      * [ReadTheDocs](https://readthedocs.org)

   * We do not use tox or nox. CI matrix permutations are tested using uv with dependency groups and just recipe shortcuts. For example to run all tests against python 3.13:

      ``just test-all -p 3.13``
   * Release workflow is triggered on tag creation with semver naming patterns - it uses trusted publishing with PyPi.
   * Testing
      * In CI a pip freeze artifact is created for each test run
      * A ``just debug-test <test>`` recipe drops you into the debugger at the start of a test.
   * Configurable options include:
      * Use [OpenSSF Scorecard](https://securityscorecards.dev/)
      * License: MIT, Apache, BSD-3 or None

## Using This Template

### On GitHub (recommended)

**Prerequisite:** Create a [fine-grained PAT](https://github.com/settings/personal-access-tokens/new)
scoped to the new repo with **Contents**, **Pull requests**, and **Workflows** set to
**Read and write**, then add it as a repo secret named **`BOOTSTRAP_TOKEN`**.
GitHub's default `GITHUB_TOKEN` cannot push `.github/workflows/` files, so the bootstrap PR
will fail without this token.

1. Click **"Use this template"** → **"Create a new repository"**
2. Create a [fine-grained PAT](https://github.com/settings/personal-access-tokens/new)
   scoped to the new repo with **Contents**, **Pull requests**, and **Workflows** set to
   **Read and write**. We recommend setting the expiry time to as short as possible because this token will be one-time use by the boostrap workflow.
   ![Multiple Subcommands Example](https://raw.githubusercontent.com/bckohan/python-package-template/main/PAT_perms.png)
2. Add the `BOOTSTRAP_TOKEN` secret (Settings → Secrets and variables → Actions).
3. Create third party secrets:
   * Create a [codecov.io](https://codecov.io) key and set it as the ``CODECOV_TOKEN`` in an environment named ``codecov``
   * (If using) Create a [scorecard PAT](https://github.com/ossf/scorecard-action/blob/main/docs/authentication/fine-grained-auth-token.md) and assign it to ``SCORECARD_TOKEN`` in an environment named ``scorecard``
4. Run the **Bootstrap** workflow manually (Actions → Bootstrap Repository → Run workflow).
   It reads the repo name, owner, and description from GitHub's metadata and opens a PR
   with all template files rendered.
5. Review and merge the PR.

### Locally

```bash
uvx --with pyfiglet --with jinja2-time cookiecutter gh:bckohan/python-package-template
```

## Derived Variables

All values are derived automatically from GitHub repository metadata — no manual input needed:

| Variable | Source |
|----------|--------|
| `project_slug` | repository name |
| `package_name` | repository name with `-` → `_` |
| `description` | repository description |
| `author_name` | owner's GitHub display name |
| `author_email` | owner's public GitHub email (falls back to `@users.noreply.github.com`) |
| `github_owner` | repository owner (org or user) |
| `year` | current year |
