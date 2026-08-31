"""The ``/responses`` namespace: plain CRUD, no sub-resources."""

from __future__ import annotations

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
