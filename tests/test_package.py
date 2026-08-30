import get_connected_client


def test_version():
    assert get_connected_client.__title__ == "get-connected-client"


def test_public_exports():
    from get_connected_client import GalaxyClient  # noqa: F401

    assert get_connected_client.__all__
    for name in get_connected_client.__all__:
        assert hasattr(get_connected_client, name), f"missing export: {name}"
