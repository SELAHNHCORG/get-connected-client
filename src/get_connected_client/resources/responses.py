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
        ``need.id`` becomes ``need_id`` and ``user.id`` becomes ``user_id``;
        ``shift.id`` becomes ``schedule_ids``, a one-element list: the read
        object reports a single ``shift`` while the request field is an
        array, so a merged update can only carry the one shift ``GET``
        returns. If a response covers more than one shift, pass
        ``schedule_ids=[...]`` explicitly to :meth:`patch` rather than
        relying on the merge. ``team.id`` becomes ``team_id`` when present.
        Ids are sent as strings.

        ``need_id`` and ``user_id`` can be recovered by fetching the missing
        need or user and passing the id explicitly if the nested object is
        absent. ``schedule_ids`` cannot: for a response to a need with no
        shifts, ``shift`` is null on the read object and there is no id to
        supply, so a merged update yields a body without the required
        ``schedule_ids`` and the API answers 422.

        .. warning::
           Passing ``schedule_ids=[]`` to :meth:`patch` for a shiftless
           response is untested against the live API; it may or may not be
           accepted in place of an omitted key.

        ``questions`` has no counterpart on the read object -- its ``answers``
        list is a different shape and is not carried -- so a merged update
        always sends it absent and cannot preserve a response's answers to
        custom questions; pass ``questions=`` explicitly to :meth:`patch` if
        the response has any.

        Dropped as read-only, with no request-schema counterpart at all:
        ``response_status``, ``response_phone``, ``response_address``,
        ``response_comments``, ``response_source``, ``response_date_updated``,
        ``answers``, ``agency``, ``initiative``, plus ids. ``response_phone``
        and ``response_address`` are simply absent from the request schema,
        so the API offers no way to update them.

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
