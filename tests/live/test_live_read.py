"""Read-only smoke tests against the real API.

Run explicitly: ``uv run pytest -m live``. Requires GALAXY_API_KEY.
Never run in CI.
"""

import os

import pytest

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.environ.get("GALAXY_API_KEY"), reason="GALAXY_API_KEY not set"
    ),
]


@pytest.fixture(scope="module")
def live_client():
    from galaxy_digital_cli.client import GalaxyClient

    # base_url is passed explicitly here because GalaxyClient itself never
    # reads GALAXY_API_URL -- see tests/live/conftest.py's module docstring.
    # read_only=True: belt and suspenders -- these tests must never write.
    with GalaxyClient(
        base_url=os.environ.get("GALAXY_API_URL", "us1"), read_only=True
    ) as client:
        yield client


def test_auth_and_causes(live_client):
    # A successful call is itself the confirmation that the raw-key
    # Authorization header format is correct -- a wrong scheme would 401 and
    # raise AuthError instead of returning here.
    causes = live_client.lookups.causes()
    assert isinstance(causes, list)


def test_list_users_first_page(live_client):
    users = []
    for user in live_client.users.list(per_page=5):
        users.append(user)
        if len(users) >= 5:
            break
    assert users and users[0].id


def test_read_only_client_blocks_writes(live_client):
    from galaxy_digital_cli.exceptions import ReadOnlyError

    with pytest.raises(ReadOnlyError):
        live_client.users.create(user_fname="nope")
