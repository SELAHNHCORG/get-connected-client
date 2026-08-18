"""Neutralize the parent ``_isolate_env`` autouse fixture for live tests.

``tests/conftest.py`` defines an autouse fixture ``_isolate_env`` that forces
``GALAXY_API_KEY=test-key`` and clears ``GALAXY_API_TOKEN`` and
``GALAXY_API_URL`` for every test in the suite -- exactly right for the
respx-mocked unit tests, exactly wrong here: it would stomp the user's real
``GALAXY_API_KEY`` with a fake one and delete the ``GALAXY_API_TOKEN`` these
tests actually authenticate with, before a live test ever ran.

pytest resolves fixtures by walking from the test's own module up through
enclosing conftest.py files and stopping at the first match for a given
name. A fixture defined here, in ``tests/live/conftest.py``, is *closer* to
tests under ``tests/live/`` than the one in ``tests/conftest.py``, so it
fully shadows -- not supplements -- the parent fixture: the parent
``_isolate_env`` body never executes for any test under this directory,
autouse or not. This was verified directly (not just reasoned about) with a
throwaway experiment: a scratch package with a parent conftest defining an
autouse fixture that sets an env var, and a child conftest one directory
down redefining the same-named fixture as a no-op. A parent-directory test
observed the parent's env var; a child-directory test observed it was never
set -- proving the child fixture ran *instead of*, not *in addition to*, the
parent's.

Net effect: live tests see the real process environment untouched, so
``GALAXY_API_TOKEN`` (the credential that actually authenticates),
``GALAXY_API_KEY`` and ``GALAXY_API_URL`` (if the user wants something other
than the production default) pass straight through to
:class:`~galaxy_digital_cli.client.GalaxyClient`. This works
because the ``live_client`` fixtures in ``test_live_read.py`` and
``test_live_write.py`` read ``GALAXY_API_URL`` themselves and pass it as
``base_url=`` explicitly -- ``GalaxyClient`` itself never reads that env var.

This does not affect gating. The ``pytest.mark.skipif`` conditions in
``test_live_read.py`` and ``test_live_write.py`` read ``os.environ`` at
*collection* time, which happens before any fixture -- autouse or
otherwise -- runs. So skip/deselect decisions are made off the real
environment regardless of what this fixture does or doesn't touch.
"""

import pytest


@pytest.fixture(autouse=True)
def _isolate_env():
    """No-op override: see module docstring for why this must NOT set
    GALAXY_API_KEY or clear GALAXY_API_TOKEN / GALAXY_API_URL like the
    parent fixture does."""
    yield
