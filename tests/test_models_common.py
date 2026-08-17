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
