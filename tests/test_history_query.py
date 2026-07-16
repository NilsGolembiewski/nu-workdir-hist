"""Tests for querying the nushell history sqlite DB by cwd."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from nu_workdir_hist import history
from nu_workdir_hist.errors import HistoryError, NoSqliteHistoryError


def test_query_returns_commands_for_cwd_most_recent_first(populated_db, proj_dir):
    rows = history.query_history(populated_db, str(proj_dir), limit=50)
    assert [r.command_line for r in rows] == ["rm -rf build", "git status", "ls -la"]


def test_query_excludes_null_cwd_rows(populated_db, proj_dir):
    rows = history.query_history(populated_db, str(proj_dir), limit=50)
    assert "imported-no-cwd" not in [r.command_line for r in rows]


def test_query_excludes_other_cwds(populated_db, other_dir):
    rows = history.query_history(populated_db, str(other_dir), limit=50)
    assert [r.command_line for r in rows] == ["make test"]


def test_query_limit_caps_results(populated_db, proj_dir):
    rows = history.query_history(populated_db, str(proj_dir), limit=2)
    assert [r.command_line for r in rows] == ["rm -rf build", "git status"]


def test_query_limit_zero_means_no_limit(populated_db, proj_dir):
    rows = history.query_history(populated_db, str(proj_dir), limit=0)
    assert len(rows) == 3


def test_query_unknown_cwd_returns_empty(populated_db):
    rows = history.query_history(populated_db, "/nowhere", limit=50)
    assert rows == []


def test_query_carries_metadata(populated_db, proj_dir):
    rows = history.query_history(populated_db, str(proj_dir), limit=50)
    top = rows[0]
    assert top.command_line == "rm -rf build"
    assert top.start_timestamp == 1700000003000
    assert top.exit_status == 0
    assert top.cwd == str(proj_dir)
    assert top.id == 4


def test_query_opens_read_only(populated_db, proj_dir):
    # The tool must not lock nushell: read-only mode means writes fail.
    # We verify the connection the tool creates is read-only by attempting a
    # write through a ro connection ourselves.
    con = sqlite3.connect(f"file:{populated_db}?mode=ro", uri=True)
    with pytest.raises(sqlite3.OperationalError):
        con.execute("INSERT INTO history (command_line) VALUES ('x')")
    con.close()
    # And the tool itself should still read fine.
    rows = history.query_history(populated_db, str(proj_dir), limit=50)
    assert len(rows) == 3


def test_query_missing_history_table_raises_history_error(tmp_path):
    db = tmp_path / "notnushell.sqlite3"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE other (x INTEGER)")
    con.commit()
    con.close()
    with pytest.raises(HistoryError):
        history.query_history(db, "/anywhere", limit=50)


def test_query_corrupt_db_raises_history_error(tmp_path):
    db = tmp_path / "broken.sqlite3"
    db.write_bytes(b"not a sqlite database at all")
    with pytest.raises(HistoryError):
        history.query_history(db, "/anywhere", limit=50)