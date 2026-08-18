"""LIVE WRITE tests -- they touch production. Only run with the user present:

    GALAXY_LIVE_WRITE_ACK=I-UNDERSTAND-THIS-WRITES-TO-PROD uv run pytest -m live_write

The scenarios are agreed with the user at run time; this file starts with a
single reversible round-trip and grows only by explicit agreement.
"""

import os
import uuid

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

    # base_url is passed explicitly here because GalaxyClient itself never
    # reads GALAXY_API_URL -- see tests/live/conftest.py's module docstring.
    with GalaxyClient(base_url=os.environ.get("GALAXY_API_URL", "us1")) as client:
        yield client


_SELFTEST_PREFIX = "galaxy-digital-cli-selftest"


def test_cluster_round_trip(live_client):
    """Create a throwaway cluster, verify it exists, delete it."""
    # GET /clusters declares no paging params in the spec, so listing here
    # relies on the server returning the full (small) collection in one page.

    # Best-effort sweep first: delete any leftover clusters from prior
    # crashed runs so they don't pile up.
    for cluster in live_client.clusters.list():
        if cluster.name and cluster.name.startswith(_SELFTEST_PREFIX):
            cluster_id = getattr(cluster, "id", None)
            if cluster_id is not None:
                live_client.clusters.delete(cluster_id)

    name = f"{_SELFTEST_PREFIX}-{uuid.uuid4().hex[:8]}"
    made = live_client.clusters.create(name=name)
    made_id = getattr(made, "id", None)
    if made_id is None:
        # The API didn't hand back a usable id -- try to find the cluster we
        # just created by name so it doesn't leak, then fail loudly (not
        # skip): a stranded cluster with no id to clean up is a real bug.
        for cluster in live_client.clusters.list():
            if cluster.name == name:
                stray_id = getattr(cluster, "id", None)
                if stray_id is not None:
                    live_client.clusters.delete(stray_id)
        pytest.fail(
            f"API did not return the created cluster id; cluster {name!r} "
            "may need manual cleanup"
        )
    try:
        names = [c.name for c in live_client.clusters.list()]
        assert name in names
    finally:
        live_client.clusters.delete(made_id)
