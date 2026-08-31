import pytest

from get_connected_client import exceptions as exc


@pytest.mark.parametrize(
    "status,klass",
    [
        (401, exc.AuthError),
        (403, exc.AuthError),
        (404, exc.NotFoundError),
        (422, exc.ValidationFailedError),
        (429, exc.RateLimitError),
        (500, exc.GalaxyHTTPError),
    ],
)
def test_for_status(status, klass):
    e = exc.GalaxyHTTPError.for_status(status, "boom")
    assert isinstance(e, klass)
    assert e.status_code == status
    assert "boom" in str(e)


def test_hierarchy():
    assert issubclass(exc.GalaxyHTTPError, exc.GalaxyError)
    assert issubclass(exc.ReadOnlyError, exc.GalaxyError)
    assert issubclass(exc.MissingAPIKeyError, exc.GalaxyError)
