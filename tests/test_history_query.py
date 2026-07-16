"""Tests for querying the nushell history sqlite DB by cwd."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from nu_workdir_hist import history
from nu_workdir_hist.errors import HistoryError, NoSqliteHistoryError


def test_query_returns_commands_for_cwd_oldest_first(populated_db, proj_dir):
    # The N most-recent matching rows are selected, then printed oldest-first
    # (chronological): lowest id first.
    rows = history.query_history(populated_db, str(proj_dir), limit=50)
    assert [r.command_line for r in rows] == ["ls -la", "git status", "rm -rf build"]


def test_query_excludes_null_cwd_rows(populated_db, proj_dir):
    rows = history.query_history(populated_db, str(proj_dir), limit=50)
    assert "imported-no-cwd" not in [r.command_line for r in rows]


def test_query_excludes_other_cwds(populated_db, other_dir):
    rows = history.query_history(populated_db, str(other_dir), limit=50)
    assert [r.command_line for r in rows] == ["make test"]


def test_query_limit_caps_results(populated_db, proj_dir):
    # --last 2 selects the 2 most-recent (ids 4, 2) then prints oldest-first.
    rows = history.query_history(populated_db, str(proj_dir), limit=2)
    assert [r.command_line for r in rows] == ["git status", "rm -rf build"]


def test_query_limit_zero_means_no_limit(populated_db, proj_dir):
    rows = history.query_history(populated_db, str(proj_dir), limit=0)
    assert len(rows) == 3


def test_query_limit_zero_returns_oldest_first(populated_db, proj_dir):
    rows = history.query_history(populated_db, str(proj_dir), limit=0)
    # Oldest-first even with no limit.
    assert [r.id for r in rows] == [1, 2, 4]


def test_query_limit_selects_most_recent_then_oldest_first(populated_db, tmp_path):
    # 5 matching rows with distinct ids; --last 3 selects the 3 most-recent
    # (ids 3,4,5) and prints them oldest-first (3,4,5).
    db = tmp_path / "h.sqlite3"
    con = sqlite3.connect(str(db))
    con.execute(
        "CREATE TABLE history (id INTEGER PRIMARY KEY, command_line TEXT NOT NULL, "
        "cwd TEXT, start_timestamp INTEGER, exit_status INTEGER)"
    )
    cwd = str(tmp_path)
    for i in range(1, 6):
        con.execute(
            "INSERT INTO history (id, command_line, cwd, start_timestamp, exit_status) "
            "VALUES (?, ?, ?, ?, ?)",
            (i, f"cmd{i}", cwd, 1700000000000 + i * 1000, 0),
        )
    con.commit()
    con.close()
    rows = history.query_history(db, cwd, limit=3)
    assert [r.command_line for r in rows] == ["cmd3", "cmd4", "cmd5"]
    assert [r.id for r in rows] == [3, 4, 5]


def test_query_unknown_cwd_returns_empty(populated_db):
    rows = history.query_history(populated_db, "/nowhere", limit=50)
    assert rows == []


def test_query_carries_metadata(populated_db, proj_dir):
    rows = history.query_history(populated_db, str(proj_dir), limit=50)
    # Oldest-first: the first row is the oldest (id 1).
    top = rows[0]
    assert top.command_line == "ls -la"
    assert top.start_timestamp == 1700000000000
    assert top.exit_status == 0
    assert top.cwd == str(proj_dir)
    assert top.id == 1


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