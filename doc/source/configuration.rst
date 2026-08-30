Configuration
=============

The ``galaxy`` command resolves its settings through
:func:`~get_connected_client.config.load_settings`, with a fixed precedence,
highest first:

.. list-table:: CLI precedence
   :header-rows: 1
   :widths: 10 90

   * - Order
     - Source
   * - 1
     - Explicit arguments -- the CLI flags ``--api-key``, ``--token``,
       ``--url`` and ``--read-only``.
   * - 2
     - Environment variables -- ``GALAXY_API_KEY``, ``GALAXY_API_TOKEN``,
       ``GALAXY_API_URL``, ``GALAXY_READ_ONLY``.
   * - 3
     - Built-in defaults -- server ``us1``, ``read_only`` off, no
       credentials.

There is no configuration file: nothing is persisted to disk, and no
plaintext key or token is ever written anywhere by this tool. A source that
provides a value wins outright; it is not merged with lower sources for
that same setting. ``read_only`` is the one exception at the client level:
see `Read-only modes`_ below.

One setting is deliberately outside that table: ``GALAXY_FORMAT`` /
``--format`` chooses a *renderer*, never anything the API sees, so it is
resolved by the CLI itself rather than by
:func:`~get_connected_client.config.load_settings` -- see `Output format`_.

Two credentials, two jobs
--------------------------

The site API key does **not** authenticate requests. Sent as an
``Authorization`` value -- raw or ``Bearer``-prefixed -- it is answered with
a 401. What it *is* good for is identifying the site in the body of a
login, which is where the credential that does authenticate comes from:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Credential
     - Role
   * - ``GALAXY_API_KEY`` (site key)
     - A UUID issued by your site. Sent only as the ``key`` field of the
       ``POST /users/login`` body. Never authenticates anything on its own.
   * - ``GALAXY_API_TOKEN`` (session token)
     - What that login returns: a JWT valid for roughly a year, sent on
       every request as ``Authorization: Bearer <token>``.

So a session begins by trading the site key plus an email and password for
a token:

.. code-block:: bash

   export GALAXY_API_KEY=YOUR_SITE_KEY
   eval "$(galaxy auth login --email you@example.org --export)"

``--export`` writes exactly one line to stdout --
``export GALAXY_API_TOKEN='<token>'`` -- and routes the password prompt and
every other message to stderr, which is what makes the ``eval`` safe. See
:doc:`cli` for the rest of the ``auth`` sub-app.

The wire format is the same either way: the client prefixes whichever
credential it has with ``Bearer `` (and leaves a value that already starts
with ``Bearer `` alone, so exporting a whole header value works too). A
client holding both sends the *token*; one holding only a site key still
sends it -- harmlessly, since login is the only thing it can accomplish --
and the resulting 401 is the API telling you to run
``galaxy auth login``.

Library behavior
----------------

The table above describes the CLI. :class:`~get_connected_client.client.GalaxyClient`
deliberately implements *none* of that chain except the two credentials'
env var fallbacks: it takes what you pass it, and reads ``GALAXY_API_KEY``
and ``GALAXY_API_TOKEN`` when ``api_key`` and ``token`` are omitted.
``GALAXY_API_URL`` is never consulted by the client, so ``base_url``
defaults to ``us1`` regardless of what the CLI would have resolved.
(``GALAXY_READ_ONLY`` is the one other env var the client does honor, and
only in one direction -- see `Read-only modes`_.)

.. code-block:: python

   from get_connected_client import GalaxyClient

   # explicit arguments; base_url accepts the same aliases as --url
   GalaxyClient(token="eyJ...", base_url="us2")

   # both omitted -> GALAXY_API_TOKEN / GALAXY_API_KEY; server stays us1
   GalaxyClient()

At least one of the two must be resolvable, or the constructor raises
:class:`~get_connected_client.exceptions.MissingAPIKeyError`.
:meth:`GalaxyClient.login <get_connected_client.client.GalaxyClient.login>` is
the library counterpart of ``galaxy auth login``: it defaults the ``key``
field from ``api_key``, and on success adopts the returned token, so every
later request carries it.

.. code-block:: python

   with GalaxyClient(api_key="SITE-KEY") as client:
       client.login("you@example.org", "hunter2")
       client.users.get(5)          # authenticated with the new token

Library callers who *want* the CLI's full resolution can opt into it by
running it themselves and handing the result to the constructor:

.. code-block:: python

   from get_connected_client import GalaxyClient
   from get_connected_client.config import load_settings

   s = load_settings()
   client = GalaxyClient(
       api_key=s.api_key, token=s.token, base_url=s.url, read_only=s.read_only
   )

:func:`~get_connected_client.config.load_settings` also accepts the same
four overrides the CLI passes it (``api_key``, ``token``, ``url``,
``read_only``), which slot in at level 1 of the table.

Environment variables
----------------------

``GALAXY_API_KEY``
    The site key, sent as the ``key`` field of the login body. It cannot
    authenticate requests -- see `Two credentials, two jobs`_.

``GALAXY_API_TOKEN``
    The session token from ``galaxy auth login``, sent as
    ``Authorization: Bearer <token>``. This is the credential that
    authenticates.

``GALAXY_API_URL``
    The server URL or alias (``us1``, ``us2``, ``ca``).

``GALAXY_READ_ONLY``
    A tri-state flag. Unset (or empty) means "no opinion" and falls through
    to the default (off). Any of ``1``, ``true``, ``yes``, ``on``
    (case-insensitive) means true; anything else means false.

``GALAXY_FORMAT``
    How results are rendered: ``table`` (the default) or ``json``,
    case-insensitive. **CLI-only** -- unlike the four above, it is not a
    client or library setting at all;
    :class:`~get_connected_client.client.GalaxyClient` returns models and
    never consults it. See `Output format`_.

Set them for the session, or add them to your shell profile
(``~/.bashrc``, ``~/.zshrc``, ...) to persist them:

.. code-block:: bash

   export GALAXY_API_KEY=YOUR_SITE_KEY
   export GALAXY_API_URL=us1        # us1 (default), us2, or ca
   export GALAXY_READ_ONLY=1        # optional: block every write
   export GALAXY_FORMAT=json        # optional: JSON instead of tables

   # the token is minted, not typed -- re-run when it expires (~1 year)
   eval "$(galaxy auth login --email you@example.org --export)"

Inspecting the result
---------------------

``galaxy config show`` reports what the chain above actually resolved, and
where each value came from -- ``flag``, ``env`` or ``default``:

.. code-block:: bash

   galaxy config show          # credentials redacted to their last 4 characters
   galaxy --json config show   # same values, as JSON

Neither the key nor the token is ever printed in full, by either renderer,
so the output is safe to paste into a bug report.

The listing includes a ``format`` row, which is the only one that is not a
:class:`~get_connected_client.config.Settings` field -- it is there precisely
because an exported ``GALAXY_FORMAT`` is otherwise invisible.

Output format
-------------

Every command renders through one global switch:

``--format table``
    A rich table, the default. Human-readable, and explicitly not a data
    interchange format -- column widths, wrapping and styling are free to
    change between releases.

``--format json``
    Raw JSON on stdout, for scripting. ``galaxy --format json needs list |
    jq ...`` is the intended shape. Writes that return no body still emit
    ``{"ok": true}``, so a successful command never produces empty stdout.

``--json`` is a shorthand for ``--format json``, kept because it predates
the general option; the two are interchangeable. Passing both is fine when
they agree (``--json --format json``) and is refused when they contradict
each other (``--json --format table``), rather than one silently winning.

The default comes from ``GALAXY_FORMAT``, so a scripting-oriented shell can
opt in once:

.. code-block:: bash

   export GALAXY_FORMAT=json
   galaxy needs list                    # JSON, no flag needed
   galaxy --format table needs list     # ... and back to a table, just here

Precedence is the familiar one -- an explicit ``--format`` (or ``--json``)
beats ``GALAXY_FORMAT``, which beats the ``table`` default. Values are
case-insensitive in both places; anything that is not a known format is a
usage error.

Server aliases
--------------

``url`` accepts either a full URL or one of three built-in aliases,
resolved by :func:`~get_connected_client.config.resolve_url`:

.. list-table::
   :header-rows: 1

   * - Alias
     - URL
   * - ``us1`` (default)
     - ``https://api.galaxydigital.com/api``
   * - ``us2``
     - ``https://www.volunteerapi.com/api``
   * - ``ca``
     - ``https://ca.volunteerapi.com/api``

Read-only modes
----------------

Because the only account available during development is a production
account, blocking writes is a first-class feature, not an afterthought.
There are three independent ways to turn it on:

1. **Constructor**: ``GalaxyClient(read_only=True)``.
2. **CLI flag**: ``galaxy --read-only ...``.
3. **Environment**: ``GALAXY_READ_ONLY=1`` (export it to make it stick for
   the whole session).

:attr:`GalaxyClient.read_only <get_connected_client.client.GalaxyClient.read_only>`
is the boolean OR of the constructor flag and the environment variable --
either one can turn read-only mode *on*, but neither can turn it back
*off* once the other has set it. Concretely, ``GALAXY_READ_ONLY=0`` cannot
unblock a client built with ``read_only=True``.

The guard is enforced twice: once in
:meth:`GalaxyClient.request <get_connected_client.client.GalaxyClient.request>`
before any request is issued (including GET endpoints that have side
effects, via ``treat_as_write``), and again as an ``httpx`` request hook on
the underlying client, in case something reaches it through the ``http``
escape hatch instead of ``request()``. A blocked write raises
:class:`~get_connected_client.exceptions.ReadOnlyError`.

Read-only mode therefore blocks more than the obvious
``create``/``update``/``delete``. Four further commands are gated -- the
``auth`` pair because they are POSTs like any other write, and two
``users`` commands because the spec models them as GETs even though each
has a real side effect:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Command
     - Why it is gated
   * - ``galaxy auth login``
     - Mints a session token.
   * - ``galaxy auth authenticate``
     - Mints a one-click login link.
   * - ``galaxy users welcome-email``
     - Puts mail in someone's inbox
       (``GET /users/{id}/welcomeEmail``).
   * - ``galaxy users oneclick``
     - Hands out a passwordless login link
       (``GET /users/{id}/oneclick``) -- the same artifact
       ``authenticate`` returns, so it is gated the same way.

Of those four, only ``welcome-email`` also shows the confirmation prompt
described below. The ``auth`` pair skips it because the operator just
typed a password, so a second "are you sure?" would not add anything (and
neither command echoes the password back); ``oneclick`` skips it because
it changes no stored record -- it prints a link. Read-only mode, not the
prompt, is what guards those three.

Confirm prompts and ``--yes``
-------------------------------

Independent of read-only mode, every CLI write shows the operator what is
about to happen and requires explicit confirmation:

.. code-block:: text

   $ galaxy users delete 42
   About to write to the API: DELETE /users/42
   Proceed? [y/N]:

Pass ``--yes``/``-y`` on the root command to skip the prompt -- required
for non-interactive use such as scripts or CI. This is a UX safeguard, not
a security boundary: it runs in the CLI layer only
(``confirm_write()``), so library callers
using :class:`~get_connected_client.client.GalaxyClient` directly do not get
a prompt -- read-only mode is the mechanism for guarding library code.
