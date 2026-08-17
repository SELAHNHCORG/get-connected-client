"""Render rows as a rich table or raw JSON."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from typing import Any

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)


def _to_dict(row: Any) -> dict[str, Any]:
    """Coerce a row -- model, mapping or scalar -- into a flat dict."""
    if isinstance(row, BaseModel):
        return row.model_dump()
    return row if isinstance(row, dict) else {"value": row}


def output(
    state: Any, rows: Iterable[Any], columns: Sequence[str], title: str = ""
) -> None:
    """Print rows as a rich table (default) or raw JSON (``--json``)."""
    data = [_to_dict(r) for r in rows]
    if state.json_output:
        console.print_json(json.dumps(data, default=str))
        return
    table = Table(title=title or None)
    for col in columns:
        table.add_column(col)
    for item in data:
        table.add_row(*[str(item.get(c, "")) for c in columns])
    console.print(table)


def output_one(state: Any, row: Any) -> None:
    """Print a single record as a field/value table or raw JSON (``--json``)."""
    item = _to_dict(row)
    if state.json_output:
        console.print_json(json.dumps(item, default=str))
        return
    table = Table(show_header=False)
    table.add_column("field", style="bold")
    table.add_column("value")
    for key, value in item.items():
        table.add_row(key, str(value))
    console.print(table)
