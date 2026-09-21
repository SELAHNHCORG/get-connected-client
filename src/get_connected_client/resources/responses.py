"""The ``/responses`` namespace: plain CRUD, no sub-resources."""

from __future__ import annotations

from typing import Any

from ..models.responses import Response
from .base import (
    CreateMixin,
    DeleteMixin,
    GetMixin,
    ListMixin,
    Resource,
    UpdateMixin,
)


class Responses(
    ListMixin[Response],
    GetMixin[Response],
    CreateMixin[Response],
    UpdateMixin[Response],
    DeleteMixin[Response],
    Resource[Response],
):
    """Volunteer responses (sign-ups) to needs.

    This namespace covers every ``/responses`` endpoint in ``doc/api.yml`` --
    2 of 2 paths, 5 of 5 operations, full coverage. There are no
    sub-resources: just CRUD on the collection and the row -- :meth:`list`,
    :meth:`get`, :meth:`create`, :meth:`update`, :meth:`delete`, inherited
    from the mixins.

    :meth:`list` accepts ``show_inactive`` in addition to the standard paging
    filters -- see :meth:`~get_connected_client.resources.base.ListMixin.list`::

        client.responses.list(show_inactive=True)
    """

    path = "/responses"
    model = Response
    request_fields = frozenset(
        {
            "need_id",
            "questions",
            "response_date_added",
            "response_note",
            "schedule_ids",
            "team_id",
            "user_id",
        }
    )

    def to_request(self, obj: Response) -> dict[str, Any]:
        """Flatten a fetched response into the shape ``PUT /responses/{id}`` wants.

        The three required write fields all live inside nested read objects:
        ``need.id`` becomes ``need_id``, ``user.id`` becomes ``user_id`` and
        ``shift.id`` becomes ``schedule_ids`` (a one-element list; a response
        is tied to one shift). ``team.id`` becomes ``team_id`` when present.
        Ids are sent as strings. A fetched response missing any of those
        nested objects yields a body without that required field, so supply
        it explicitly to :meth:`patch` in that case.

        ``questions`` has no counterpart on the read object -- its ``answers``
        list is a different shape and is not carried -- so a merged update
        always sends it absent. The read-only ``response_status``,
        ``answers``, ``agency`` and ``initiative`` are dropped.

        :param obj: the fetched response.
        :return: the request body.
        """
        body = super().to_request(obj)
        if obj.need is not None and obj.need.id is not None:
            body["need_id"] = str(obj.need.id)
        if obj.user is not None and obj.user.id is not None:
            body["user_id"] = str(obj.user.id)
        if obj.shift is not None and obj.shift.id is not None:
            body["schedule_ids"] = [str(obj.shift.id)]
        if obj.team is not None and obj.team.id is not None:
            body["team_id"] = str(obj.team.id)
        return body
