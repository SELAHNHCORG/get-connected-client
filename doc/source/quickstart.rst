Quickstart
==========

Install
-------

.. code-block:: bash

   pip install galaxy-digital-cli

This installs both the ``galaxy_digital_cli`` library and the ``galaxy``
command line tool.

Library
-------

:class:`~galaxy_digital_cli.client.GalaxyClient` is the entry point. It
holds one namespace per resource (``users``, ``agencies``, ``needs``,
``events``, ``hours``, ``responses``, ``teams``, ``groups``,
``qualifications``, ``benchmarks``, ``clusters``, ``lookups``, ``auth``) and
funnels every request through a single method, so retries, error mapping,
and the read-only guard all live in one place.

Use it as a context manager so the underlying connection is always closed:

.. code-block:: python

   from galaxy_digital_cli import GalaxyClient

   with GalaxyClient(api_key="...") as client:
       # list() returns an iterator that pages through the endpoint
       # transparently -- rows stream as they arrive.
       for user in client.users.list(per_page=50):
           print(user.id, user.user_email)

       need = client.needs.get(123)
       print(need.need_title)

The API key can also be supplied via the ``GALAXY_API_KEY`` environment
variable, in which case the constructor needs nothing:

.. code-block:: python

   with GalaxyClient() as client:
       agency = client.agencies.get(1)

CLI
---

The ``galaxy`` command mirrors the library: one sub-app per resource, with
``list``, ``get``, ``create``, ``update`` and ``delete`` where the endpoint
supports them, plus resource-specific sub-commands (``users agencies``,
``needs add-shift``, and so on). It adds a ``config`` sub-app that reports
the resolved settings, and splits the library's ``lookups`` namespace into
the ``causes``, ``interests``, ``impacts`` and ``registration-questions``
sub-apps. See :doc:`cli` for the full command tree.

Credentials come from the environment -- put these in your shell profile
(``~/.bashrc``, ``~/.zshrc``, ...) to keep them across sessions:

.. code-block:: bash

   export GALAXY_API_KEY=YOUR_API_KEY
   export GALAXY_API_URL=us1        # us1 (default), us2, or ca

   galaxy config show               # check what got resolved, key redacted

Then use it:

.. code-block:: bash

   galaxy users list --per-page 10
   galaxy --json needs get 123
   galaxy needs create --title "Beach Cleanup" --agency-id 42

``--json`` emits raw JSON instead of a formatted table, which is convenient
for scripting or piping into ``jq``. Like every global option it belongs to
the root command, so it goes *before* the sub-app name.

Write safety, in brief
-----------------------

Every write command (``create``, ``update``, ``delete``, and a handful of
other endpoints that mutate state) prints exactly what it is about to send
and asks for confirmation before touching the network:

.. code-block:: text

   $ galaxy needs delete 123
   About to write to the API: DELETE /needs/123
   Proceed? [y/N]:

Pass ``--yes``/``-y`` to skip the prompt in scripts, or ``--read-only`` (or
``GALAXY_READ_ONLY=1``) to block writes outright, at the client or CLI
level. See :doc:`configuration` for the full write-safety model.
