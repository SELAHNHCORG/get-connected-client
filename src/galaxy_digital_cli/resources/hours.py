"""The ``/hours`` namespace: plain CRUD, no sub-resources."""

from __future__ import annotations

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
    """

    path = "/hours"
    model = Hour
