import httpx
import pytest

from galaxy_digital_cli import exceptions as exc
from galaxy_digital_cli.client import GalaxyClient

from .conftest import BASE


def test_missing_key(monkeypatch):
    monkeypatch.delenv("GALAXY_API_KEY", raising=False)
    with pytest.raises(exc.MissingAPIKeyError):
        GalaxyClient(api_key=None, base_url=BASE)


def test_auth_header_and_unwrap(client, api):
    route = api.get("/causes").respond(json={"data": [{"id": 1, "name": "x"}]})
    assert client.get_data("/causes") == [{"id": 1, "name": "x"}]
    assert route.calls.last.request.headers["Authorization"] == "test-key"


def test_server_alias():
    c = GalaxyClient(api_key="k", base_url="ca")
    assert c.base_url == "https://ca.volunteerapi.com/api"


@pytest.mark.parametrize(
    "status,klass",
    [(401, exc.AuthError), (404, exc.NotFoundError), (422, exc.ValidationFailedError)],
)
def test_error_mapping(client, api, status, klass):
    api.get("/users/9").respond(status_code=status, json={"error": "nope"})
    with pytest.raises(klass):
        client.get_data("/users/9")


def test_read_only_blocks_before_request(api):
    client = GalaxyClient(api_key="k", base_url=BASE, read_only=True)
    with pytest.raises(exc.ReadOnlyError):
        client.request("POST", "/users", json={"user_fname": "x"})
    assert not api.calls


def test_env_read_only_overrides(monkeypatch, client, api):
    monkeypatch.setenv("GALAXY_READ_ONLY", "1")
    with pytest.raises(exc.ReadOnlyError):
        client.request("DELETE", "/users/1")
    assert not api.calls


def test_read_only_guards_raw_http_access(api):
    """Defense in depth: bypassing request() via .http is still blocked."""
    client = GalaxyClient(api_key="k", base_url=BASE, read_only=True)
    with pytest.raises(exc.ReadOnlyError):
        client.http.post("/users", json={"user_fname": "x"})
    assert not api.calls
    # reads through the same escape hatch are untouched
    api.get("/causes").respond(json={"data": []})
    assert client.http.get("/causes").status_code == 200


def test_retry_then_success(client, api, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    route = api.get("/causes")
    route.side_effect = [
        httpx.Response(500),
        httpx.Response(429),
        httpx.Response(200, json={"data": []}),
    ]
    assert client.get_data("/causes") == []
    assert route.call_count == 3


def test_retry_exhausted(api, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    client = GalaxyClient(api_key="k", base_url=BASE, retries=1)
    api.get("/causes").respond(status_code=500)
    with pytest.raises(exc.GalaxyHTTPError):
        client.get_data("/causes")


def test_paginate(client, api):
    page1 = {"data": [{"id": i} for i in range(1, 4)]}
    page2 = {"data": [{"id": 4}]}
    route = api.get("/hours")
    route.side_effect = [
        httpx.Response(200, json=page1),
        httpx.Response(200, json=page2),
    ]
    rows = list(client.paginate("/hours", per_page=3))
    assert [r["id"] for r in rows] == [1, 2, 3, 4]
    assert route.calls[1].request.url.params["since_id"] == "3"


def test_paginate_stops_when_cursor_does_not_advance(client, api):
    """A server that ignores since_id must not loop us forever."""
    page = {"data": [{"id": i} for i in range(1, 4)]}
    route = api.get("/hours").respond(json=page)
    rows = list(client.paginate("/hours", per_page=3))
    assert [r["id"] for r in rows] == [1, 2, 3]
    assert route.call_count == 2  # one probe past the first page, then stop


def test_paginate_stops_when_rows_have_no_ids(client, api):
    """A full page with no usable cursor ends iteration rather than looping."""
    route = api.get("/hours").respond(json={"data": [{"name": "a"}] * 3})
    assert len(list(client.paginate("/hours", per_page=3))) == 3
    assert route.call_count == 1


def test_paginate_clamps_per_page_to_api_max(client, api):
    route = api.get("/hours").respond(json={"data": []})
    list(client.paginate("/hours", per_page=10_000))
    assert route.calls.last.request.url.params["per_page"] == "150"


def test_paginate_404_is_empty(client, api):
    api.get("/hours").respond(status_code=404)
    assert list(client.paginate("/hours")) == []


def test_context_manager_closes():
    c = GalaxyClient(api_key="k", base_url=BASE)
    with c:
        _ = c.http  # force creation
    assert c._http is None
