"""Shared pytest fixtures: a real-schema nushell history.sqlite3 in a temp dir."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from nu_workdir_hist.schema import connect_for_writing, populate


@pytest.fixture
def history_db(tmp_path: Path) -> Path:
    """A path to a fresh, empty, real-schema history.sqlite3."""
    db = tmp_path / "history.sqlite3"
    connect_for_writing(db).close()
    return db


@pytest.fixture
def history_conn(tmp_path: Path):
    """An open writable connection to a real-schema DB (closed after the test)."""
    db = tmp_path / "history.sqlite3"
    conn = connect_for_writing(db)
    yield conn
    conn.close()


@pytest.fixture
def populated_db(tmp_path: Path) -> Path:
    """A DB with a known set of rows across two real directories + a NULL cwd row.

    Two real directories (``proj_dir`` and ``other_dir``) are created under
    ``tmp_path`` so tests can actually ``chdir`` into them; the stored ``cwd``
    values point at those real paths. ``proj_dir`` has three commands (ids 1,2,4),
    ``other_dir`` has one (id 3), and one row has a NULL cwd (id 5).
    """
    proj_dir = tmp_path / "proj"
    other_dir = tmp_path / "other"
    proj_dir.mkdir()
    other_dir.mkdir()
    db = tmp_path / "history.sqlite3"
    conn = connect_for_writing(db)
    populate(
        conn,
        [
            {"id": 1, "command_line": "ls -la", "cwd": str(proj_dir),
             "start_timestamp": 1700000000000, "exit_status": 0},
            {"id": 2, "command_line": "git status", "cwd": str(proj_dir),
             "start_timestamp": 1700000001000, "exit_status": 0},
            {"id": 3, "command_line": "make test", "cwd": str(other_dir),
             "start_timestamp": 1700000002000, "exit_status": 1},
            {"id": 4, "command_line": "rm -rf build", "cwd": str(proj_dir),
             "start_timestamp": 1700000003000, "exit_status": 0},
            {"id": 5, "command_line": "imported-no-cwd", "cwd": None,
             "start_timestamp": 1700000004000, "exit_status": 0},
        ],
    )
    conn.close()
    return db


@pytest.fixture
def proj_dir(populated_db: Path, tmp_path: Path) -> Path:
    """The 'proj' directory whose cwd has 3 history rows."""
    return tmp_path / "proj"


@pytest.fixture
def other_dir(populated_db: Path, tmp_path: Path) -> Path:
    """The 'other' directory whose cwd has 1 history row."""
    return tmp_path / "other"


@pytest.fixture
def chdir_to(monkeypatch):
    """Return a callable that changes the process cwd (and $PWD) for the test."""
    def _go(path: str | Path) -> str:
        p = str(path)
        os.chdir(p)
        monkeypatch.setenv("PWD", p)
        return p
    return _go


@pytest.fixture
def isolated_cwd(tmp_path: Path, monkeypatch) -> Path:
    """A temp directory the test runs in, so Path.cwd() is stable."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PWD", str(tmp_path))
    return tmp_path