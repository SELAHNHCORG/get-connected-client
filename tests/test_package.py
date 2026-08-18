import galaxy_digital_cli


def test_version():
    assert galaxy_digital_cli.__title__ == "galaxy-digital-cli"


def test_public_exports():
    from galaxy_digital_cli import GalaxyClient  # noqa: F401

    assert galaxy_digital_cli.__all__
    for name in galaxy_digital_cli.__all__:
        assert hasattr(galaxy_digital_cli, name), f"missing export: {name}"
