"""The merged-update flow every ``update`` command shares.

The API's PUT is a full replacement, so a bare ``--data '{"x": 1}'`` is
rejected with 422 for every required field it lacks. Each ``update`` command
therefore hands its fields to :func:`run_update`, which fetches the record,
merges, shows the diff and sends the whole body -- unless ``--replace`` asks
for the raw PUT.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

import typer

from ..resources.base import PatchPlan
from ._confirm import confirm_patch, confirm_write, warn_missing_required
from ._output import OutputFormat, console, err_console, output_result

#: The ``--replace`` option, shared by every ``update`` command.
REPLACE = typer.Option(
    False,
    "--replace",
    help=(
        "Send only the given fields as the whole PUT body: no fetch, no "
        "merge. Required fields the body lacks are warned about, and the "
        "API rejects a body missing any."
    ),
)


class _Updatable(Protocol):
    """What :func:`run_update` needs from a resource namespace."""

    # A read-only property, not a bare annotation: the resources declare
    # ``required_fields`` as a ``ClassVar``, which satisfies this form but
    # not a protocol instance variable.
    @property
    def required_fields(self) -> frozenset[str]: ...

    def url(self, *parts: Any) -> str: ...
    def prepare_patch(self, id: int, **fields: Any) -> PatchPlan: ...
    def update(self, id: int, **fields: Any) -> Any: ...


def _no_changes(state: Any, message: str) -> None:
    """Report that nothing will be written, without writing anything.

    Under ``--format json`` a no-op still has to leave parseable stdout for
    whatever is downstream of the pipe, so it emits the same empty change
    list either way and keeps the human-readable *message* on stderr.
    """
    if state.format is OutputFormat.JSON:
        console.print_json(json.dumps({"changes": []}))
    else:
        err_console.print(message)


def run_update(
    state: Any, resource: _Updatable, id: int, fields: dict[str, Any], *, replace: bool
) -> None:
    """Confirm and send an update of *id* on *resource*.

    With *replace* false (the default) the record is fetched, *fields* are
    merged over it and only the changed fields are shown for confirmation;
    when nothing would change, nothing is written. With *replace* true,
    *fields* are shown and sent verbatim -- no fetch, no merge -- after a
    warning naming any required field the body lacks.

    :param resource: a namespace with ``required_fields``, ``url``,
        ``prepare_patch`` and ``update`` (any
        :class:`~get_connected_client.resources.base.UpdateMixin`).
    :raises typer.BadParameter: *fields* names ``id``; the row is chosen by
        the positional argument, and a body ``id`` would be sent as data.
    """
    if "id" in fields:
        raise typer.BadParameter(
            "must not set 'id'; the record is chosen by the ID argument",
            param_hint="--data",
        )
    if not fields:
        _no_changes(state, "[yellow]Nothing to update:[/] name at least one field.")
        return
    target = f"PUT {resource.url(id)}"
    if replace:
        # No fetch means no merged body to check, but the operator can still
        # be told which required fields this body is missing before it goes.
        warn_missing_required(
            PatchPlan(
                current={},
                body=fields,
                changes=[],
                missing_required=sorted(resource.required_fields - fields.keys()),
            )
        )
        confirm_write(state, target, fields)
        output_result(state, resource.update(id, **fields))
        return
    plan = resource.prepare_patch(id, **fields)
    if not plan.changes:
        _no_changes(
            state,
            "[yellow]No changes:[/] every supplied field already has that value.",
        )
        return
    confirm_patch(state, target, plan)
    output_result(state, resource.update(id, **plan.body))
