import json

import pytest

from get_connected_client.exceptions import NotFoundError
from get_connected_client.models.common import Tag
from get_connected_client.models.hours import Hour
from get_connected_client.models.needs import Need
from get_connected_client.models.responses import Response
from get_connected_client.resources.base import (
    Change,
    CreateMixin,
    DeleteMixin,
    GetMixin,
    ListMixin,
    PatchPlan,
    Resource,
    UpdateMixin,
    _id_str,
    _id_strs,
    _names,
    _wire,
)
from get_connected_client.resources.hours import Hours
from get_connected_client.resources.needs import Needs
from get_connected_client.resources.responses import Responses


class Widgets(
    ListMixin[Tag],
    GetMixin[Tag],
    CreateMixin[Tag],
    UpdateMixin[Tag],
    DeleteMixin[Tag],
    Resource[Tag],
):
    path = "/widgets"
    model = Tag


def test_list_parses_and_filters(client, api):
    route = api.get("/widgets").respond(json={"data": [{"id": 1, "name": "a"}]})
    rows = list(Widgets(client).list(show_inactive=True, since_created="2024-01-01"))
    assert isinstance(rows[0], Tag) and rows[0].name == "a"
    params = route.calls.last.request.url.params
    assert params["show_inactive"] == "Yes"
    assert params["since_created"] == "2024-01-01"


def test_list_show_inactive_false(client, api):
    route = api.get("/widgets").respond(json={"data": [{"id": 1, "name": "a"}]})
    list(Widgets(client).list(show_inactive=False))
    assert route.calls.last.request.url.params["show_inactive"] == "No"


def test_list_show_inactive_omitted(client, api):
    """None must omit the param entirely, not send a falsy value."""
    route = api.get("/widgets").respond(json={"data": [{"id": 1, "name": "a"}]})
    # `list()` with no arguments is also the typing smoke test: the declared
    # return type is Iterator[Tag] (checked statically by mypy/pyright), and
    # the isinstance below pins the runtime half of that contract.
    rows = list(Widgets(client).list())
    assert isinstance(rows[0], Tag)
    assert "show_inactive" not in route.calls.last.request.url.params


def test_get(client, api):
    api.get("/widgets/5").respond(json={"data": {"id": 5, "name": "w"}})
    assert Widgets(client).get(5).id == 5


def test_create_update_delete(client, api):
    api.post("/widgets").respond(json={"data": {"id": 9, "name": "n"}})
    made = Widgets(client).create(name="n")
    assert made.id == 9
    api.put("/widgets/9").respond(json={})
    assert Widgets(client).update(9, name="m") == {}
    route = api.delete("/widgets/9").respond(json={})
    Widgets(client).delete(9)
    assert route.called


def test_sublist_parses_rows(client, api):
    api.get("/widgets/1/things").respond(
        json={"data": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]}
    )
    rows = Widgets(client)._get_list("/widgets/1/things", Tag)
    assert len(rows) == 2
    assert all(isinstance(r, Tag) for r in rows)
    assert [r.name for r in rows] == ["a", "b"]


def test_sublist_404_empty(client, api):
    api.get("/widgets/1/things").respond(status_code=404)
    assert Widgets(client)._get_list("/widgets/1/things", Tag) == []


class RequestWidgets(Widgets):
    """Widgets with a request allowlist: `name`/`tags` are writable, `id` is not.

    `tags` is not a declared field of `Tag`; `GalaxyModel`'s `extra="allow"`
    lets it round-trip through `to_request` untouched, which is what lets
    the tests below exercise `_same`'s list handling.
    """

    path = "/rwidgets"
    request_fields = frozenset({"name", "tags"})
    required_fields = frozenset({"name"})


def test_to_request_default_keeps_nothing(client):
    """With no request_fields declared, nothing is writable."""
    assert Widgets(client).to_request(Tag(id=1, name="a")) == {}


def test_to_request_filters_to_request_fields(client):
    assert RequestWidgets(client).to_request(Tag(id=1, name="a")) == {"name": "a"}


def test_to_request_drops_none(client):
    assert RequestWidgets(client).to_request(Tag(id=1, name=None)) == {}


def test_prepare_patch_merges_and_reports_changes(client, api):
    api.get("/rwidgets/5").respond(json={"data": {"id": 5, "name": "old"}})
    plan = RequestWidgets(client).prepare_patch(5, name="new", colour="red")
    assert plan.current == {"name": "old"}
    assert plan.body == {"name": "new", "colour": "red"}
    assert plan.changes == [
        Change(field="name", old="old", new="new"),
        Change(field="colour", old=None, new="red"),
    ]


def test_prepare_patch_unchanged_value_is_not_a_change(client, api):
    api.get("/rwidgets/5").respond(json={"data": {"id": 5, "name": "same"}})
    plan = RequestWidgets(client).prepare_patch(5, name="same")
    assert plan.changes == []
    assert plan.body == {"name": "same"}


def test_prepare_patch_int_and_numeric_string_are_same(client, api):
    """Ids come back as strings; a caller's int must not read as a change."""
    api.get("/rwidgets/5").respond(json={"data": {"id": 5, "name": "42"}})
    plan = RequestWidgets(client).prepare_patch(5, name=42)
    assert plan.changes == []


def test_prepare_patch_float_and_numeric_string_are_same(client, api):
    api.get("/rwidgets/5").respond(json={"data": {"id": 5, "name": "1"}})
    plan = RequestWidgets(client).prepare_patch(5, name=1.0)
    assert plan.changes == []


def test_prepare_patch_bool_and_string_true_is_a_change(client, api):
    """Booleans must not fall into the numeric/string equivalence."""
    api.get("/rwidgets/5").respond(json={"data": {"id": 5, "name": "True"}})
    plan = RequestWidgets(client).prepare_patch(5, name=True)
    assert plan.changes == [Change(field="name", old="True", new=True)]


def test_prepare_patch_list_of_numeric_strings_is_not_a_change(client, api):
    """A list of ids as strings must match the same ids supplied as ints."""
    api.get("/rwidgets/5").respond(json={"data": {"id": 5, "tags": ["1", "2"]}})
    plan = RequestWidgets(client).prepare_patch(5, tags=[1, 2])
    assert plan.changes == []


def test_prepare_patch_list_with_different_values_is_a_change(client, api):
    api.get("/rwidgets/5").respond(json={"data": {"id": 5, "tags": ["1", "3"]}})
    plan = RequestWidgets(client).prepare_patch(5, tags=["1", "2"])
    assert plan.changes == [Change(field="tags", old=["1", "3"], new=["1", "2"])]


def test_prepare_patch_requires_request_fields(client, api):
    """A resource with no allowlist has no base for prepare_patch to merge over."""
    with pytest.raises(NotImplementedError):
        Widgets(client).prepare_patch(5, name="x")
    assert not api.calls


def test_prepare_patch_propagates_not_found(client, api):
    api.get("/rwidgets/5").respond(status_code=404)
    with pytest.raises(NotFoundError):
        RequestWidgets(client).prepare_patch(5, name="new")


def test_prepare_patch_makes_no_write(client, api):
    api.get("/rwidgets/5").respond(json={"data": {"id": 5, "name": "old"}})
    RequestWidgets(client).prepare_patch(5, name="new")
    assert [c.request.method for c in api.calls] == ["GET"]


def test_patch_puts_merged_body(client, api):
    api.get("/rwidgets/5").respond(json={"data": {"id": 5, "name": "old"}})
    route = api.put("/rwidgets/5").respond(json={"data": {"id": 5, "name": "new"}})
    made = RequestWidgets(client).patch(5, name="new")
    assert made.name == "new"
    assert json.loads(route.calls.last.request.content) == {"name": "new"}


def test_patch_plan_exported():
    import get_connected_client

    assert get_connected_client.PatchPlan is PatchPlan
    assert get_connected_client.Change is Change


def test_id_helpers():
    """The wire convention, in one place: ids go over as strings."""
    assert _id_str(None) is None
    assert _id_str(Tag(id=None, name="a")) is None
    assert _id_str(Tag(id=0, name="a")) == "0"  # 0 is a valid id
    assert _id_strs(None) == []
    assert _id_strs([]) == []
    assert _id_strs([Tag(id=1), Tag(id=None), Tag(id=2)]) == ["1", "2"]
    assert _names(None) == []
    assert _names([Tag(name="a"), Tag(name=""), Tag(name=None)]) == ["a"]


def test_prepare_patch_reports_missing_required_without_refusing(client, api):
    """Advisory only: the body is still built and would still be sent."""
    api.get("/rwidgets/5").respond(json={"data": {"id": 5}})
    plan = RequestWidgets(client).prepare_patch(5)
    assert plan.missing_required == ["name"]
    assert plan.body == {}


def test_prepare_patch_reports_no_missing_required_when_present(client, api):
    """A required field the fetched row already carries is not flagged."""
    api.get("/rwidgets/5").respond(json={"data": {"id": 5, "name": "a"}})
    assert RequestWidgets(client).prepare_patch(5).missing_required == []


def test_supplied_field_clears_missing_required(client, api):
    """Computed against ``body``, not ``current``: a supplied field counts."""
    api.get("/rwidgets/5").respond(json={"data": {"id": 5}})
    assert RequestWidgets(client).prepare_patch(5, name="a").missing_required == []


#: (resource, model, read attribute, the nested shape, the key it would derive)
ID_DERIVED = [
    (Needs, Need, "agency", {"agency_name": "HH"}, "agency_id"),
    (Needs, Need, "initiative", {"init_title": "Spring"}, "initiative_id"),
    (Needs, Need, "groups", [{"group_title": "Rotary"}], "groups"),
    (Hours, Hour, "user", {"user_fname": "Ada"}, "user_id"),
    (Hours, Hour, "groups", [{"group_title": "Rotary"}], "group_ids"),
    (Responses, Response, "need", {"need_title": "Cleanup"}, "need_id"),
    (Responses, Response, "user", {"user_fname": "Ada"}, "user_id"),
    (Responses, Response, "shift", {"start": "2024-03-01 08:00:00"}, "schedule_ids"),
    (Responses, Response, "team", {"team_name": "Crew"}, "team_id"),
]


@pytest.mark.parametrize(
    ("resource", "model", "attr", "nested", "key"),
    ID_DERIVED,
    ids=[f"{r.__name__}.{a}" for r, _, a, _, _ in ID_DERIVED],
)
def test_nested_object_without_an_id_derives_no_key(
    client, resource, model, attr, nested, key
):
    """A nested object the API returned without an id yields no derived key.

    Omitting the key leaves the server's value alone; guessing one would be
    worse than the 422 a missing required field earns. The list-valued cases
    are the exception: the attribute is present, so the key is emitted as
    ``[]``, the documented "clear the list" semantics rather than absence.
    """
    body = resource(client).to_request(model.model_validate({attr: nested}))
    if isinstance(nested, list):
        assert body[key] == []
    else:
        assert key not in body


def test_wire_stringifies_ints_and_walks_lists():
    """The one wire convention: ints become strings, lists are walked."""
    assert _wire(4) == "4"
    assert _wire(True) is True
    assert _wire(1.5) == 1.5
    assert _wire("x") == "x"
    assert _wire([1, "2", [3], True]) == ["1", "2", ["3"], True]


def test_prepare_patch_wires_supplied_ints_and_id_lists(client, api):
    """Supplied fields go through the same int->str pass as fetched ones,
    so a merged body never mixes a JSON number with the spec's string ids."""
    api.get("/rwidgets/5").respond(json={"data": {"id": 5, "name": "old"}})
    plan = RequestWidgets(client).prepare_patch(5, name=42, tags=[7, "8"])
    assert plan.body == {"name": "42", "tags": ["7", "8"]}
    assert plan.changes == [
        Change(field="name", old="old", new="42"),
        Change(field="tags", old=None, new=["7", "8"]),
    ]
