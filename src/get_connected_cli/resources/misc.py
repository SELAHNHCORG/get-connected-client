"""The ``/clusters`` namespace, plus the site's read-only lookup lists.

``Clusters`` is a small CRUD-minus-two namespace (agencies attach to
clusters; see :meth:`~get_connected_cli.resources.agencies.Agencies.clusters`).
``Lookups`` bundles four unrelated flat GET-only endpoints -- ``/causes``,
``/interests``, ``/impacts`` and ``/questions/registration`` -- that share
no ``{id}`` and no request shape, only the fact that each is a fixed list
the site defines up front.
"""

from __future__ import annotations

from ..models.common import Cause, Cluster, Impact, Interest, Question
from .base import CreateMixin, DeleteMixin, ListMixin, Resource


class Clusters(
    ListMixin[Cluster], CreateMixin[Cluster], DeleteMixin[Cluster], Resource[Cluster]
):
    """Clusters -- named groupings agencies attach to.

    This namespace covers every ``/clusters`` endpoint in ``doc/api.yml`` --
    2 of 2 paths, 3 of 3 operations, full coverage. There is no
    ``GetMixin``/``UpdateMixin``: the spec defines neither
    ``GET /clusters/{id}`` nor ``PUT /clusters/{id}``.

    ``GET /clusters`` declares no query parameters at all in the spec -- not
    even the usual paging trio ``per_page``/``since_id``/``since_created`` --
    unlike every other list endpoint in this API. :meth:`list` still accepts
    them, for the same call signature as every other namespace; any
    unrecognized parameter is simply not documented as doing anything.
    """

    path = "/clusters"
    model = Cluster


class Lookups(Resource[Cause]):
    """Read-only site-wide lookups, each with no ``{id}`` of its own.

    Covers ``/causes``, ``/interests``, ``/impacts`` and
    ``/questions/registration`` -- 4 of 4 paths, 4 of 4 operations, full
    coverage. ``path``/``model`` are unused placeholders required by
    :class:`~get_connected_cli.resources.base.Resource`: each method below
    names its own endpoint and return model directly, since the four
    endpoints have nothing in common but being flat, unpaginated, GET-only
    lists.
    """

    path = ""
    model = Cause

    def causes(self) -> list[Cause]:
        """The site's available causes."""
        return self._get_list("/causes", Cause)

    def interests(self) -> list[Interest]:
        """The site's available interests."""
        return self._get_list("/interests", Interest)

    def impacts(self) -> list[Impact]:
        """The site's available impact areas."""
        return self._get_list("/impacts", Impact)

    def registration_questions(self) -> list[Question]:
        """The site's custom registration questions."""
        return self._get_list("/questions/registration", Question)
