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
    _id_str,
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

    This namespace covers every ``/responses`` endpoint in ``doc/api.yml`` -- 2
    of 2 paths, 5 of 5 operations, full coverage. There are no sub-resources:
    just CRUD on the collection and the row --
    :meth:`~get_connected_client.resources.base.ListMixin.list`,
    :meth:`~get_connected_client.resources.base.GetMixin.get`,
    :meth:`~get_connected_client.resources.base.CreateMixin.create`,
    :meth:`~get_connected_client.resources.base.UpdateMixin.update`,
    :meth:`~get_connected_client.resources.base.DeleteMixin.delete`, inherited
    from the mixins.

    :meth:`~get_connected_client.resources.base.ListMixin.list` accepts
    ``show_inactive`` in addition to the standard paging filters::

        client.responses.list(show_inactive=True)

    .. note::
       Two ``PUT`` fields cannot be recovered from a fetched response. A
       response to a need with no shifts has ``shift`` null, so a merged
       update yields a body without the required ``schedule_ids`` and the
       API answers 422 -- there is no id to supply. And the read object's
       ``answers`` are a different shape from the request schema's
       ``questions``, so a merged update cannot preserve a response's
       answers to custom questions; pass ``questions=`` to
       :meth:`~get_connected_client.resources.base.UpdateMixin.patch`
       explicitly if the response has any.
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

    required_fields = frozenset(
        {
            "need_id",
            "schedule_ids",
            "user_id",
        }
    )

    def to_request(self, obj: Response) -> dict[str, Any]:
        """Flatten a fetched response into the shape ``PUT /responses/{id}`` wants.

        The three required write fields all live inside nested read objects:
        ``need.id`` becomes ``need_id`` and ``user.id`` becomes ``user_id``;
        ``shift.id`` becomes ``schedule_ids``, a one-element list: the read
        object reports a single ``shift`` while the request field is an array,
        so a merged update can only carry the one shift ``GET`` returns. If a
        response covers more than one shift, pass ``schedule_ids=[...]``
        explicitly to
        :meth:`~get_connected_client.resources.base.UpdateMixin.patch` rather
        than relying on the merge. ``team.id`` becomes ``team_id`` when
        present. Ids are sent as strings.

        ``response_date_added`` is carried deliberately: the spec says the
        server uses the current date when it is not provided, so omitting it
        from a merged update silently resets the sign-up date to now.

        ``need_id`` and ``user_id`` can be recovered by fetching the missing
        need or user and passing the id explicitly if the nested object is
        absent. ``schedule_ids`` cannot -- see the class note.

        .. warning::
           Passing ``schedule_ids=[]`` to
           :meth:`~get_connected_client.resources.base.UpdateMixin.patch` for a
           shiftless response is untested against the live API; it may or may
           not be accepted in place of an omitted key.

        ``questions`` has no counterpart on the read object -- see the class
        note.

        Dropped as read-only: ``response_status``, ``response_comments``,
        ``response_source``, ``response_date_updated``, ``answers``,
        ``agency``, ``initiative``, plus ids.

        Dropped as unsupported: ``response_phone`` and ``response_address``
        are returned by ``GET`` but appear nowhere in
        ``responseRequestSchema``, so the API offers no way to update them
        at all -- not through :meth:`to_request`, and not by passing them to
        :meth:`~get_connected_client.resources.base.UpdateMixin.patch`.

        :param obj: the fetched response.
        :return: the request body.
        """
        body = super().to_request(obj)
        if (need_id := _id_str(obj.need)) is not None:
            body["need_id"] = need_id
        if (user_id := _id_str(obj.user)) is not None:
            body["user_id"] = user_id
        if (shift_id := _id_str(obj.shift)) is not None:
            body["schedule_ids"] = [shift_id]
        if (team_id := _id_str(obj.team)) is not None:
            body["team_id"] = team_id
        return body
