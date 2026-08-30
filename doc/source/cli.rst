Command Line Interface
=======================

The ``galaxy`` command has one sub-app per resource. Run ``galaxy --help``
or ``galaxy <resource> --help`` for the full, current option list for any
command -- this page is an index, not a replacement for ``--help``.

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

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Command
     - Description
   * - ``show``
     - Show the resolved ``api_key`` and ``token`` (both redacted), ``url``
       and ``read_only``, plus whether each came from a flag, the
       environment, or the default.

There is nothing to set or unset: settings come from the global flags, then
``GALAXY_API_KEY`` / ``GALAXY_API_TOKEN`` / ``GALAXY_API_URL`` /
``GALAXY_READ_ONLY``, then the defaults. See :doc:`configuration`.

``auth`` -- credential exchange
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Command
     - Description
   * - ``login``
     - Exchange the site key, an email and a password for a session token.
   * - ``authenticate``
     - Verify credentials and mint a one-click login link.

``login`` is where every session starts, since the site key cannot
authenticate requests by itself. Its options:

``--email TEXT``
    The account email address (required).

``--password TEXT``
    The account password. Omit it and the command prompts, hidden, on
    stderr.

``--key TEXT``
    The site key for the login body. Defaults to the resolved
    ``--api-key`` / ``GALAXY_API_KEY``; ``--key`` alone is enough to log in
    even with no ``GALAXY_API_KEY`` set. The command errors out only if
    neither is available.

``--export``
    Print exactly one line on stdout --
    ``export GALAXY_API_TOKEN='<token>'`` -- and nothing else, so the token
    can be adopted by the current shell:

    .. code-block:: bash

       eval "$(galaxy auth login --email you@example.org --export)"

    Every other message, the password prompt included, goes to stderr.

Without ``--export`` the token is printed in a table, wrapped in full
rather than truncated, and ``--json`` emits the whole login record for
scripting.

Both commands are blocked by ``--read-only`` -- see :doc:`configuration`.
Passwords are always collected via a hidden prompt unless ``--password`` is
given explicitly.

``users`` -- manage users
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Command
     - Description
   * - ``list``
     - List users, paging through every match.
   * - ``get ID``
     - Show one user.
   * - ``create``
     - Create a user.
   * - ``update ID``
     - Update a user, sending only the fields you name.
   * - ``delete ID``
     - Delete a user (soft delete).
   * - ``agencies ID``
     - List the agencies a user has fanned.
   * - ``add-agency ID AGENCY_ID``
     - Fan an agency on a user's behalf.
   * - ``remove-agency ID AGENCY_ID``
     - Drop a user's fan relationship with an agency.
   * - ``benchmarks ID``
     - List the benchmarks a user has earned.
   * - ``remove-benchmark ID BENCHMARK_ID``
     - Take a benchmark away from a user.
   * - ``causes ID``
     - List a user's causes.
   * - ``add-cause ID CAUSE_ID``
     - Assign a cause to a user.
   * - ``remove-cause ID CAUSE_ID``
     - Unassign a cause from a user.
   * - ``extras ID``
     - List a user's custom key/value data.
   * - ``set-extras ID``
     - Replace a user's extras.
   * - ``hours ID``
     - List the hours a user has submitted.
   * - ``interests ID``
     - List a user's interests.
   * - ``add-interest ID INTEREST_ID``
     - Assign an interest to a user.
   * - ``remove-interest ID INTEREST_ID``
     - Unassign an interest from a user.
   * - ``welcome-email ID``
     - Send a user the site's welcome email. A GET with a side effect, so
       ``--read-only`` blocks it.
   * - ``oneclick ID``
     - Mint a one-click login link for a user. Also a GET with a side
       effect -- it hands out a credential -- so ``--read-only`` blocks it
       too.
   * - ``optouts ID``
     - Show which message areas a user has opted out of.
   * - ``add-optout ID AREAS...``
     - Opt a user out of messaging.
   * - ``remove-optout ID AREAS...``
     - Lift named areas from a user's opt-out list.
   * - ``qualifications ID``
     - List a user's qualifications.
   * - ``registration-answers ID``
     - List a user's custom registration answers.
   * - ``set-registration-answers ID``
     - Store a user's custom registration answers.
   * - ``responses ID``
     - List the needs a user has signed up for.
   * - ``tracks ID``
     - List a user's tracks.
   * - ``tags ID``
     - List a user's tags.
   * - ``add-tags ID TAGS...``
     - Add one or more tags, by name, to a user.
   * - ``remove-tag ID TAG_ID``
     - Remove a tag from a user.

``agencies`` -- manage agencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Command
     - Description
   * - ``list``
     - List agencies, paging through every match.
   * - ``get ID``
     - Show one agency.
   * - ``create``
     - Create an agency.
   * - ``update ID``
     - Update an agency, sending only the fields you name.
   * - ``delete ID``
     - Delete an agency (soft delete).
   * - ``causes ID``
     - List the causes attached to an agency.
   * - ``add-cause ID CAUSE_ID``
     - Attach a cause to an agency.
   * - ``remove-cause ID CAUSE_ID``
     - Detach a cause from an agency.
   * - ``clusters ID``
     - List the clusters attached to an agency.
   * - ``add-cluster ID CLUSTER_ID``
     - Attach a cluster to an agency.
   * - ``remove-cluster ID CLUSTER_ID``
     - Detach a cluster from an agency.
   * - ``managers ID``
     - List the users who manage an agency.
   * - ``add-manager ID USER_ID``
     - Make a user a manager of an agency.
   * - ``remove-manager ID USER_ID``
     - Remove a user as a manager of an agency.
   * - ``tags ID``
     - List an agency's tags.
   * - ``add-tags ID TAGS...``
     - Add one or more tags, by name, to an agency.
   * - ``remove-tag ID TAG_ID``
     - Remove a tag from an agency.

``needs`` -- manage needs
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Command
     - Description
   * - ``list``
     - List needs, paging through every match.
   * - ``get ID``
     - Show one need.
   * - ``create``
     - Create a need.
   * - ``update ID``
     - Update a need, sending only the fields you name.
   * - ``delete ID``
     - Delete a need (soft delete).
   * - ``responses ID``
     - List the responses (sign-ups) to a need.
   * - ``questions ID``
     - List the custom questions asked of volunteers responding to a need.
   * - ``add-shift ID``
     - Add a shift to a need.
   * - ``remove-shift ID SHIFT_ID``
     - Remove a shift from a need.
   * - ``add-interest ID INTEREST_ID``
     - Attach an interest to a need.
   * - ``remove-interest ID INTEREST_ID``
     - Detach an interest from a need.
   * - ``add-qualification ID QUALIFICATION_ID``
     - Attach a qualification to a need.
   * - ``remove-qualification ID QUALIFICATION_ID``
     - Detach a qualification from a need.

``events`` -- manage events
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Command
     - Description
   * - ``list``
     - List events, paging through every match.
   * - ``get ID``
     - Show one event.
   * - ``create``
     - Create an event.
   * - ``update ID``
     - Update an event, sending only the fields you name.
   * - ``delete ID``
     - Delete an event (soft delete).

``hours`` -- manage hour records
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Command
     - Description
   * - ``list``
     - List hour records, paging through every match.
   * - ``get ID``
     - Show one hour record.
   * - ``create``
     - Create an hour record.
   * - ``update ID``
     - Update an hour record, sending only the fields you name.
   * - ``delete ID``
     - Delete an hour record (soft delete).

``responses`` -- manage responses (need sign-ups)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Command
     - Description
   * - ``list``
     - List responses, paging through every match.
   * - ``get ID``
     - Show one response.
   * - ``create``
     - Create a response.
   * - ``update ID``
     - Update a response, sending only the fields you name.
   * - ``delete ID``
     - Delete a response (soft delete).

``teams`` -- manage teams
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Command
     - Description
   * - ``list``
     - List teams, paging through every match.
   * - ``get ID``
     - Show one team.
   * - ``create``
     - Create a team.
   * - ``delete ID``
     - Delete a team (soft delete).
   * - ``add-member ID MEMBER``
     - Attach a member to a team.
   * - ``remove-member ID MEMBER``
     - Detach a member from a team.

``groups`` -- manage groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Command
     - Description
   * - ``list``
     - List groups, paging through every match.
   * - ``get ID``
     - Show one group.
   * - ``create``
     - Create a group.
   * - ``update ID``
     - Update a group, sending only the fields you name.
   * - ``delete ID``
     - Delete a group (soft delete).
   * - ``add-need ID NEED_ID``
     - Attach a need to a group.
   * - ``remove-need ID NEED_ID``
     - Detach a need from a group.
   * - ``add-user ID USER_ID``
     - Attach a user to a group.
   * - ``remove-user ID USER_ID``
     - Detach a user from a group.

``qualifications`` -- manage qualifications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Command
     - Description
   * - ``list``
     - List qualifications, paging through every match.
   * - ``get ID``
     - Show one qualification.
   * - ``create``
     - Create a qualification.
   * - ``update ID``
     - Update a qualification, sending only the fields you name.
   * - ``delete ID``
     - Delete a qualification (soft delete).
   * - ``users ID``
     - List the users who hold a qualification.

``benchmarks`` -- manage benchmarks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Command
     - Description
   * - ``list``
     - List benchmarks, paging through every match.
   * - ``get ID``
     - Show one benchmark.
   * - ``create``
     - Create a benchmark.
   * - ``update ID``
     - Update a benchmark, sending only the fields you name.
   * - ``delete ID``
     - Delete a benchmark (soft delete).
   * - ``users ID``
     - List the users who have earned a benchmark.

``clusters``, ``causes``, ``interests``, ``impacts``, ``registration-questions``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Small, mostly read-only lookup endpoints:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Command
     - Description
   * - ``clusters list``
     - List clusters.
   * - ``clusters create``
     - Create a cluster.
   * - ``clusters delete ID``
     - Delete a cluster.
   * - ``causes list``
     - List the site's available causes.
   * - ``interests list``
     - List the site's available interests.
   * - ``impacts list``
     - List the site's available impact areas.
   * - ``registration-questions list``
     - List the site's custom registration questions.

``reports`` -- aggregate answers the API will not compute
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Command
     - Description
   * - ``attendance``
     - Rank a program's volunteers by how many of its sessions they
       attended, highest first.

Every command here only reads, so none of them prompts and all of them work
under ``--read-only``.

``attendance`` takes attendance from hour records: a volunteer counts as
having attended on every distinct date they logged time against the matched
needs, so two entries on one day are one program attended. The table adds a
1-based ``rank``, sorted by programs attended, then total hours, then name.
Its options:

``--program TEXT``
    Match needs whose title contains this text, case-insensitively. The
    ``/needs`` endpoint's own ``need_title`` filter is tried first, and the
    full need list (inactive included) is scanned as a fallback when that
    returns nothing.

``--need-id INT``
    Count this need id exactly, skipping title resolution. Repeatable, and
    may be combined with ``--program``. At least one of ``--program`` and
    ``--need-id`` is required.

``--start YYYY-MM-DD`` / ``--end YYYY-MM-DD``
    Inclusive bounds on the attendance date. Both are optional; omitting
    them counts everything.

``--year INT``
    Shorthand for ``--start YEAR-01-01 --end YEAR-12-31``. It may not be
    combined with ``--start`` or ``--end``.

``--status TEXT``
    Only count hour records with this status, e.g. ``approved``
    (case-insensitive, repeatable). By default every status counts.

``--full-scan``
    Page through every hour record. ``/hours`` has no need, user or
    attendance-date filter, so the report scans and narrows client-side; by
    default a ``--start`` bound also sends ``since_created``, which skips the
    pages of hours logged before the period and makes that scan far shorter.
    That trades completeness for speed -- hours logged *before* the date they
    were served would be missed -- so pass ``--full-scan`` when the report
    must be exhaustive.

``--local PATH``
    Merge in volunteers from VolunteerLocal_. See below.

With ``--json`` the output is a single object with a ``needs`` key (what the
program name matched) and a ``rows`` key (the ranking), because which needs
were counted is half the answer.

.. code-block:: bash

   galaxy reports attendance --program "hollywood" --year 2026

Merging VolunteerLocal in with ``--local``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sites that also run VolunteerLocal_ can put the two systems side by side.
``--local`` takes the path to a file VolunteerLocal's data already sits in,
and the kind is told from the suffix:

``.sqlite3``, ``.sqlite``, ``.db``
    A sqlite database holding the ``selah_vol_db_volunteerrecord`` table.
    It is opened **read-only**, so the report can never write to it.

``.csv``
    A VolunteerLocal export, in either variant it produces -- the full
    volunteer database or the per-signup export (which carries the same
    totals but no shift dates). Unknown columns, including the long tail of
    per-event question columns, are ignored.

There is no API to call: VolunteerLocal exports files, so a file is what
this reads. A missing path, an unreadable file or a suffix that is neither
of the above is a plain error, and it is reported before the hours scan
starts rather than after it.

Volunteers are matched on **email** first, case-insensitively. When the
emails do not line up -- either side is missing one, or they simply differ,
which happens when someone uses different addresses in the two systems -- a
fallback is tried against the volunteer's full ``first last`` name, checked
against every VolunteerLocal record. Name-only matches are best-effort: two
volunteers who share a full name can occasionally attach the wrong record,
so verify by email when it matters. Matched Galaxy rows
gain ``vl_shifts``, ``vl_events`` and ``vl_hours`` columns (blank where
VolunteerLocal knows nothing about that volunteer, and ``vl_events`` is
always blank for the sqlite source, which has no event count). Volunteers
only VolunteerLocal knows are appended *after* the ranking with a ``-``
rank, ordered by shifts, so the report also answers "who is missing from
Galaxy Digital entirely?".

.. warning::

    The ``vl_`` figures are **lifetime totals**. The exports have no
    per-date rows, so nothing can narrow them: ``--start``, ``--end`` and
    ``--year`` bound the Galaxy Digital columns only. The table prints a
    note saying so whenever a period is in play.

With ``--json`` the object gains a ``local_only`` key -- the unmatched
VolunteerLocal records, each with ``email``, ``first_name``, ``last_name``,
``total_shifts``, ``total_events``, ``total_hours``, ``outreach``,
``non_outreach``, ``first_shift`` and ``last_shift`` -- and every row in
``rows`` gains a ``volunteerlocal`` key holding that same object, or
``null`` when the volunteer was not matched.

.. code-block:: bash

   galaxy reports attendance --program "hollywood" --year 2026 \
       --local ~/Development/selah_vol_stats/db.sqlite3

.. _VolunteerLocal: https://volunteerlocal.com

Soft deletes
------------

Where the table above says "soft delete", the API marks the record inactive
rather than removing it, so it may reappear when listing with
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
