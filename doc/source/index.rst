get-connected-client
====================

.. |license| image:: https://img.shields.io/badge/License-MIT-blue.svg
   :target: https://opensource.org/licenses/MIT
   :alt: License: MIT

.. |ruff| image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/
   astral-sh/ruff/main/assets/badge/v2.json
   :target: https://github.com/astral-sh/ruff
   :alt: Ruff

.. |pypi-version| image:: https://badge.fury.io/py/get-connected-client.svg
   :target: https://pypi.python.org/pypi/get-connected-client/
   :alt: PyPI version

.. |pypi-pyversions| image:: https://img.shields.io/pypi/pyversions/get-connected-client.svg
   :target: https://pypi.python.org/pypi/get-connected-client/
   :alt: PyPI pyversions

.. |pypi-status| image:: https://img.shields.io/pypi/status/get-connected-client.svg
   :target: https://pypi.python.org/pypi/get-connected-client
   :alt: PyPI status

.. |pypi-types| image:: https://img.shields.io/pypi/types/get-connected-client.svg
   :target: https://pypi.python.org/pypi/get-connected-client
   :alt: PyPI - Types

.. |docs| image:: https://readthedocs.org/projects/get-connected-client/badge/?version=latest
   :target: http://get-connected-client.readthedocs.io/en/latest/
   :alt: Documentation Status

.. |codecov| image:: https://codecov.io/gh/SELAHNHCORG/get-connected-client/branch/main/
   graph/badge.svg?token=0IZOKN2DYL
   :target: https://codecov.io/gh/SELAHNHCORG/get-connected-client
   :alt: Code Cov

.. |tests| image:: https://github.com/SELAHNHCORG/get-connected-client/actions/workflows/
   test.yml/badge.svg?branch=main
   :target: https://github.com/SELAHNHCORG/get-connected-client/actions/workflows/
      test.yml?query=branch:main
   :alt: Test Status

.. |lint| image:: https://github.com/SELAHNHCORG/get-connected-client/actions/workflows/
   lint.yml/badge.svg?branch=main
   :target: https://github.com/SELAHNHCORG/get-connected-client/actions/workflows/
      lint.yml?query=branch:main
   :alt: Lint Status

.. |codeql| image:: https://github.com/SELAHNHCORG/get-connected-client/actions/workflows/
   github-code-scanning/codeql/badge.svg?branch=main
   :target: https://github.com/SELAHNHCORG/get-connected-client/actions/workflows/
      github-code-scanning/codeql?query=branch:main
   :alt: CodeQL

.. |zizmor| image:: https://github.com/SELAHNHCORG/get-connected-client/actions/workflows/
   zizmor.yml/badge.svg?branch=main
   :target: https://docs.zizmor.sh/
   :alt: Zizmor

.. |bandit| image:: https://github.com/SELAHNHCORG/get-connected-client/actions/workflows/
   bandit.yml/badge.svg?branch=main
   :target: https://bandit.readthedocs.io
   :alt: Bandit

|license| |ruff| |pypi-version| |pypi-pyversions| |pypi-status| |pypi-types|
|docs| |codecov| |tests| |lint| |codeql| |zizmor| |bandit|

:pypi:`get-connected-client` is a typed Python client for
`Galaxy Digital's <https://www.galaxydigital.com/>`_
`Get Connected API <https://api.galaxydigital.com/docs/>`_, with an
optional command line interface. It wraps all 66 documented API paths behind a
typed, synchronous :class:`~get_connected_client.client.GalaxyClient` -- the sole
choke point for every request. Installing the optional ``cli`` extra
(``pip install "get-connected-client[cli]"``) adds a ``galaxy`` command with one
sub-app per resource: ``config``, ``users``, ``agencies``, ``needs``, ``events``,
``hours``, ``responses``, ``teams``, ``groups``, ``qualifications``,
``benchmarks``, ``clusters``, ``causes``, ``interests``, ``impacts``,
``registration-questions`` and ``auth``.

The library's namespaces line up with those, minus ``config`` (which
inspects the CLI's resolved environment settings and has no client
counterpart) and with the four lookup sub-apps rolled into a single
``client.lookups``.

Because the only Galaxy Digital account available for development and
testing is a production account, the library and CLI are built around a
write-safety model: writes can be blocked outright (constructor flag,
``--read-only``, or the ``GALAXY_READ_ONLY`` env var), and every CLI write
shows the operator exactly what will change and asks for confirmation
before it fires.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   quickstart
   configuration
   cli
   api
