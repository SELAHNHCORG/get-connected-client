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

``--format [table|json]``
    How results are rendered: ``table`` (the default) for a formatted rich
    table, ``json`` for raw JSON -- for scripting. Falls back to
    ``GALAXY_FORMAT``, so a session that always wants JSON can export it
    once instead of repeating the flag. The value is case-insensitive on
    both the flag and the environment variable.

``--json``
    Shorthand for ``--format json``. The two are interchangeable; giving
    both is only an error when they disagree
    (``--json --format table`` is refused rather than silently resolved).

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

.. typer:: get_connected_client.cli:app:config
   :prog: galaxy config
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

There is nothing to set or unset: settings come from the global flags, then
``GALAXY_API_KEY`` / ``GALAXY_API_TOKEN`` / ``GALAXY_API_URL`` /
``GALAXY_READ_ONLY`` / ``GALAXY_FORMAT``, then the defaults. See
:doc:`configuration`.

``auth`` -- credential exchange
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: get_connected_client.cli:app:auth
   :prog: galaxy auth
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

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

.. typer:: get_connected_client.cli:app:users
   :prog: galaxy users
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

``agencies`` -- manage agencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: get_connected_client.cli:app:agencies
   :prog: galaxy agencies
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

``needs`` -- manage needs
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: get_connected_client.cli:app:needs
   :prog: galaxy needs
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

``events`` -- manage events
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: get_connected_client.cli:app:events
   :prog: galaxy events
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

``hours`` -- manage hour records
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: get_connected_client.cli:app:hours
   :prog: galaxy hours
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

``responses`` -- manage responses (need sign-ups)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: get_connected_client.cli:app:responses
   :prog: galaxy responses
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

``teams`` -- manage teams
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: get_connected_client.cli:app:teams
   :prog: galaxy teams
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

``groups`` -- manage groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: get_connected_client.cli:app:groups
   :prog: galaxy groups
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

``qualifications`` -- manage qualifications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: get_connected_client.cli:app:qualifications
   :prog: galaxy qualifications
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

``benchmarks`` -- manage benchmarks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: get_connected_client.cli:app:benchmarks
   :prog: galaxy benchmarks
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

``clusters``, ``causes``, ``interests``, ``impacts``, ``registration-questions``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Small, mostly read-only lookup endpoints:

.. typer:: get_connected_client.cli:app:clusters
   :prog: galaxy clusters
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

.. typer:: get_connected_client.cli:app:causes
   :prog: galaxy causes
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

.. typer:: get_connected_client.cli:app:interests
   :prog: galaxy interests
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

.. typer:: get_connected_client.cli:app:impacts
   :prog: galaxy impacts
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

.. typer:: get_connected_client.cli:app:registration-questions
   :prog: galaxy registration-questions
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

``reports`` -- aggregate answers the API will not compute
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. typer:: get_connected_client.cli:app:reports
   :prog: galaxy reports
   :show-nested:
   :make-sections:
   :preferred: svg
   :width: 100
   :convert-png: latex

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

.. _cli-updates-are-merged:

Updates are merged
------------------

The API's ``PUT`` replaces the whole record: every field its request
schema marks required must be present, whatever the record already holds.
Sending only ``--data '{"user_notes": "..."}'`` on a user would be
answered with a 422 naming ``user_email``, ``user_fname``, ``user_lname``
and ``user_status`` as missing.

So every ``update`` command first fetches the record, converts it into a
request body, lays the fields you named over it, and sends the
result. The confirmation prompt shows only what changes:

.. code-block:: text

   $ galaxy users update 8821 --data '{"user_notes": "Prefers mornings."}'
   About to write to the API: PUT /users/8821 (merged over the current record)
   field        current   new
   user_notes   (none)    Prefers mornings.
   Proceed? [y/N]:

Long values are folded across as many lines as they take, never cut
short: you are approving exactly what will be sent.

If the merged body still lacks a field the API marks required -- because
the record did not carry it and you did not name it -- a warning naming
those fields is printed to stderr before the prompt, and under ``--yes``
too. The write is not blocked: the API is the authority, and its answer
is shown as usual.

If nothing you named differs from what the record already holds, nothing
is written: the command says so on stderr and exits 0. Naming no fields
at all does the same, without even fetching. Under ``--format json``
both cases print ``{"changes": []}`` on stdout, so a pipe still gets
parseable output.

``--replace`` skips the fetch and the merge and sends exactly the fields
you gave as the whole body. It still warns about required fields that
body lacks, and the API rejects a body missing any. Use it when you
already hold a complete body, or when the merge gets in your way.

``--data`` may not set ``id``: the record is chosen by the ID argument.

What the merge cannot do
~~~~~~~~~~~~~~~~~~~~~~~~

The API's read and write shapes disagree in a few places, so some fields
cannot be carried from the fetched record into the body. Each is
documented on the resource class in the :doc:`API reference <api>`; in
brief:

* ``groups update`` still needs ``ug_type`` (``gc`` or ``slm``) in
  ``--data``: the API requires it on every write and never returns it,
  so a merged update without it is answered with a 422.
* ``needs update`` never carries the record's shifts -- the read shape
  does not match the write shape, and resending them risks duplicating
  rows that ``needs add-shift`` / ``needs remove-shift`` manage.
  ``virtual_need``, ``need_hours_description``, ``event_id``,
  ``interests`` and ``attributes`` exist only on the write side and are
  sent absent unless you name them. ``agency_id`` is derived from the
  fetched need's ``agency``; if the record has none, name it yourself.
* ``agencies update`` never carries ``agency_contacts`` (a list of
  strings on read, a single string on write, with no documented
  relationship between the two), so a merged update may clear it. Pass
  ``agency_contacts`` explicitly to set or preserve it.
* ``events update`` sends ``event_capacity``, ``event_contact``,
  ``event_country`` and ``event_phone`` absent unless you name them:
  they exist only on the write side. ``event_area`` and
  ``event_area_id`` are carried from the record when it has them, and
  must be named when it does not.
* ``hours update`` cannot carry ``response_id``, which ``GET`` never
  returns, so a merged update on an hour logged against a need may
  detach it from its response. Find the id among that need's responses
  (``galaxy needs responses <need-id>``, matched on the volunteer) and
  pass it with ``--response-id``.
* ``responses update`` derives ``schedule_ids`` from the record's single
  ``shift``. A response to a need with no shifts therefore cannot be
  merged -- there is no id to supply and the API answers 422 -- and a
  response covering several shifts must name ``schedule_ids`` itself.
  Answers to custom questions cannot be preserved either: the record's
  ``answers`` are a different shape from the write side's
  ``questions``, so pass ``questions`` if the response has any.
  ``response_phone`` and ``response_address`` are returned by ``GET``
  but appear nowhere in the request schema, so the API offers no way to
  update them at all. ``response_date_added`` is re-sent when the record
  carries it, since omitting it resets the sign-up date to now.
