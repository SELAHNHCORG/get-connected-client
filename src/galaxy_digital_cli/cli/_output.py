"""Render rows as a rich table or raw JSON."""

from __future__ import annotations

import enum
import json
from collections.abc import Iterable, Sequence
from typing import Any

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)


class OutputFormat(str, enum.Enum):
    """How a command renders its result.

    Selected globally with ``--format`` (or ``GALAXY_FORMAT``); ``--json``
    is a shorthand for ``--format json``. Deriving from :class:`str` keeps
    the members usable wherever their wire value is wanted -- typer renders
    the choices in ``--help`` from them -- and leaves room for more
    renderers (csv, yaml, ...) without touching any call site.
    """

    TABLE = "table"
    JSON = "json"

    def __str__(self) -> str:
        return self.value


def _to_dict(row: Any) -> dict[str, Any]:
    """Coerce a row -- model, mapping or scalar -- into a flat dict."""
    if isinstance(row, BaseModel):
        return row.model_dump()
    return row if isinstance(row, dict) else {"value": row}


def output(
    state: Any, rows: Iterable[Any], columns: Sequence[str], title: str = ""
) -> None:
    """Print rows as a rich table (default) or raw JSON (``--format json``)."""
    data = [_to_dict(r) for r in rows]
    if state.format is OutputFormat.JSON:
        console.print_json(json.dumps(data, default=str))
        return
    table = Table(title=title or None)
    for col in columns:
        table.add_column(col)
    for item in data:
        table.add_row(*[str(item.get(c, "")) for c in columns])
    console.print(table)


def output_one(state: Any, row: Any) -> None:
    """Print one record as a field/value table or raw JSON (``--format json``)."""
    item = _to_dict(row)
    if state.format is OutputFormat.JSON:
        console.print_json(json.dumps(item, default=str))
        return
    table = Table(show_header=False)
    table.add_column("field", style="bold")
    # fold, not the default ellipsis: a value the operator needs to copy --
    # a session token above all -- must be printed in full, wrapped across
    # as many lines as it takes, never truncated to "eyJ0eXAi…".
    table.add_column("value", overflow="fold", no_wrap=False)
    for key, value in item.items():
        table.add_row(key, str(value))
    console.print(table)


def output_result(state: Any, result: Any = None) -> None:
    """Report the outcome of a write.

    Many write endpoints answer 204, or a bare message with nothing to
    render -- some as ``None``/``""``, others as an empty list. Under
    ``--format json`` those must still emit *something* parseable -- a
    script piping us into ``jq`` should never get an empty stdout on
    success -- so they print ``{"ok": true}``. When the API did return a
    model or dict, it is printed by :func:`output_one` as usual.
    """
    if result is None or result == "" or result == []:
        if state.format is OutputFormat.JSON:
            console.print_json(json.dumps({"ok": True}))
        else:
            console.print("[green]done[/]")
        return
    output_one(state, result)
