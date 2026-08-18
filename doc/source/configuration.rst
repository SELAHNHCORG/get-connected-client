Configuration
=============

The ``galaxy`` command resolves its settings through
:func:`~galaxy_digital_cli.config.load_settings`, with a fixed precedence,
highest first:

.. list-table:: CLI precedence
   :header-rows: 1
   :widths: 10 90

   * - Order
     - Source
   * - 1
     - Explicit arguments -- the CLI flags ``--api-key``, ``--url`` and
       ``--read-only``.
   * - 2
     - Environment variables -- ``GALAXY_API_KEY``, ``GALAXY_API_URL``,
       ``GALAXY_READ_ONLY``.
   * - 3
     - The config file (``~/.config/galaxy-digital/config.toml`` by
       default, or wherever ``GALAXY_CONFIG_FILE`` points).
   * - 4
     - Built-in defaults -- server ``us1``, ``read_only`` off, no API key.

A source that provides a value wins outright; it is not merged with lower
sources for that same setting. ``read_only`` is the one exception at the
client level: see `Read-only modes`_ below.

Library behavior
----------------

The table above describes the CLI. :class:`~galaxy_digital_cli.client.GalaxyClient`
deliberately implements *none* of that chain except the API key's env var
fallback: it takes what you pass it, and reads ``GALAXY_API_KEY`` when
``api_key`` is omitted. ``GALAXY_API_URL`` and the config file are never
consulted by the client, so ``base_url`` defaults to ``us1`` regardless of
what the CLI would have resolved. (``GALAXY_READ_ONLY`` is the one env var
the client does honor, and only in one direction -- see `Read-only
modes`_.)

.. code-block:: python

   from galaxy_digital_cli import GalaxyClient

   # explicit arguments; base_url accepts the same aliases as --url
   GalaxyClient(api_key="...", base_url="us2")

   # api_key omitted -> GALAXY_API_KEY; server stays us1
   GalaxyClient()

Library callers who *want* the CLI's full resolution can opt into it by
running it themselves and handing the result to the constructor:

.. code-block:: python

   from galaxy_digital_cli import GalaxyClient
   from galaxy_digital_cli.config import load_settings

   s = load_settings()
   client = GalaxyClient(api_key=s.api_key, base_url=s.url, read_only=s.read_only)

:func:`~galaxy_digital_cli.config.load_settings` also accepts the same
three overrides the CLI passes it (``api_key``, ``url``, ``read_only``),
which slot in at level 1 of the table.

Environment variables
----------------------

``GALAXY_API_KEY``
    The API key sent as the ``Authorization`` header.

``GALAXY_API_URL``
    The server URL or alias (``us1``, ``us2``, ``ca``).

``GALAXY_READ_ONLY``
    A tri-state flag. Unset (or empty) means "no opinion" and falls through
    to the config file. Any of ``1``, ``true``, ``yes``, ``on``
    (case-insensitive) means true; anything else means false.

``GALAXY_CONFIG_FILE``
    Overrides the config file path used by :func:`~galaxy_digital_cli.config.config_file`.

Config file
-----------

Location
   ``user_config_path("galaxy-digital") / "config.toml"`` -- typically
   ``~/.config/galaxy-digital/config.toml`` on Linux/macOS, or the platform
   equivalent via `platformdirs`. Override with ``GALAXY_CONFIG_FILE``.

Keys
   ``api_key``, ``url``, ``read_only`` -- the same three settings, as plain
   TOML values.

Permissions
   The file is created (and any existing file re-chmod'd) to mode ``0600``
   on every write, since it may hold a plaintext API key.

Manage it with the CLI rather than editing it by hand:

.. code-block:: bash

   galaxy config set api_key YOUR_API_KEY
   galaxy config set url us1
   galaxy config set read_only true
   galaxy config show     # api_key is redacted to its last 4 characters
   galaxy config path
   galaxy config unset read_only

Server aliases
--------------

``url`` accepts either a full URL or one of three built-in aliases,
resolved by :func:`~galaxy_digital_cli.config.resolve_url`:

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
2. **CLI flag**: ``galaxy --read-only ...``, or persist it with
   ``galaxy config set read_only true``.
3. **Environment**: ``GALAXY_READ_ONLY=1``.

:attr:`GalaxyClient.read_only <galaxy_digital_cli.client.GalaxyClient.read_only>`
is the boolean OR of the constructor flag and the environment variable --
either one can turn read-only mode *on*, but neither can turn it back
*off* once the other has set it. Concretely, ``GALAXY_READ_ONLY=0`` cannot
unblock a client built with ``read_only=True``.

The guard is enforced twice: once in
:meth:`GalaxyClient.request <galaxy_digital_cli.client.GalaxyClient.request>`
before any request is issued (including GET endpoints that have side
effects, via ``treat_as_write``), and again as an ``httpx`` request hook on
the underlying client, in case something reaches it through the ``http``
escape hatch instead of ``request()``. A blocked write raises
:class:`~galaxy_digital_cli.exceptions.ReadOnlyError`.

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
using :class:`~galaxy_digital_cli.client.GalaxyClient` directly do not get
a prompt -- read-only mode is the mechanism for guarding library code.
