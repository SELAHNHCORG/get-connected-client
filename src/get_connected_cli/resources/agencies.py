"""The ``/agencies`` namespace: CRUD plus every agency sub-resource."""

from __future__ import annotations

from typing import Any

from ..models.agencies import Agency
from ..models.common import Cause, Cluster, Tag, UserMini
from .base import (
    CreateMixin,
    DeleteMixin,
    GetMixin,
    ListMixin,
    Resource,
    UpdateMixin,
)


class Agencies(
    ListMixin[Agency],
    GetMixin[Agency],
    CreateMixin[Agency],
    UpdateMixin[Agency],
    DeleteMixin[Agency],
    Resource[Agency],
):
    """Agencies and everything hanging off them.

    This namespace covers every ``/agencies`` endpoint in ``doc/api.yml`` --
    10 of 10 paths, 17 of 17 operations, full coverage, nothing excluded.
    They group as:

    * **CRUD** on the collection and the row -- :meth:`list`, :meth:`get`,
      :meth:`create`, :meth:`update`, :meth:`delete`, inherited from the
      mixins.
    * **Membership** sub-resources, each a read plus add/remove --
      :meth:`causes`, :meth:`clusters`, :meth:`managers` and :meth:`tags`.

    :meth:`list` accepts the endpoint's standard paging filters -- see
    :meth:`~get_connected_cli.resources.base.ListMixin.list` -- ``/agencies``
    defines no filters of its own beyond those.
    """

    path = "/agencies"
    model = Agency

    # -- causes -------------------------------------------------------

    def causes(self, id: int) -> list[Cause]:
        """The causes attached to this agency."""
        return self._get_list(self._url(id, "causes"), Cause)

    def add_cause(self, id: int, cause_id: int) -> Any:
        """Attach *cause_id* to this agency."""
        return self._client.request("POST", self._url(id, "causes", cause_id))

    def remove_cause(self, id: int, cause_id: int) -> Any:
        """Detach *cause_id* from this agency."""
        return self._client.request("DELETE", self._url(id, "causes", cause_id))

    # -- clusters -----------------------------------------------------

    def clusters(self, id: int) -> list[Cluster]:
        """The clusters attached to this agency."""
        return self._get_list(self._url(id, "clusters"), Cluster)

    def add_cluster(self, id: int, cluster_id: int) -> Any:
        """Attach *cluster_id* to this agency."""
        return self._client.request("POST", self._url(id, "clusters", cluster_id))

    def remove_cluster(self, id: int, cluster_id: int) -> Any:
        """Detach *cluster_id* from this agency."""
        return self._client.request("DELETE", self._url(id, "clusters", cluster_id))

    # -- managers -------------------------------------------------------

    def managers(self, id: int) -> list[UserMini]:
        """The users who manage this agency."""
        return self._get_list(self._url(id, "managers"), UserMini)

    def add_manager(self, id: int, user_id: int) -> Any:
        """Make *user_id* a manager of this agency."""
        return self._client.request("POST", self._url(id, "managers", user_id))

    def remove_manager(self, id: int, user_id: int) -> Any:
        """Remove *user_id* as a manager of this agency."""
        return self._client.request("DELETE", self._url(id, "managers", user_id))

    # -- tags -----------------------------------------------------------

    def tags(self, id: int) -> list[Tag]:
        """The tags on this agency."""
        return self._get_list(self._url(id, "tags"), Tag)

    def add_tags(self, id: int, tags: list[str]) -> Any:
        """Add *tags* -- names, not ids -- to this agency."""
        return self._client.request("POST", self._url(id, "tags"), json={"tags": tags})

    def remove_tag(self, id: int, tag_id: int) -> Any:
        """Remove the tag with this id from the agency."""
        return self._client.request("DELETE", self._url(id, "tags", tag_id))
