"""Read VolunteerLocal volunteer records off disk.

Some volunteers are tracked in `VolunteerLocal <https://volunteerlocal.com>`_
rather than (or as well as) Galaxy Digital, and VolunteerLocal has no API we
can call: what it offers is a CSV export, which some sites then load into a
local database. Both are supported here, so a report can put the two systems
side by side -- see ``galaxy reports attendance --local``.

Two shapes are read:

* a **sqlite database** (``.sqlite3``, ``.sqlite``, ``.db``) holding the
  ``selah_vol_db_volunteerrecord`` table an internal Django app writes, and
* a **CSV export** (``.csv``) taken straight out of VolunteerLocal, in
  either of the two variants it produces -- the full volunteer database, and
  the per-signup export, which carries the same totals but no shift dates.

Every number here is a **lifetime** total. Neither export has per-date rows,
so nothing in this module can be narrowed to a period; callers must say so
rather than let the figures read as if they were.

Only the standard library is used -- :mod:`sqlite3` and :mod:`csv` -- and
nothing is ever written: the database is opened read-only.
"""

from __future__ import annotations

import csv
import math
import sqlite3
import urllib.parse
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import LocalDataError

#: File suffixes read as a sqlite database.
SQLITE_SUFFIXES = frozenset({".sqlite3", ".sqlite", ".db"})

#: The table the internal Django app ("selah_vol_stats") keeps records in.
TABLE = "selah_vol_db_volunteerrecord"

#: Columns selected from :data:`TABLE`, named explicitly: the real table has
#: many more, and a ``SELECT *`` would break the moment a migration adds one.
_SELECT = (
    "SELECT email, first_name, last_name, total_shifts, total_hours, "
    "first_shift, last_shift "
    "FROM selah_vol_db_volunteerrecord"
)

#: CSV header -> field, lowercased for a case-tolerant lookup. Headers not
#: listed here are ignored: the exports carry a long tail of per-event
#: question columns that no report of ours reads.
_CSV_FIELDS = {
    "email": "email",
    "first name": "first_name",
    "last name": "last_name",
    "total shifts": "total_shifts",
    "total events": "total_events",
    "non-outreach": "non_outreach",
    "outreach": "outreach",
    "date of first shift": "first_shift",
    "date of last shift": "last_shift",
}

#: Hours headers, best first. VolunteerLocal reports hours two ways --
#: scheduled shift time and actual check-in time -- and only the first is
#: present for volunteers who never checked in, so it is the one we prefer.
_CSV_HOURS = ("total hours (by shift time)", "total hours (by check-in time)")


@dataclass
class LocalVolunteer:
    """One VolunteerLocal volunteer, with their lifetime totals.

    Every field is optional: the two export variants disagree about which
    columns exist (the signup export has no shift dates), the database has
    no outreach split at all, and any cell may simply be blank.
    """

    email: str | None
    first_name: str | None
    last_name: str | None
    total_shifts: int | None
    total_events: int | None
    total_hours: float | None
    outreach: int | None
    non_outreach: int | None
    first_shift: str | None
    last_shift: str | None


def _text(value: Any) -> str | None:
    """*value* as trimmed text, with blank (and non-scalar) treated as absent."""
    if value is None or isinstance(value, (list, tuple, dict)):
        return None
    text = str(value).strip()
    return text or None


def _int(value: Any) -> int | None:
    """*value* as an int, or None when it is blank or not a number.

    A junk cell costs the report that one figure; it never costs the whole
    file, which is the only outcome an operator could do nothing about.
    """
    text = _text(value)
    if text is None:
        return None
    try:
        return int(float(text))
    except (ValueError, OverflowError):
        return None


def _float(value: Any) -> float | None:
    """*value* as a float, or None when it is blank or not a number.

    ``inf``, ``-inf`` and ``nan`` all parse fine as floats but are not
    meaningful totals, so they are treated the same as junk text.
    """
    text = _text(value)
    if text is None:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def read_local_volunteers(path: Path) -> list[LocalVolunteer]:
    """Every volunteer record in the file at *path*.

    The reader is chosen by suffix: :data:`SQLITE_SUFFIXES` means the
    database, ``.csv`` means an export. An empty table or a header-only CSV
    is not an error -- it is a site that has not recorded anything yet -- and
    answers ``[]``.

    :raises LocalDataError: the file is missing, has a suffix we cannot read,
        lacks the expected table, or cannot be parsed.
    """
    path = Path(path)
    if not path.is_file():
        raise LocalDataError(f"no such VolunteerLocal file: {path}")
    suffix = path.suffix.lower()
    if suffix in SQLITE_SUFFIXES:
        return _read_sqlite(path)
    if suffix == ".csv":
        return _read_csv(path)
    raise LocalDataError(
        f"cannot tell what kind of file {path.name!r} is: expected a sqlite "
        "database (.sqlite3, .sqlite, .db) or a VolunteerLocal .csv export"
    )


def _read_sqlite(path: Path) -> list[LocalVolunteer]:
    """Read :data:`TABLE` out of the sqlite database at *path*.

    The connection is opened ``mode=ro``: this is somebody else's live
    database, and a report has no business being able to write to it.
    """
    try:
        connection = sqlite3.connect(
            f"file:{urllib.parse.quote(str(path))}?mode=ro", uri=True
        )
    except sqlite3.Error as error:
        raise LocalDataError(f"cannot open {path}: {error}") from error
    try:
        rows = connection.execute(_SELECT).fetchall()
    except sqlite3.Error as error:
        raise LocalDataError(
            f"cannot read table {TABLE} from {path}: {error}"
        ) from error
    finally:
        connection.close()
    return [
        LocalVolunteer(
            email=_text(row[0]),
            first_name=_text(row[1]),
            last_name=_text(row[2]),
            total_shifts=_int(row[3]),
            total_events=None,  # the table does not carry an event count
            total_hours=_float(row[4]),
            outreach=None,  # nor the outreach split -- CSV exports only
            non_outreach=None,
            first_shift=_text(row[5]),
            last_shift=_text(row[6]),
        )
        for row in rows
    ]


def _csv_row(cells: Mapping[str, Any]) -> LocalVolunteer:
    """One export row, already keyed by lowercased header."""
    fields: dict[str, Any] = {}
    for header, field in _CSV_FIELDS.items():
        fields[field] = cells.get(header)
    hours = next(
        (cells.get(header) for header in _CSV_HOURS if cells.get(header)), None
    )
    return LocalVolunteer(
        email=_text(fields["email"]),
        first_name=_text(fields["first_name"]),
        last_name=_text(fields["last_name"]),
        total_shifts=_int(fields["total_shifts"]),
        total_events=_int(fields["total_events"]),
        total_hours=_float(hours),
        outreach=_int(fields["outreach"]),
        non_outreach=_int(fields["non_outreach"]),
        first_shift=_text(fields["first_shift"]),
        last_shift=_text(fields["last_shift"]),
    )


def _read_csv(path: Path) -> list[LocalVolunteer]:
    """Read a VolunteerLocal CSV export.

    ``utf-8-sig`` because the exports start with a byte-order mark, which
    would otherwise glue itself to the first header and hide that column.
    Headers are matched case-insensitively and unknown ones are dropped, so
    the same reader handles both export variants and survives VolunteerLocal
    adding columns.
    """
    rows: list[LocalVolunteer] = []
    line = 0
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                return []
            for raw in reader:
                line = reader.line_num
                rows.append(
                    _csv_row(
                        {
                            header.strip().lower(): value
                            for header, value in raw.items()
                            if header
                        }
                    )
                )
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        where = f"{path} line {line + 1}" if line else str(path)
        raise LocalDataError(f"cannot read {where}: {error}") from error
    return rows
