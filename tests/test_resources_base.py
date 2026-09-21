import json

from get_connected_client.models.common import Tag
from get_connected_client.resources.base import (
    Change,
    CreateMixin,
    DeleteMixin,
    GetMixin,
    ListMixin,
    PatchPlan,
    Resource,
    UpdateMixin,
)


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
    """Widgets with a request allowlist: `name` is writable, `id` is not."""

    path = "/rwidgets"
    request_fields = frozenset({"name"})


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


def test_prepare_patch_makes_no_write(client, api):
    api.get("/rwidgets/5").respond(json={"data": {"id": 5, "name": "old"}})
    RequestWidgets(client).prepare_patch(5, name="new")
    assert all(c.request.method == "GET" for c in api.calls)


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
