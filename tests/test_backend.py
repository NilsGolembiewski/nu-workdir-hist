"""Tests for backend detection (sqlite present vs plaintext-only vs missing)."""

from __future__ import annotations

from pathlib import Path

import pytest

from nu_workdir_hist import backend
from nu_workdir_hist.errors import NoSqliteHistoryError


def test_detect_sqlite_present_returns_sqlite(populated_db):
    result = backend.detect(populated_db)
    assert result.kind is backend.Kind.SQLITE
    assert result.path == populated_db


def test_detect_plaintext_only_raises_no_sqlite(tmp_path):
    # A nushell config dir containing only history.txt.
    cfg = tmp_path / "nushell"
    cfg.mkdir()
    (cfg / "history.txt").write_text("ls\n\ngit status\n")
    sqlite_path = cfg / "history.sqlite3"
    with pytest.raises(NoSqliteHistoryError) as exc:
        backend.detect(sqlite_path)
    msg = str(exc.value)
    assert "plaintext" in msg.lower()
    assert "sqlite" in msg.lower()
    assert "file_format" in msg
    assert "history import" in msg
    assert str(sqlite_path) in msg


def test_detect_missing_entirely_raises_no_sqlite(tmp_path):
    sqlite_path = tmp_path / "history.sqlite3"
    with pytest.raises(NoSqliteHistoryError) as exc:
        backend.detect(sqlite_path)
    msg = str(exc.value)
    # Should still be actionable but distinguish "no file at all".
    assert str(sqlite_path) in msg
    assert "sqlite" in msg.lower()