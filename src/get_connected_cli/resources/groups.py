"""The ``/groups`` namespace: CRUD plus needs/users membership."""

from __future__ import annotations

from typing import Any

from ..models.groups import Group
from .base import (
    CreateMixin,
    DeleteMixin,
    GetMixin,
    ListMixin,
    Resource,
    UpdateMixin,
)


class Groups(
    ListMixin[Group],
    GetMixin[Group],
    CreateMixin[Group],
    UpdateMixin[Group],
    DeleteMixin[Group],
    Resource[Group],
):
    """User groups and everything hanging off them.

    This namespace covers every ``/groups`` endpoint in ``doc/api.yml`` -- 4
    of 4 paths, 9 of 9 operations, full coverage, nothing excluded. They
    group as:

    * **CRUD** on the collection and the row -- :meth:`list`, :meth:`get`,
      :meth:`create`, :meth:`update`, :meth:`delete`, inherited from the
      mixins.
    * **Membership**, add/remove only (the API has no dedicated read
      endpoint for either -- both live on the ``needs``/``users`` arrays of
      the group object itself) -- :meth:`add_need`/:meth:`remove_need` and
      :meth:`add_user`/:meth:`remove_user`.

    :meth:`list` accepts ``show_inactive`` in addition to the standard paging
    filters -- see :meth:`~get_connected_cli.resources.base.ListMixin.list`.
    """

    path = "/groups"
    model = Group

    # -- needs ----------------------------------------------------------

    def add_need(self, id: int, need_id: int) -> Any:
        """Attach *need_id* to this group."""
        return self._client.request("POST", self._url(id, "needs", need_id))

    def remove_need(self, id: int, need_id: int) -> Any:
        """Detach *need_id* from this group."""
        return self._client.request("DELETE", self._url(id, "needs", need_id))

    # -- users ------------------------------------------------------------

    def add_user(self, id: int, user_id: int) -> Any:
        """Attach *user_id* to this group."""
        return self._client.request("POST", self._url(id, "users", user_id))

    def remove_user(self, id: int, user_id: int) -> Any:
        """Detach *user_id* from this group."""
        return self._client.request("DELETE", self._url(id, "users", user_id))
