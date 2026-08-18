from galaxy_digital_cli import models


def test_extra_fields_survive():
    tag = models.Tag.model_validate({"id": "7", "name": "vip", "brand_new_field": "x"})
    assert tag.id == 7
    assert tag.model_dump()["brand_new_field"] == "x"


def test_common_models_exist():
    for name in [
        "Tag",
        "Cause",
        "Cluster",
        "Interest",
        "Impact",
        "Category",
        "Extra",
        "Question",
        "Shift",
        "TrackMini",
        "UserMini",
        "AgencyMini",
        "NeedMini",
        "GroupMini",
        "InitiativeMini",
        "TeamMini",
    ]:
        assert hasattr(models, name)


def test_user_mini_fields():
    u = models.UserMini.model_validate(
        {
            "id": 1,
            "domain_id": 2,
            "user_fname": "A",
            "user_lname": "B",
            "user_email": "a@b.co",
        }
    )
    assert u.user_email == "a@b.co"


def test_int_fields_tolerate_loose_api_strings():
    """Live regression: the API sends "" (and junk) where the spec says int."""
    shift = models.Shift.model_validate({"id": "7", "slots": ""})
    assert shift.slots is None
    assert models.Shift.model_validate({"slots": "unlimited"}).slots is None
    assert models.Shift.model_validate({"slots": "12"}).slots == 12
    assert models.Shift.model_validate({"slots": "3.0"}).slots == 3
    assert models.Shift.model_validate({"slots": 5}).slots == 5
    assert models.Shift.model_validate({"slots": None}).slots is None
    # str-typed fields keep their empty strings untouched
    assert models.Shift.model_validate({"start": ""}).start == ""


def test_need_parses_shift_with_blank_slots():
    """The exact payload shape that crashed `galaxy needs list` live."""
    from galaxy_digital_cli.models.needs import Need

    need = Need.model_validate(
        {"id": "1", "need_title": "Help out", "shifts": [{"id": "2", "slots": ""}]}
    )
    assert need.shifts is not None
    assert need.shifts[0].slots is None
