"""The ``/benchmarks`` namespace: full CRUD plus the users sub-list."""

from __future__ import annotations

from ..models.benchmarks import Benchmark
from ..models.common import UserMini
from .base import CreateMixin, DeleteMixin, GetMixin, ListMixin, Resource, UpdateMixin


class Benchmarks(
    ListMixin[Benchmark],
    GetMixin[Benchmark],
    CreateMixin[Benchmark],
    UpdateMixin[Benchmark],
    DeleteMixin[Benchmark],
    Resource[Benchmark],
):
    """Benchmarks -- service milestones volunteers can earn.

    This namespace covers every ``/benchmarks`` endpoint in ``doc/api.yml``
    -- 3 of 3 paths, 6 of 6 operations, full coverage. They group as:

    * **CRUD** -- :meth:`list`, :meth:`get`, :meth:`create`, :meth:`update`,
      :meth:`delete`, inherited from the mixins.
    * **Membership** -- :meth:`users`, the volunteers who have earned this
      benchmark. The spec answers with ``userMiniObject`` rows, not the
      full ``benchmarkMiniObject``-flavored user -- confirmed against
      ``doc/api.yml``'s ``listBenchmarkUsersResponse``.
    """

    path = "/benchmarks"
    model = Benchmark

    def users(self, id: int) -> list[UserMini]:
        """The users who have earned this benchmark."""
        return self._get_list(self._url(id, "users"), UserMini)
