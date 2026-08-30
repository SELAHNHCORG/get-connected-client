Quickstart
==========

Install
-------

.. code-block:: bash

   pip install get-connected-client

That is the ``get_connected_client`` library on its own -- ``httpx`` and
``pydantic``, nothing else. The ``galaxy`` command line tool is optional and
ships behind the ``cli`` extra:

.. code-block:: bash

   pip install "get-connected-client[cli]"

The ``galaxy`` entry point is always installed, but without the extra it exits
with a message telling you to install it. Every CLI example below needs the
extra.

Two credentials
---------------

Authentication is a two-step affair, and the two credentials are not
interchangeable:

``GALAXY_API_KEY`` -- the **site key**
    A UUID issued by your Galaxy Digital site. It does *not* authenticate
    requests: the API answers 401 for it, raw or ``Bearer``-prefixed. Its
    one job is to identify the site in the body of a login.

``GALAXY_API_TOKEN`` -- the **session token**
    What logging in returns, and the only thing that authenticates a
    request -- sent as ``Authorization: Bearer <token>``. It is a JWT with
    a lifetime of roughly a year, so this is a rare chore, not a per-run
    one.

CLI
---

The ``galaxy`` command mirrors the library: one sub-app per resource, with
``list``, ``get``, ``create``, ``update`` and ``delete`` where the endpoint
supports them, plus resource-specific sub-commands (``users agencies``,
``needs add-shift``, and so on). It adds a ``config`` sub-app that reports
the resolved settings, and splits the library's ``lookups`` namespace into
the ``causes``, ``interests``, ``impacts`` and ``registration-questions``
sub-apps. See :doc:`cli` for the full command tree.

**Step 1 -- export the site key.** Put this in your shell profile
(``~/.bashrc``, ``~/.zshrc``, ...) so it survives across sessions:

.. code-block:: bash

   export GALAXY_API_KEY=YOUR_SITE_KEY
   export GALAXY_API_URL=us1        # optional: us1 (default), us2, or ca

**Step 2 -- log in and adopt the token.** ``--export`` prints exactly one
line on stdout, ``export GALAXY_API_TOKEN='<token>'``, and nothing else, so
``eval`` can pull it straight into the current shell. The password is
prompted for on stderr, which is what keeps stdout clean:

.. code-block:: bash

   eval "$(galaxy auth login --email you@example.org --export)"

**Step 3 -- use the CLI.**

.. code-block:: bash

   galaxy config show               # both credentials, redacted
   galaxy users list --per-page 10
   galaxy --json needs get 123
   galaxy needs create --title "Beach Cleanup" --agency-id 42

Repeat step 2 when the token expires (about a year) or whenever you want a
fresh one. Nothing is persisted to disk by the CLI, so the token lives only
in your environment.

Without ``--export``, ``galaxy auth login`` prints a table with the token in
full -- wrapped across lines, never truncated -- so it can be copied by
hand. For scripting, ``--json`` gives you the raw record:

.. code-block:: bash

   GALAXY_API_TOKEN=$(galaxy --json auth login --email you@example.org | jq -r .token)

``--json`` emits raw JSON instead of a formatted table, which is convenient
for scripting or piping into ``jq``. Like every global option it belongs to
the root command, so it goes *before* the sub-app name.

Library
-------

:class:`~get_connected_client.client.GalaxyClient` is the entry point. It
holds one namespace per resource (``users``, ``agencies``, ``needs``,
``events``, ``hours``, ``responses``, ``teams``, ``groups``,
``qualifications``, ``benchmarks``, ``clusters``, ``lookups``, ``auth``) and
funnels every request through a single method, so retries, error mapping,
and the read-only guard all live in one place.

Use it as a context manager so the underlying connection is always closed:

.. code-block:: python

   from get_connected_client import GalaxyClient

   # the site key alone gets you exactly one thing: a token
   with GalaxyClient(api_key="SITE-KEY") as client:
       client.login("you@example.org", "hunter2")

       # list() returns an iterator that pages through the endpoint
       # transparently -- rows stream as they arrive.
       for user in client.users.list(per_page=50):
           print(user.id, user.user_email)

:meth:`~get_connected_client.client.GalaxyClient.login` stores the token on
the client and rebuilds its HTTP transport around it, so every later call
is authenticated. A token you already have can be handed to the constructor
instead:

.. code-block:: python

   with GalaxyClient(token="eyJ...") as client:
       need = client.needs.get(123)
       print(need.need_title)

Both credentials can equally come from ``GALAXY_API_KEY`` and
``GALAXY_API_TOKEN``, in which case the constructor needs nothing:

.. code-block:: python

   with GalaxyClient() as client:
       agency = client.agencies.get(1)

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
