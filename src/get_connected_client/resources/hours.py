"""The ``/hours`` namespace: plain CRUD, no sub-resources."""

from __future__ import annotations

from typing import Any

from ..models.hours import Hour
from .base import (
    CreateMixin,
    DeleteMixin,
    GetMixin,
    ListMixin,
    Resource,
    UpdateMixin,
)


class Hours(
    ListMixin[Hour],
    GetMixin[Hour],
    CreateMixin[Hour],
    UpdateMixin[Hour],
    DeleteMixin[Hour],
    Resource[Hour],
):
    """Volunteer hour records.

    This namespace covers every ``/hours`` endpoint in ``doc/api.yml`` -- 2
    of 2 paths, 5 of 5 operations, full coverage. There are no sub-resources:
    just CRUD on the collection and the row -- :meth:`list`, :meth:`get`,
    :meth:`create`, :meth:`update`, :meth:`delete`, inherited from the
    mixins.

    Unlike ``/events``, ``/hours`` list does accept ``show_inactive``::

        client.hours.list(show_inactive=True)

    .. note::
       ``response_id`` ties an hour to the response it was logged against
       and is **never returned by** ``GET`` -- the read object carries a
       ``need`` object instead, and ``need.id`` is not a response id.
       :meth:`to_request` therefore cannot carry it, and a merged update on a
       need-linked hour (``hour_type == "need"``) sends it absent, which may
       detach the hour from its response. Look the id up with
       ``client.needs.responses(need_id)`` and pass ``response_id=`` to
       :meth:`patch` to preserve the link.
    """

    path = "/hours"
    model = Hour
    request_fields = frozenset(
        {
            "group_ids",
            "hour_contact_details",
            "hour_contact_name",
            "hour_hours",
            "hour_location",
            "hour_miles",
            "hour_relationship",
            "hour_start",
            "hour_status",
            "response_id",
            "user_id",
        }
    )

    def to_request(self, obj: Hour) -> dict[str, Any]:
        """Flatten a fetched hour record into the shape ``PUT /hours/{id}`` wants.

        The request schema names the volunteer as ``user_id``, the groups as
        ``group_ids`` and the start as ``hour_start``; the read object nests
        the first two and calls the third ``hour_date_start``. Ids are sent
        as strings; a group with no id is skipped.

        ``response_id`` has no counterpart on the read object at all -- see
        the class docstring's note. ``hour_start`` is required by the PUT,
        so a fetched record with no ``hour_date_start`` yields a body
        without it and the caller must supply it.

        :param obj: the fetched hour record.
        :return: the request body.
        """
        body = super().to_request(obj)
        if obj.hour_date_start is not None:
            body["hour_start"] = obj.hour_date_start
        if obj.user is not None and obj.user.id is not None:
            body["user_id"] = str(obj.user.id)
        if obj.groups is not None:
            body["group_ids"] = [str(g.id) for g in obj.groups if g.id is not None]
        return body
