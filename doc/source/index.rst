get-connected-client
====================

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
