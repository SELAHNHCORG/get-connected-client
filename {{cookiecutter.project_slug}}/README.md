# {{cookiecutter.project_slug}}

{%- if cookiecutter.license == "MIT" %}
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
{%- elif cookiecutter.license == "Apache" %}
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
{%- elif cookiecutter.license == "BSD-3" %}
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
{%- endif %}
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PyPI version](https://badge.fury.io/py/{{cookiecutter.project_slug}}.svg)](https://pypi.python.org/pypi/{{cookiecutter.project_slug}}/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/{{cookiecutter.project_slug}}.svg)](https://pypi.python.org/pypi/{{cookiecutter.project_slug}}/)
[![PyPI status](https://img.shields.io/pypi/status/{{cookiecutter.project_slug}}.svg)](https://pypi.python.org/pypi/{{cookiecutter.project_slug}})
[![Documentation Status](https://readthedocs.org/projects/{{cookiecutter.project_slug}}/badge/?version=latest)](http://{{cookiecutter.project_slug}}.readthedocs.io/?badge=latest/)
[![Code Cov](https://codecov.io/gh/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}}/branch/main/graph/badge.svg?token=0IZOKN2DYL)](https://codecov.io/gh/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}})
[![Test Status](https://github.com/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}}/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}}/actions/workflows/test.yml?query=branch:main)
[![Lint Status](https://github.com/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}}/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}}/actions/workflows/lint.yml?query=branch:main)
{%- if cookiecutter.scorecard == "true" %}
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}}/badge)](https://securityscorecards.dev/viewer/?uri=github.com/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}})
{%- endif %}

{{cookiecutter.description}}

## Installation

```bash
pip install {{cookiecutter.project_slug}}
```

## Quick Start

TODO: Add quick start example.

## Documentation

Full documentation is available at [{{cookiecutter.project_slug}}.readthedocs.io](https://{{cookiecutter.project_slug}}.readthedocs.io).

## Development

```bash
git clone https://github.com/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}}.git
cd {{cookiecutter.project_slug}}
just setup
just install
just test
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md).
