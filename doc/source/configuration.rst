Configuration
=============

Settings are resolved by :func:`~galaxy_digital_cli.config.load_settings`
with a fixed precedence, highest first:

.. list-table:: Precedence
   :header-rows: 1
   :widths: 10 90

   * - Order
     - Source
   * - 1
     - Explicit arguments -- CLI flags (``--api-key``, ``--url``,
       ``--read-only``) or constructor keyword arguments
       (:class:`~galaxy_digital_cli.client.GalaxyClient`).
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
effects, such as ``/users/{id}/welcomeEmail``, via ``treat_as_write``), and
again as an ``httpx`` request hook on the underlying client, in case
something reaches it through the ``http`` escape hatch instead of
``request()``. A blocked write raises
:class:`~galaxy_digital_cli.exceptions.ReadOnlyError`.

``galaxy auth login`` and ``galaxy auth authenticate`` are blocked by
``--read-only`` too: minting a session token or a one-click login link is a
side effect worth gating like any other write, even though neither command
goes through the confirmation prompt described below (the operator just
typed a password; a second "are you sure?" would not add anything, and
neither command echoes the password back).

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
(:func:`~galaxy_digital_cli.cli._confirm.confirm_write`), so library callers
using :class:`~galaxy_digital_cli.client.GalaxyClient` directly do not get
a prompt -- read-only mode is the mechanism for guarding library code.
