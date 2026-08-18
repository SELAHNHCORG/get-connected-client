"""LIVE WRITE tests -- they touch production. Only run with the user present:

    GALAXY_LIVE_WRITE_ACK=I-UNDERSTAND-THIS-WRITES-TO-PROD uv run pytest -m live_write

The scenarios are agreed with the user at run time; this file starts with a
single reversible round-trip and grows only by explicit agreement.
"""

import os

import pytest

ACK = "I-UNDERSTAND-THIS-WRITES-TO-PROD"

pytestmark = [
    pytest.mark.live_write,
    pytest.mark.skipif(
        not os.environ.get("GALAXY_API_KEY"), reason="GALAXY_API_KEY not set"
    ),
    pytest.mark.skipif(
        os.environ.get("GALAXY_LIVE_WRITE_ACK") != ACK,
        reason="GALAXY_LIVE_WRITE_ACK not acknowledged",
    ),
]


@pytest.fixture(scope="module")
def live_client():
    from galaxy_digital_cli.client import GalaxyClient

    with GalaxyClient() as client:
        yield client


def test_cluster_round_trip(live_client):
    """Create a throwaway cluster, verify it exists, delete it."""
    made = live_client.clusters.create(name="galaxy-digital-cli-selftest")
    made_id = getattr(made, "id", None)
    if made_id is None:
        pytest.skip("API did not return the created cluster id; clean up manually")
    try:
        names = [c.name for c in live_client.clusters.list()]
        assert "galaxy-digital-cli-selftest" in names
    finally:
        live_client.clusters.delete(made_id)
