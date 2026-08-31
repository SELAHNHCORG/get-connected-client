"""The ``/teams`` namespace: list/get/create/delete plus membership."""

from __future__ import annotations

from typing import Any

from ..models.teams import Team
from .base import CreateMixin, DeleteMixin, GetMixin, ListMixin, Resource


class Teams(
    ListMixin[Team],
    GetMixin[Team],
    CreateMixin[Team],
    DeleteMixin[Team],
    Resource[Team],
):
    """Teams -- a group of volunteers responding together to a single need.

    This namespace covers every ``/teams`` endpoint in ``doc/api.yml`` -- 3
    of 3 paths, 6 of 6 operations, full coverage, nothing excluded. They
    group as:

    * **CRUD**, minus update -- :meth:`list`, :meth:`get`, :meth:`create`,
      :meth:`delete`, inherited from the mixins. There is no
      ``UpdateMixin``: the spec defines no ``PUT /teams/{id}``.
    * **Membership** -- :meth:`add_member`/:meth:`remove_member`.

    :meth:`list` accepts ``show_inactive`` in addition to the standard paging
    filters -- see :meth:`~get_connected_client.resources.base.ListMixin.list`.
    """

    path = "/teams"
    model = Team

    # -- members ------------------------------------------------------

    def add_member(self, id: int, member: int, *, sch_id: int | None = None) -> Any:
        """Attach *member* (a user id) to this team.

        *sch_id* -- a schedule id -- is the one optional field of the
        spec's ``teamMemberAttachRequest`` body; omitted, an empty JSON
        object is still sent since the endpoint marks the body required.
        """
        body: dict[str, Any] = {}
        if sch_id is not None:
            body["sch_id"] = sch_id
        return self._client.request("POST", self._url(id, "member", member), json=body)

    def remove_member(self, id: int, member: int) -> Any:
        """Detach *member* (a user id) from this team."""
        return self._client.request("DELETE", self._url(id, "member", member))
