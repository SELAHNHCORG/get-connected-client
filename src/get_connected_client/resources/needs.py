"""The ``/needs`` namespace: CRUD plus every need sub-resource."""

from __future__ import annotations

from typing import Any

from ..models.common import Question
from ..models.needs import Need
from ..models.responses import Response
from .base import (
    CreateMixin,
    DeleteMixin,
    GetMixin,
    ListMixin,
    Resource,
    UpdateMixin,
    _id_str,
    _id_strs,
    _names,
)


class Needs(
    ListMixin[Need],
    GetMixin[Need],
    CreateMixin[Need],
    UpdateMixin[Need],
    DeleteMixin[Need],
    Resource[Need],
):
    """Needs (volunteer opportunities) and everything hanging off them.

    This namespace covers every ``/needs`` endpoint in ``doc/api.yml`` -- 8
    of 8 paths, 13 of 13 operations, full coverage, nothing excluded. They
    group as:

    * **CRUD** on the collection and the row -- :meth:`list`, :meth:`get`,
      :meth:`create`, :meth:`update`, :meth:`delete`, inherited from the
      mixins.
    * **Read-only** sub-resources -- :meth:`responses` and :meth:`questions`.
    * **Shifts** -- :meth:`add_shift` and :meth:`remove_shift`.
    * **Membership** sub-resources, add/remove only (the API has no read
      endpoint for either) -- :meth:`add_interest`/:meth:`remove_interest`
      and :meth:`add_qualification`/:meth:`remove_qualification`.

    :meth:`list` accepts the endpoint's own filters on top of the standard
    paging ones::

        client.needs.list(agency_id=9, need_status="active")

    Supported filters: ``agency_id``, ``need_title`` and ``need_status``.

    .. note::
       ``/needs/{id}/shifts`` does *not* use ``shiftRequestSchema`` (that
       schema's ``slots``/``start_date``/``start_time``/``duration`` fields
       are only used inside ``needRequestSchema``'s embedded ``shifts``
       array, i.e. when shifts are supplied as part of a need create/update).
       The dedicated endpoint has its own inline schema instead: a
       ``shifts`` array of ``{"start", "slots", "duration"}`` objects, with
       one combined ``start`` datetime rather than a separate date/time
       pair. :meth:`add_shift` keeps the friendlier separate
       ``start_date``/``start_time`` arguments and joins them into ``start``
       to match what the endpoint actually expects on the wire. For the
       same reason :meth:`to_request` never carries a fetched need's shifts
       into a merged update.
    """

    path = "/needs"
    model = Need
    request_fields = frozenset(
        {
            "accessible",
            "agency_id",
            "attributes",
            "event_id",
            "family_friendly",
            "groups",
            "initiative_id",
            "interests",
            "need_address",
            "need_address2",
            "need_allow_groups",
            "need_body",
            "need_city",
            "need_comments",
            "need_contact",
            "need_date",
            "need_date_close",
            "need_date_type",
            "need_hours",
            "need_hours_description",
            "need_impact_area",
            "need_latitude",
            "need_longitude",
            "need_postal",
            "need_public",
            "need_response_notify",
            "need_state",
            "need_status",
            "need_title",
            "need_type",
            "need_volunteers_needed",
            "outdoors",
            "shifts",
            "tags",
            "virtual_need",
        }
    )

    required_fields = frozenset(
        {
            "agency_id",
            "need_body",
            "need_date_type",
            "need_hours",
            "need_postal",
            "need_public",
            "need_status",
            "need_title",
        }
    )

    def to_request(self, obj: Need) -> dict[str, Any]:
        """Flatten a fetched need into the shape ``PUT /needs/{id}`` wants.

        The read object nests what the request schema takes flat:
        ``agency``/``initiative`` objects become ``agency_id``/
        ``initiative_id``, ``tags`` objects become their names, ``groups``
        objects become their ids. All ids are sent as strings.

        ``shifts`` is deliberately **left out**: the read shape
        (``shiftObject``) does not match ``shiftRequestSchema``, and
        resending shifts on every update risks duplicating rows that
        :meth:`add_shift`/:meth:`remove_shift` already manage. Pass
        ``shifts=[...]`` explicitly to :meth:`patch` if you mean to.

        ``needRequestSchema`` also has write-only fields with no counterpart
        on the read object -- ``virtual_need``, ``need_hours_description``,
        ``event_id``, ``interests`` and ``attributes`` -- so a merged update
        always sends them absent; pass any of these explicitly to
        :meth:`patch` if you rely on them. ``agency_id`` is required by the
        PUT, but a fetched need with no ``agency`` object yields a body
        without it, so the caller must supply ``agency_id=`` explicitly in
        that case too.

        :param obj: the fetched need.
        :return: the request body.
        """
        body = super().to_request(obj)
        body.pop("shifts", None)
        if (agency_id := _id_str(obj.agency)) is not None:
            body["agency_id"] = agency_id
        if (initiative_id := _id_str(obj.initiative)) is not None:
            body["initiative_id"] = initiative_id
        if obj.tags is not None:
            body["tags"] = _names(obj.tags)
        if obj.groups is not None:
            body["groups"] = _id_strs(obj.groups)
        return body

    # -- responses ----------------------------------------------------

    def responses(self, id: int) -> list[Response]:
        """The responses (sign-ups) to this need."""
        return self._get_list(self._url(id, "responses"), Response)

    # -- shifts ---------------------------------------------------------

    def add_shift(
        self, id: int, *, slots: int, start_date: str, start_time: str, duration: str
    ) -> Any:
        """Add a shift to this need.

        See the class docstring's note: the wire body is ``{"shifts":
        [{"start": ..., "slots": ..., "duration": ...}]}``, not the four
        flat fields of ``shiftRequestSchema``. *start_date* and *start_time*
        are joined with a space to build ``start``.
        """
        body = {
            "shifts": [
                {
                    "start": f"{start_date} {start_time}",
                    "slots": slots,
                    "duration": duration,
                }
            ]
        }
        return self._client.request("POST", self._url(id, "shifts"), json=body)

    def remove_shift(self, id: int, shift_id: int) -> Any:
        """Remove *shift_id* from this need."""
        return self._client.request("DELETE", self._url(id, "shifts", shift_id))

    # -- interests --------------------------------------------------------

    def add_interest(self, id: int, interest_id: int) -> Any:
        """Attach *interest_id* to this need."""
        return self._client.request("POST", self._url(id, "interests", interest_id))

    def remove_interest(self, id: int, interest_id: int) -> Any:
        """Detach *interest_id* from this need."""
        return self._client.request("DELETE", self._url(id, "interests", interest_id))

    # -- qualifications -----------------------------------------------------

    def add_qualification(self, id: int, qualification_id: int) -> Any:
        """Attach *qualification_id* to this need."""
        return self._client.request(
            "POST", self._url(id, "qualifications", qualification_id)
        )

    def remove_qualification(self, id: int, qualification_id: int) -> Any:
        """Detach *qualification_id* from this need."""
        return self._client.request(
            "DELETE", self._url(id, "qualifications", qualification_id)
        )

    # -- questions ------------------------------------------------------

    def questions(self, id: int) -> list[Question]:
        """The custom questions asked of volunteers responding to this need."""
        return self._get_list(self._url(id, "questions"), Question)
