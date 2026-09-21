"""Every updatable resource's ``request_fields`` matches its PUT schema.

``doc/api.yml`` is the vendored source of truth. If Galaxy Digital adds a
field to a request schema, this test fails until the allowlist catches up,
which is the point: a stale allowlist would silently drop that field from
every merged update.
"""

import importlib
import inspect
import pkgutil
from pathlib import Path

import pytest
import yaml

from get_connected_client import resources
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


@pytest.mark.parametrize(("cls", "schema"), PAIRS, ids=[c.__name__ for c, _ in PAIRS])
def test_required_fields_match_spec(schemas, cls, schema):
    expected = frozenset(schemas[schema].get("required", ()))
    assert cls.required_fields == expected, (
        f"{cls.__name__}.required_fields drifted from {schema}: "
        f"missing={sorted(expected - cls.required_fields)} "
        f"extra={sorted(cls.required_fields - expected)}"
    )


@pytest.mark.parametrize(("cls", "schema"), PAIRS, ids=[c.__name__ for c, _ in PAIRS])
def test_every_scalar_request_property_is_a_string(schemas, cls, schema):
    """``Resource.to_request`` stringifies ints on the strength of this.

    If this ever fails, the blanket int->str pass in ``_wire`` has to become
    a per-field decision driven by the spec.
    """
    offenders = {
        name: prop.get("type")
        for name, prop in schemas[schema]["properties"].items()
        if prop.get("type") not in ("string", "array", "object")
    }
    assert offenders == {}, f"{schema} has non-string scalar properties: {offenders}"


def test_every_updatable_resource_is_covered():
    """A new UpdateMixin subclass must be added to PAIRS (and get an allowlist)."""
    covered = {cls for cls, _ in PAIRS}
    found = set()
    for info in pkgutil.iter_modules(resources.__path__):
        module = importlib.import_module(f"{resources.__name__}.{info.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, UpdateMixin)
                and obj is not UpdateMixin
                and obj.__module__ == module.__name__
            ):
                found.add(obj)
    assert found == covered, f"uncovered: {found - covered} stale: {covered - found}"
