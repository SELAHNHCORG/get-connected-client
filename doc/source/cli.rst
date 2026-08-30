Command Line Interface
=======================

The ``galaxy`` command has one sub-app per resource. Run ``galaxy --help``
or ``galaxy <resource> --help`` for the full, current option list for any
command -- this page is an index, not a replacement for ``--help``. The
command reference below is rendered directly from the live application with
`sphinxcontrib-typer <https://sphinxcontrib-typer.readthedocs.io/>`_, so it
can never drift out of sync with the actual CLI.

Global options
--------------

These apply to every sub-command and must be given before the sub-app name
(e.g. ``galaxy --json needs list``):

``--api-key TEXT``
    The site API key, used to log in. Falls back to ``GALAXY_API_KEY``. It
    does not authenticate requests on its own -- see :doc:`configuration`.

``--token TEXT``
    The session token from ``galaxy auth login``, sent as
    ``Authorization: Bearer <token>``. Falls back to ``GALAXY_API_TOKEN``.

``--url TEXT``
    Server URL or alias (``us1``, ``us2``, ``ca``). Falls back to
    ``GALAXY_API_URL``.

``--read-only``
    Block all writes for this invocation. See :doc:`configuration`.

``--json``
    Emit raw JSON instead of a formatted table -- for scripting.

``--yes`` / ``-y``
    Skip the "are you sure?" prompt shown before every write.

``--debug``
    Show full tracebacks instead of a one-line error message.

``--version``
    Print the installed version and exit.

Command tree
------------

``config`` -- inspect the resolved configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: galaxy_digital_cli.cli:app:config
   :prog: galaxy config
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

There is nothing to set or unset: settings come from the global flags, then
``GALAXY_API_KEY`` / ``GALAXY_API_TOKEN`` / ``GALAXY_API_URL`` /
``GALAXY_READ_ONLY``, then the defaults. See :doc:`configuration`.

``auth`` -- credential exchange
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: galaxy_digital_cli.cli:app:auth
   :prog: galaxy auth
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

``login`` is where every session starts, since the site key cannot
authenticate requests by itself.

``--export`` puts one shell-eval'able line on stdout and nothing else, so
the token can be adopted by the current shell without ever being written to
a file:

.. code-block:: bash

   eval "$(galaxy auth login --email you@example.org --export)"

Every other message, the password prompt included, goes to stderr -- which
is also why the password is always collected via a hidden prompt unless
``--password`` is given explicitly.

Without ``--export`` the token is printed in a table, wrapped in full
rather than truncated, and ``--json`` emits the whole login record for
scripting.

Both commands are blocked by ``--read-only`` -- see :doc:`configuration`.

``users`` -- manage users
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: galaxy_digital_cli.cli:app:users
   :prog: galaxy users
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

``agencies`` -- manage agencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: galaxy_digital_cli.cli:app:agencies
   :prog: galaxy agencies
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

``needs`` -- manage needs
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: galaxy_digital_cli.cli:app:needs
   :prog: galaxy needs
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

``events`` -- manage events
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: galaxy_digital_cli.cli:app:events
   :prog: galaxy events
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

``hours`` -- manage hour records
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: galaxy_digital_cli.cli:app:hours
   :prog: galaxy hours
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

``responses`` -- manage responses (need sign-ups)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: galaxy_digital_cli.cli:app:responses
   :prog: galaxy responses
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

``teams`` -- manage teams
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: galaxy_digital_cli.cli:app:teams
   :prog: galaxy teams
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

``groups`` -- manage groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: galaxy_digital_cli.cli:app:groups
   :prog: galaxy groups
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

``qualifications`` -- manage qualifications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: galaxy_digital_cli.cli:app:qualifications
   :prog: galaxy qualifications
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

``benchmarks`` -- manage benchmarks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: galaxy_digital_cli.cli:app:benchmarks
   :prog: galaxy benchmarks
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

``clusters``, ``causes``, ``interests``, ``impacts``, ``registration-questions``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Small, mostly read-only lookup endpoints:

.. typer:: galaxy_digital_cli.cli:app:clusters
   :prog: galaxy clusters
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

.. typer:: galaxy_digital_cli.cli:app:causes
   :prog: galaxy causes
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

.. typer:: galaxy_digital_cli.cli:app:interests
   :prog: galaxy interests
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

.. typer:: galaxy_digital_cli.cli:app:impacts
   :prog: galaxy impacts
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

.. typer:: galaxy_digital_cli.cli:app:registration-questions
   :prog: galaxy registration-questions
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

``reports`` -- aggregate answers the API will not compute
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: galaxy_digital_cli.cli:app:reports
   :prog: galaxy reports
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100

Every command here only reads, so none of them prompts and all of them work
under ``--read-only``.

``attendance`` takes attendance from hour records: a volunteer counts as
having attended on every distinct date they logged time against the matched
needs, so two entries on one day are one program attended. The table adds a
1-based ``rank``, sorted by programs attended, then total hours, then name.

``--program`` matches needs whose title contains the given text,
case-insensitively: the ``/needs`` endpoint's own ``need_title`` filter is
tried first, and the full need list (inactive included) is scanned as a
fallback when that returns nothing. ``--need-id`` counts a need id exactly,
skipping title resolution, and may be combined with ``--program``; at least
one of the two is required.

``--full-scan`` trades completeness for speed: ``/hours`` has no need, user
or attendance-date filter, so the report pages through every hour record and
narrows client-side. By default a ``--start`` bound also sends
``since_created``, which skips the pages of hours logged before the period
and makes that scan far shorter -- but hours logged *before* the date they
were served would then be missed, so pass ``--full-scan`` when the report
must be exhaustive.

With ``--json`` the output is a single object with a ``needs`` key (what the
program name matched) and a ``rows`` key (the ranking), because which needs
were counted is half the answer.

.. code-block:: bash

   galaxy reports attendance --program "hollywood" --year 2026

Soft deletes
------------

Where the reference above says "a soft delete", the API marks the record
inactive rather than removing it, so it may reappear when listing with
``--show-inactive`` (where the endpoint supports that filter). That is what
the spec documents for the ``delete`` on ``users``, ``agencies``, ``needs``,
``events``, ``hours``, ``responses``, ``teams``, ``groups``,
``qualifications`` and ``benchmarks``. It says nothing of the sort about
``clusters delete`` or about the ``remove-*``/``detach`` sub-commands, so do
not assume those are recoverable. Deleting an event is also only *mostly*
soft: the spec warns it permanently deletes that event's RSVPs.

Free-form fields with ``--data``
----------------------------------

Most ``create`` and ``update`` commands expose the common fields
(``--title``, ``--name``, and so on) as named options, plus a catch-all
``--data`` option that takes a JSON object of any further ``*_*`` fields the
endpoint accepts. Keys in ``--data`` win over the named options when both
set the same field.

``clusters create`` is the exception: the endpoint takes a name and nothing
else, so it offers ``--name`` alone.
