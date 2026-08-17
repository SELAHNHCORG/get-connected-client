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
    assert client.read_only is True
    with pytest.raises(exc.ReadOnlyError):
        client.request("DELETE", "/users/1")
    assert not api.calls


def test_env_read_only_cannot_unblock_constructor_flag(monkeypatch, api):
    """GALAXY_READ_ONLY=0 must never unblock a client built read_only=True."""
    monkeypatch.setenv("GALAXY_READ_ONLY", "0")
    client = GalaxyClient(api_key="k", base_url=BASE, read_only=True)
    assert client.read_only is True
    with pytest.raises(exc.ReadOnlyError):
        client.request("POST", "/users", json={"user_fname": "x"})
    assert not api.calls


def test_write_reaches_wire_when_not_read_only(client, api):
    """The positive path: a permitted write is sent verbatim and parsed."""
    route = api.post("/users").respond(json={"data": {"id": 7}})
    assert client.request("POST", "/users", json={"user_fname": "x"}) == {
        "data": {"id": 7}
    }
    assert client.read_only is False
    assert route.calls.last.request.method == "POST"
    assert b'"user_fname"' in route.calls.last.request.content
    assert b'"x"' in route.calls.last.request.content


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


def test_post_is_not_retried_on_5xx(client, api, monkeypatch):
    """A POST may already have committed: never fire it twice on a 5xx."""
    monkeypatch.setattr("time.sleep", lambda s: pytest.fail("POST must not back off"))
    route = api.post("/users").respond(status_code=500)
    with pytest.raises(exc.GalaxyHTTPError):
        client.request("POST", "/users", json={"user_fname": "x"})
    assert route.call_count == 1


def test_post_is_retried_on_429(client, api, monkeypatch):
    """A 429 was rejected, not processed, so replaying it is safe."""
    monkeypatch.setattr("time.sleep", lambda s: None)
    route = api.post("/users")
    route.side_effect = [
        httpx.Response(429),
        httpx.Response(200, json={"data": {"id": 7}}),
    ]
    assert client.request("POST", "/users", json={"user_fname": "x"}) == {
        "data": {"id": 7}
    }
    assert route.call_count == 2


def test_retry_after_header_honored(client, api, monkeypatch):
    slept = []
    monkeypatch.setattr("time.sleep", slept.append)
    route = api.get("/causes")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "7"}),
        httpx.Response(200, json={"data": []}),
    ]
    assert client.get_data("/causes") == []
    assert slept == [7.0]


def test_retry_after_unparseable_falls_back_to_backoff(client, api, monkeypatch):
    slept = []
    monkeypatch.setattr("time.sleep", slept.append)
    route = api.get("/causes")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"}),
        httpx.Response(200, json={"data": []}),
    ]
    assert client.get_data("/causes") == []
    assert slept == [0.5]


def test_retry_after_is_clamped(client, api, monkeypatch):
    slept = []
    monkeypatch.setattr("time.sleep", slept.append)
    route = api.get("/causes")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "86400"}),
        httpx.Response(200, json={"data": []}),
    ]
    assert client.get_data("/causes") == []
    assert slept == [60.0]


def test_connection_error_wrapped_after_retries(api, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    client = GalaxyClient(api_key="k", base_url=BASE, retries=2)
    route = api.get("/causes")
    route.side_effect = httpx.ConnectError("boom")
    with pytest.raises(exc.GalaxyConnectionError) as info:
        client.get_data("/causes")
    assert "boom" in str(info.value)
    assert route.call_count == 3  # original + 2 retries


def test_connection_error_then_success(client, api, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    route = api.get("/causes")
    route.side_effect = [
        httpx.ConnectError("boom"),
        httpx.Response(200, json={"data": [{"id": 1}]}),
    ]
    assert client.get_data("/causes") == [{"id": 1}]
    assert route.call_count == 2


def test_post_connection_error_is_not_retried(client, api, monkeypatch):
    """The write may have landed before the socket died: do not repeat it."""
    monkeypatch.setattr("time.sleep", lambda s: pytest.fail("POST must not back off"))
    route = api.post("/users")
    route.side_effect = httpx.ConnectError("boom")
    with pytest.raises(exc.GalaxyConnectionError):
        client.request("POST", "/users", json={"user_fname": "x"})
    assert route.call_count == 1


def test_empty_body_returns_none(client, api):
    api.get("/causes").respond(status_code=200, content=b"")
    assert client.request("GET", "/causes") is None


def test_non_json_body_returns_none(client, api):
    api.get("/causes").respond(status_code=200, text="<html>oops</html>")
    assert client.request("GET", "/causes") is None


def test_unwrap_passes_through_payload_without_data_key(client, api):
    api.get("/causes").respond(json={"id": 1, "name": "x"})
    assert client.get_data("/causes") == {"id": 1, "name": "x"}


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


def test_paginate_single_object_payload(client, api):
    """A non-list ``data`` payload still yields its one row."""
    api.get("/hours").respond(json={"data": {"id": 1, "hours": 2}})
    assert list(client.paginate("/hours", per_page=3)) == [{"id": 1, "hours": 2}]


def test_paginate_drops_overlapping_rows(client, api):
    """Pages that partially overlap must not yield the same row twice."""
    route = api.get("/hours")
    route.side_effect = [
        httpx.Response(200, json={"data": [{"id": 1}, {"id": 2}, {"id": 3}]}),
        httpx.Response(200, json={"data": [{"id": 2}, {"id": 3}, {"id": 4}]}),
        httpx.Response(200, json={"data": [{"id": 5}]}),
    ]
    rows = list(client.paginate("/hours", per_page=3))
    assert [r["id"] for r in rows] == [1, 2, 3, 4, 5]


def test_paginate_honors_caller_supplied_since_id(client, api):
    """A caller's since_id seeds the cursor and filters the first page."""
    route = api.get("/hours").respond(json={"data": [{"id": 5}, {"id": 6}]})
    rows = list(client.paginate("/hours", {"since_id": "5"}, per_page=3))
    assert [r["id"] for r in rows] == [6]
    assert route.calls.last.request.url.params["since_id"] == "5"


def test_paginate_tolerates_non_numeric_ids(client, api):
    """A row whose id will not parse is passed through, not fatal."""
    route = api.get("/hours").respond(json={"data": [{"id": "abc"}]})
    assert list(client.paginate("/hours", per_page=3)) == [{"id": "abc"}]
    assert route.call_count == 1


def test_paginate_floors_per_page(client, api):
    """A nonsense per_page cannot make every page look full."""
    route = api.get("/hours").respond(json={"data": [{"id": 1}]})
    assert [r["id"] for r in client.paginate("/hours", per_page=0)] == [1]
    assert route.calls.last.request.url.params["per_page"] == "1"


def test_context_manager_closes():
    c = GalaxyClient(api_key="k", base_url=BASE)
    with c:
        inner = c.http  # force creation
    assert inner.is_closed
