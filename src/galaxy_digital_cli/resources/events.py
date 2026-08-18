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
       :class:`~galaxy_digital_cli.resources.base.ListMixin`, but passing it
       has no effect on the server; the CLI does not expose it for this
       resource.
    """

    path = "/events"
    model = Event
