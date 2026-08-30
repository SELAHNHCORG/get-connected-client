import get_connected_cli


def test_version():
    assert get_connected_cli.__title__ == "get-connected-cli"


def test_public_exports():
    from get_connected_cli import GalaxyClient  # noqa: F401

    assert get_connected_cli.__all__
    for name in get_connected_cli.__all__:
        assert hasattr(get_connected_cli, name), f"missing export: {name}"
