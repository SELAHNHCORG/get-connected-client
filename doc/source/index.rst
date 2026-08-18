galaxy-digital-cli
===================

**galaxy-digital-cli** is a Python library and command line interface for
`Galaxy Digital's Get Connected API <https://www.galaxydigital.com/>`_. It
wraps all 66 documented API paths behind a typed, synchronous
:class:`~galaxy_digital_cli.client.GalaxyClient` -- the sole choke point for
every request -- and a ``galaxy`` command with one sub-app per resource
(users, agencies, needs, events, hours, responses, teams, groups,
qualifications, benchmarks, clusters, lookups, and auth).

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
