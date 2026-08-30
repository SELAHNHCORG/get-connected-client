"""Models for the ``/benchmarks`` endpoints.

Field names are copied verbatim from ``doc/api.yml``; the API sends numeric
ids as strings and pydantic coerces them.
"""

from __future__ import annotations

from .base import GalaxyModel


class Benchmark(GalaxyModel):
    """benchmarkObject -- a service milestone volunteers can earn.

    ``update_at`` is spelled that way in the spec -- the API's own typo,
    kept verbatim so payloads round-trip (see also
    :class:`~get_connected_client.models.common.BenchmarkMini`, which carries
    the same typo).
    """

    id: int | None = None
    benchmark_status: str | None = None
    benchmark_title: str | None = None
    benchmark_icon: str | None = None
    benchmark_hours: str | None = None
    benchmark_date_start: str | None = None
    benchmark_date_end: str | None = None
    benchmark_approval_required: str | None = None
    benchmark_allow_indv_hours: str | None = None
    benchmark_group_id: int | None = None
    created_at: str | None = None
    update_at: str | None = None
