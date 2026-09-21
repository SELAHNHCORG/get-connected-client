"""Every updatable resource's ``request_fields`` matches its PUT schema.

``doc/api.yml`` is the vendored source of truth. If Galaxy Digital adds a
field to a request schema, this test fails until the allowlist catches up,
which is the point: a stale allowlist would silently drop that field from
every merged update.
"""

import importlib
import inspect
from pathlib import Path

import pytest
import yaml

from get_connected_client.resources import (
    agencies,
    benchmarks,
    events,
    groups,
    hours,
    needs,
    qualifications,
    responses,
    users,
)
from get_connected_client.resources.base import UpdateMixin

SPEC = Path(__file__).resolve().parents[1] / "doc" / "api.yml"

PAIRS = [
    (users.Users, "userRequestSchema"),
    (needs.Needs, "needRequestSchema"),
    (events.Events, "eventRequestSchema"),
    (groups.Groups, "groupRequestSchema"),
    (hours.Hours, "hourRequestSchema"),
    (responses.Responses, "responseRequestSchema"),
    (agencies.Agencies, "agencyRequestSchema"),
    (qualifications.Qualifications, "qualificationRequestSchema"),
    (benchmarks.Benchmarks, "benchmarkRequestSchema"),
]

#: Every module under ``get_connected_client.resources`` that defines namespaces.
RESOURCE_MODULES = (
    "agencies",
    "auth",
    "benchmarks",
    "events",
    "groups",
    "hours",
    "misc",
    "needs",
    "qualifications",
    "responses",
    "teams",
    "users",
)


@pytest.fixture(scope="module")
def schemas():
    with SPEC.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)["components"]["schemas"]


@pytest.mark.parametrize(("cls", "schema"), PAIRS, ids=[c.__name__ for c, _ in PAIRS])
def test_request_fields_match_spec(schemas, cls, schema):
    expected = frozenset(schemas[schema]["properties"])
    assert cls.request_fields == expected, (
        f"{cls.__name__}.request_fields drifted from {schema}: "
        f"missing={sorted(expected - cls.request_fields)} "
        f"extra={sorted(cls.request_fields - expected)}"
    )


def test_every_updatable_resource_is_covered():
    """A new UpdateMixin subclass must be added to PAIRS (and get an allowlist)."""
    covered = {cls for cls, _ in PAIRS}
    found = set()
    for name in RESOURCE_MODULES:
        module = importlib.import_module(f"get_connected_client.resources.{name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, UpdateMixin)
                and obj is not UpdateMixin
                and obj.__module__ == module.__name__
            ):
                found.add(obj)
    assert found == covered, f"uncovered: {found - covered}"
