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
    :meth:`~get_connected_client.resources.base.ListMixin.list` -- ``/agencies``
    defines no filters of its own beyond those.

    .. note::
       ``agency_contacts`` is a list of strings on ``GET`` but a single
       string on ``PUT``, and the spec does not say how the two relate.
       Sending the list back would be rejected or would mangle the field,
       so :meth:`to_request` never carries it and a merged update sends it
       absent -- which may clear it on the server. Pass
       ``agency_contacts="..."`` explicitly to :meth:`patch` to set or
       preserve it.
    """

    path = "/agencies"
    model = Agency
    request_fields = frozenset(
        {
            "agency_address",
            "agency_address2",
            "agency_city",
            "agency_comments",
            "agency_contact",
            "agency_contact_title",
            "agency_contacts",
            "agency_ein",
            "agency_email",
            "agency_facebook_link",
            "agency_fax",
            "agency_instagram_link",
            "agency_link",
            "agency_linkedin_link",
            "agency_mission",
            "agency_name",
            "agency_news",
            "agency_partner",
            "agency_phone",
            "agency_phone_extension",
            "agency_postal",
            "agency_state",
            "agency_status",
            "agency_twitter_link",
            "agency_url",
            "agency_video",
            "agency_youtube_link",
        }
    )

    def to_request(self, obj: Agency) -> dict[str, Any]:
        """Filter a fetched agency to the shape ``PUT /agencies/{id}`` wants.

        The request schema is a subset of the read object, so the base
        filter does nearly all the work. The one exception is
        ``agency_contacts``, which is **left out** -- see the class note.
        The three required write fields (``agency_name``, ``agency_status``,
        ``agency_postal``) are all on the read object; a fetched agency
        missing one yields a body without it, so supply it explicitly to
        :meth:`patch` in that case.

        :param obj: the fetched agency.
        :return: the request body.
        """
        body = super().to_request(obj)
        body.pop("agency_contacts", None)
        return body

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
