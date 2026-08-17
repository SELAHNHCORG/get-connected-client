from galaxy_digital_cli.models.common import Tag
from galaxy_digital_cli.resources.base import (
    CreateMixin,
    DeleteMixin,
    GetMixin,
    ListMixin,
    Resource,
    UpdateMixin,
)


class Widgets(ListMixin, GetMixin, CreateMixin, UpdateMixin, DeleteMixin, Resource):
    path = "/widgets"
    model = Tag


def test_list_parses_and_filters(client, api):
    route = api.get("/widgets").respond(json={"data": [{"id": 1, "name": "a"}]})
    rows = list(Widgets(client).list(show_inactive=True, since_created="2024-01-01"))
    assert isinstance(rows[0], Tag) and rows[0].name == "a"
    params = route.calls.last.request.url.params
    assert params["show_inactive"] == "Yes"
    assert params["since_created"] == "2024-01-01"


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


def test_sublist_404_empty(client, api):
    api.get("/widgets/1/things").respond(status_code=404)
    assert Widgets(client)._get_list("/widgets/1/things", Tag) == []
