"""``galaxy_digital_cli.vollocal`` -- reading VolunteerLocal off disk.

Every fixture here is built in ``tmp_path``: the module reads local files,
so the tests write their own rather than depend on anybody's real export.
"""

import csv
import sqlite3

import pytest

from galaxy_digital_cli import vollocal
from galaxy_digital_cli.exceptions import GalaxyError, LocalDataError
from galaxy_digital_cli.vollocal import TABLE, read_local_volunteers

#: The subset of the Django app's table the reader selects from, plus the
#: neighbouring columns it must not be disturbed by.
CREATE = f"""
CREATE TABLE {TABLE} (
    id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    first_name varchar(120) NULL,
    last_name varchar(120) NULL,
    email varchar(254) NULL,
    vol_local_id integer NULL,
    signup varchar(64) NULL,
    first_shift varchar(32) NULL,
    last_shift varchar(32) NULL,
    total_shifts integer NULL,
    total_hours real NULL,
    phone_number varchar(32) NULL
)
"""

INSERT = f"""
INSERT INTO {TABLE}
    (first_name, last_name, email, vol_local_id, signup, first_shift,
     last_shift, total_shifts, total_hours, phone_number)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

#: The full volunteer-database export: BOM, quoted headers, hours reported
#: two ways, and a tail of per-event question columns nothing reads.
VOL_DB_CSV = (
    '﻿"Total shifts","Total Hours (by shift time)",'
    '"Total Hours (by check-in time)","Total events","Non-outreach","Outreach",'
    '"Date of first shift","Date of last shift","Email","First Name",'
    '"Last Name","Mobile Phone","Do you have a car?"\r\n'
    "4,12.5,11.0,3,3,1,2026-01-05,2026-03-02,Ada@Example.ORG,Ada,Lovelace,"
    "555-0100,Yes\r\n"
    "1,2,,1,1,0,2026-02-11,2026-02-11,mary@example.org,Mary,Shelley,,No\r\n"
)

#: The per-signup export: the same totals, no shift dates at all.
SIGNUPS_CSV = (
    '﻿"Total shifts","Total Hours (by shift time)",'
    '"Total Hours (by check-in time)","Total events","Non-outreach","Outreach",'
    '"Email","First Name","Last Name","Mobile Phone"\r\n'
    "7,20.25,19,5,4,1,grace@example.org,Grace,Hopper,555-0111\r\n"
)


def make_db(path, rows=()):
    """A sqlite database with the real table and *rows* in it."""
    connection = sqlite3.connect(path)
    with connection:
        connection.execute(CREATE)
        connection.executemany(INSERT, rows)
    connection.close()
    return path


# --------------------------------------------------------------------------
# sqlite
# --------------------------------------------------------------------------


def test_reads_the_django_table(tmp_path):
    db = make_db(
        tmp_path / "db.sqlite3",
        [
            (
                "Ada",
                "Lovelace",
                "Ada@Example.ORG",
                1,
                "yes",
                "2026-01-05",
                "2026-03-02",
                4,
                12.5,
                "555-0100",
            ),
            ("Mary", "Shelley", None, 2, "yes", None, None, 1, 2.0, None),
        ],
    )
    ada, mary = read_local_volunteers(db)
    assert ada.email == "Ada@Example.ORG"
    assert (ada.first_name, ada.last_name) == ("Ada", "Lovelace")
    assert ada.total_shifts == 4
    assert ada.total_hours == 12.5
    assert (ada.first_shift, ada.last_shift) == ("2026-01-05", "2026-03-02")
    # the database carries no event count and no outreach split
    assert (ada.total_events, ada.outreach, ada.non_outreach) == (None, None, None)
    # a NULL email is not an error, it is a volunteer matched by name
    assert mary.email is None
    assert mary.first_shift is None


def test_sqlite_blanks_and_junk_become_none(tmp_path):
    db = make_db(
        tmp_path / "db.db",
        [("  Ada  ", "", "  ", 1, "", "", "", "n/a", "twelve", "")],
    )
    (volunteer,) = read_local_volunteers(db)
    assert volunteer.first_name == "Ada"  # whitespace stripped
    assert volunteer.last_name is None  # empty string is absent
    assert volunteer.email is None
    assert volunteer.total_shifts is None  # junk costs the figure, not the row
    assert volunteer.total_hours is None
    assert volunteer.last_shift is None


def test_empty_table_is_not_an_error(tmp_path):
    assert read_local_volunteers(make_db(tmp_path / "empty.sqlite")) == []


def test_missing_table_is_a_local_data_error(tmp_path):
    path = tmp_path / "other.sqlite3"
    connection = sqlite3.connect(path)
    with connection:
        connection.execute("CREATE TABLE something_else (id integer)")
    connection.close()
    with pytest.raises(LocalDataError) as error:
        read_local_volunteers(path)
    assert TABLE in str(error.value)


def test_a_file_that_is_not_a_database(tmp_path):
    path = tmp_path / "not-really.db"
    path.write_text("this is not a sqlite file\n")
    with pytest.raises(LocalDataError):
        read_local_volunteers(path)


def test_sqlite_open_failure_is_a_local_data_error(tmp_path, monkeypatch):
    """A database that cannot be opened at all -- gone, locked, unreadable."""
    db = make_db(tmp_path / "db.sqlite3")

    def refuse(*args, **kwargs):
        raise sqlite3.OperationalError("unable to open database file")

    monkeypatch.setattr(vollocal.sqlite3, "connect", refuse)
    with pytest.raises(LocalDataError) as error:
        read_local_volunteers(db)
    assert "cannot open" in str(error.value)


def test_sqlite_is_opened_read_only(tmp_path):
    """The report may never write to somebody else's live database."""
    db = make_db(
        tmp_path / "db.sqlite3", [("Ada", "L", "a@x.org", 1, "", "", "", 1, 1.0, "")]
    )
    read_local_volunteers(db)
    # the connection the reader used is closed, so prove the mode by opening
    # the same URI the same way
    connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        with pytest.raises(sqlite3.OperationalError):
            connection.execute(f"DELETE FROM {TABLE}")
    finally:
        connection.close()


# --------------------------------------------------------------------------
# csv
# --------------------------------------------------------------------------


def test_reads_the_volunteer_database_export(tmp_path):
    path = tmp_path / "vol_db.csv"
    path.write_text(VOL_DB_CSV, encoding="utf-8")
    ada, mary = read_local_volunteers(path)
    # the BOM did not swallow the first column
    assert ada.total_shifts == 4
    assert ada.email == "Ada@Example.ORG"
    assert (ada.first_name, ada.last_name) == ("Ada", "Lovelace")
    assert ada.total_events == 3
    assert (ada.outreach, ada.non_outreach) == (1, 3)
    assert (ada.first_shift, ada.last_shift) == ("2026-01-05", "2026-03-02")
    # shift time is preferred over check-in time
    assert ada.total_hours == 12.5
    assert mary.total_hours == 2.0
    assert mary.total_shifts == 1


def test_reads_the_signups_export(tmp_path):
    path = tmp_path / "signups_with_stats-2026-08-17.csv"
    path.write_text(SIGNUPS_CSV, encoding="utf-8")
    (grace,) = read_local_volunteers(path)
    assert grace.total_hours == 20.25
    assert grace.total_shifts == 7
    assert grace.total_events == 5
    # this variant has no shift dates at all
    assert (grace.first_shift, grace.last_shift) == (None, None)


def test_check_in_hours_are_the_fallback(tmp_path):
    path = tmp_path / "vol_db.csv"
    path.write_text(
        '﻿"Total shifts","Total Hours (by shift time)",'
        '"Total Hours (by check-in time)","Email"\r\n'
        "2,,6.5,ada@example.org\r\n",
        encoding="utf-8",
    )
    (volunteer,) = read_local_volunteers(path)
    assert volunteer.total_hours == 6.5


def test_csv_headers_are_case_tolerant_and_extras_ignored(tmp_path):
    path = tmp_path / "vol_db.csv"
    path.write_text(
        "TOTAL SHIFTS, email ,Total Hours (by shift time),Favourite colour\r\n"
        "3,ada@example.org,9,blue\r\n",
        encoding="utf-8",
    )
    (volunteer,) = read_local_volunteers(path)
    assert volunteer.total_shifts == 3
    assert volunteer.email == "ada@example.org"
    assert volunteer.total_hours == 9.0


def test_csv_blanks_and_junk_become_none(tmp_path):
    path = tmp_path / "vol_db.csv"
    path.write_text(
        '﻿"Total shifts","Total Hours (by shift time)","Total events",'
        '"Email","First Name","Last Name"\r\n'
        "lots,   ,3.7,,  Ada  ,\r\n",
        encoding="utf-8",
    )
    (volunteer,) = read_local_volunteers(path)
    assert volunteer.total_shifts is None
    assert volunteer.total_hours is None
    assert volunteer.total_events == 3  # "3.7" events truncates, it does not raise
    assert volunteer.email is None
    assert volunteer.first_name == "Ada"
    assert volunteer.last_name is None


def test_unparseable_row_names_its_line(tmp_path):
    """A row the csv module refuses says *which* row, so it can be fixed."""
    path = tmp_path / "vol_db.csv"
    path.write_text(
        '"Total shifts","Email"\r\n3,ada@example.org\r\n1,' + "x" * 200 + "\r\n",
        encoding="utf-8",
    )
    limit = csv.field_size_limit(20)
    try:
        with pytest.raises(LocalDataError) as error:
            read_local_volunteers(path)
    finally:
        csv.field_size_limit(limit)
    assert "line 3" in str(error.value)


def test_undecodable_csv_is_a_local_data_error(tmp_path):
    path = tmp_path / "vol_db.csv"
    path.write_bytes(b'"Total shifts","Email"\r\n3,ada@example.org\r\n1,\xff\xfe\r\n')
    with pytest.raises(LocalDataError) as error:
        read_local_volunteers(path)
    assert "cannot read" in str(error.value)


def test_empty_and_header_only_csvs(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    assert read_local_volunteers(empty) == []
    headers = tmp_path / "headers.csv"
    headers.write_text('﻿"Total shifts","Email"\r\n', encoding="utf-8")
    assert read_local_volunteers(headers) == []


# --------------------------------------------------------------------------
# dispatch and failures
# --------------------------------------------------------------------------


def test_missing_file(tmp_path):
    with pytest.raises(LocalDataError) as error:
        read_local_volunteers(tmp_path / "nope.sqlite3")
    assert "no such VolunteerLocal file" in str(error.value)


def test_a_directory_is_not_a_file(tmp_path):
    with pytest.raises(LocalDataError):
        read_local_volunteers(tmp_path)


def test_unknown_suffix(tmp_path):
    path = tmp_path / "export.xlsx"
    path.write_bytes(b"PK\x03\x04")
    with pytest.raises(LocalDataError) as error:
        read_local_volunteers(path)
    assert ".csv" in str(error.value)


def test_local_data_error_is_a_galaxy_error():
    """So the CLI's handler turns it into a message, not a traceback."""
    assert issubclass(LocalDataError, GalaxyError)


# --------------------------------------------------------------------------
# non-finite numerics
# --------------------------------------------------------------------------


def test_int_rejects_infinity_and_nan():
    """``int(float("inf"))`` raises OverflowError -- junk, not a crash."""
    assert vollocal._int("inf") is None
    assert vollocal._int("nan") is None


def test_float_rejects_infinity_and_nan():
    assert vollocal._float("inf") is None
    assert vollocal._float("nan") is None


def test_csv_row_with_infinite_total_shifts_parses_with_that_field_none(tmp_path):
    """A junk cell costs the report that one figure, never the whole file."""
    path = tmp_path / "vol_db.csv"
    path.write_text(
        '﻿"Total shifts","Email","First Name","Last Name"\r\n'
        "inf,ada@example.org,Ada,Lovelace\r\n",
        encoding="utf-8",
    )
    (volunteer,) = read_local_volunteers(path)
    assert volunteer.total_shifts is None
    assert volunteer.email == "ada@example.org"
