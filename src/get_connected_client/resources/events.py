"""The ``/events`` namespace: plain CRUD, no sub-resources."""

from __future__ import annotations

from ..models.events import Event
from .base import (
    CreateMixin,
    DeleteMixin,
    GetMixin,
    ListMixin,
    Resource,
    UpdateMixin,
)


class Events(
    ListMixin[Event],
    GetMixin[Event],
    CreateMixin[Event],
    UpdateMixin[Event],
    DeleteMixin[Event],
    Resource[Event],
):
    """Agency events.

    This namespace covers every ``/events`` endpoint in ``doc/api.yml`` -- 2
    of 2 paths, 5 of 5 operations, full coverage. There are no sub-resources:
    just CRUD on the collection and the row -- :meth:`list`, :meth:`get`,
    :meth:`create`, :meth:`update`, :meth:`delete`, inherited from the
    mixins.

    .. note::
       Unlike most other list endpoints, ``/events`` does *not* accept
       ``show_inactive`` -- the spec's ``listEvents`` operation only takes
       ``per_page``, ``since_id``, ``since_created`` and ``since_updated``.
       :meth:`list` still inherits the parameter from
       :class:`~get_connected_client.resources.base.ListMixin`, but passing it
       has no effect on the server; the CLI does not expose it for this
       resource.
    """

    path = "/events"
    model = Event
    request_fields = frozenset(
        {
            "event_address",
            "event_address2",
            "event_all_day",
            "event_area",
            "event_area_id",
            "event_capacity",
            "event_city",
            "event_comments",
            "event_contact",
            "event_country",
            "event_date_end",
            "event_date_start",
            "event_description",
            "event_email",
            "event_location",
            "event_phone",
            "event_postal",
            "event_rsvp",
            "event_state",
            "event_tags",
            "event_title",
        }
    )
