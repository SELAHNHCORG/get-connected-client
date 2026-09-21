"""The ``/qualifications`` namespace: full CRUD plus the users sub-list."""

from __future__ import annotations

from ..models.qualifications import Qualification, QualificationUser
from .base import CreateMixin, DeleteMixin, GetMixin, ListMixin, Resource, UpdateMixin


class Qualifications(
    ListMixin[Qualification],
    GetMixin[Qualification],
    CreateMixin[Qualification],
    UpdateMixin[Qualification],
    DeleteMixin[Qualification],
    Resource[Qualification],
):
    """Qualifications -- credentials a volunteer can hold or be asked for.

    This namespace covers every ``/qualifications`` endpoint in
    ``doc/api.yml`` -- 3 of 3 paths, 6 of 6 operations, full coverage. They
    group as:

    * **CRUD** -- :meth:`list`, :meth:`get`, :meth:`create`, :meth:`update`,
      :meth:`delete`, inherited from the mixins.
    * **Membership** -- :meth:`users`, the volunteers who hold this
      qualification.
    """

    path = "/qualifications"
    model = Qualification
    request_fields = frozenset(
        {
            "qualification_approval",
            "qualification_correct_answer",
            "qualification_duration",
            "qualification_hide_from_registration",
            "qualification_level",
            "qualification_link_show",
            "qualification_link_text",
            "qualification_link_url",
            "qualification_options",
            "qualification_question",
            "qualification_required",
            "qualification_status",
            "qualification_title",
            "qualification_type",
        }
    )

    def users(self, id: int) -> list[QualificationUser]:
        """The users who hold this qualification."""
        return self._get_list(self._url(id, "users"), QualificationUser)
