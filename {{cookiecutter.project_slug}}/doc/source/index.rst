.. include:: ./refs.rst
.. role:: big

{{ "=" * cookiecutter.project_slug|length }}
{{cookiecutter.project_slug}}
{{ "=" * cookiecutter.project_slug|length }}


.. only:: html

{% if cookiecutter.license == "MIT" %}
    .. image:: https://img.shields.io/badge/License-MIT-blue.svg
        :target: https://opensource.org/licenses/MIT
        :alt: MIT License
{%- elif cookiecutter.license == "Apache" %}
    .. image:: https://img.shields.io/badge/License-Apache_2.0-blue.svg
        :target: https://opensource.org/licenses/Apache-2.0
        :alt: Apache 2.0 License
{%- elif cookiecutter.license == "BSD-3" %}
    .. image:: https://img.shields.io/badge/License-BSD_3--Clause-blue.svg
        :target: https://opensource.org/licenses/BSD-3-Clause
        :alt: BSD 3-Clause License
{%- endif %}

    .. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
        :target: https://docs.astral.sh/ruff
        :alt: Ruff

    .. image:: https://badge.fury.io/py/{{cookiecutter.project_slug}}.svg
        :target: https://pypi.python.org/pypi/{{cookiecutter.project_slug}}/
        :alt: PyPI Version

    .. image:: https://img.shields.io/pypi/pyversions/{{cookiecutter.project_slug}}.svg
        :target: https://pypi.python.org/pypi/{{cookiecutter.project_slug}}/
        :alt: Python Versions

    .. image:: https://img.shields.io/pypi/status/{{cookiecutter.project_slug}}.svg
        :target: https://pypi.python.org/pypi/{{cookiecutter.project_slug}}
        :alt: Development Status

    .. image:: https://img.shields.io/pypi/types/{{cookiecutter.project_slug}}.svg
        :target: https://pypi.python.org/pypi/{{cookiecutter.project_slug}}
        :alt: Typed

    .. image:: https://readthedocs.org/projects/{{cookiecutter.project_slug}}/badge/?version=latest
        :target: http://{{cookiecutter.project_slug}}.readthedocs.io/?badge=latest/
        :alt: Documentation Status

    .. image:: https://codecov.io/gh/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}}/branch/main/graph/badge.svg?token=0IZOKN2DYL
        :target: https://codecov.io/gh/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}}
        :alt: Code Coverage

    .. image:: https://github.com/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}}/actions/workflows/test.yml/badge.svg?branch=main
        :target: https://github.com/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}}/actions/workflows/test.yml
        :alt: Test Status

    .. image:: https://github.com/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}}/actions/workflows/lint.yml/badge.svg
        :target: https://github.com/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}}/actions/workflows/lint.yml
        :alt: Lint Status

{%- if cookiecutter.scorecard == "true" %}
    .. image:: https://api.securityscorecards.dev/projects/github.com/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}}/badge
        :target: https://securityscorecards.dev/viewer/?uri=github.com/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}}
        :alt: OSSF Scorecard
{%- endif %}


{{cookiecutter.description}}

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   reference/index
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
