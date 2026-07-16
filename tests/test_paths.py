"""Tests for the nushell config-dir / history.sqlite3 path resolution."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from nu_workdir_hist import paths


def test_default_history_path_honors_xdg_config_home(monkeypatch, tmp_path):
    xdg = tmp_path / "xdgconfig"
    xdg.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.delenv("NU_HISTORY_PATH", raising=False)

    got = paths.default_history_path()
    assert got == (xdg / "nushell" / "history.sqlite3")


def test_default_history_path_linux_default(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("NU_HISTORY_PATH", raising=False)
    home = tmp_path / "home"
    (home / ".config" / "nushell").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))

    with monkeypatch.context() as m:
        m.setattr(paths.sys, "platform", "linux")
        got = paths.default_history_path()
    assert got == (home / ".config" / "nushell" / "history.sqlite3")


def test_default_history_path_macos(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("NU_HISTORY_PATH", raising=False)
    home = tmp_path / "home"
    (home / "Library" / "Application Support" / "nushell").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))

    with monkeypatch.context() as m:
        m.setattr(paths.sys, "platform", "darwin")
        got = paths.default_history_path()
    assert got == (
        home / "Library" / "Application Support" / "nushell" / "history.sqlite3"
    )


def test_xdg_config_home_wins_over_macos_default(monkeypatch, tmp_path):
    xdg = tmp_path / "xdg"
    xdg.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    with monkeypatch.context() as m:
        m.setattr(paths.sys, "platform", "darwin")
        got = paths.default_history_path()
    assert got == (xdg / "nushell" / "history.sqlite3")


def test_resolve_history_path_explicit_flag_wins(monkeypatch, tmp_path):
    explicit = tmp_path / "custom.sqlite3"
    explicit.write_bytes(b"")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("NU_HISTORY_PATH", str(tmp_path / "env.sqlite3"))

    got = paths.resolve_history_path(flag_value=str(explicit))
    assert got == explicit


def test_resolve_history_path_env_var_used_when_no_flag(monkeypatch, tmp_path):
    env_path = tmp_path / "env.sqlite3"
    monkeypatch.setenv("NU_HISTORY_PATH", str(env_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    got = paths.resolve_history_path(flag_value=None)
    assert got == env_path


def test_resolve_history_path_falls_back_to_default(monkeypatch, tmp_path):
    monkeypatch.delenv("NU_HISTORY_PATH", raising=False)
    xdg = tmp_path / "xdg"
    xdg.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    got = paths.resolve_history_path(flag_value=None)
    assert got == (xdg / "nushell" / "history.sqlite3")


def test_resolve_history_path_empty_flag_treats_as_unset(monkeypatch, tmp_path):
    monkeypatch.setenv("NU_HISTORY_PATH", str(tmp_path / "env.sqlite3"))
    xdg = tmp_path / "xdg"
    xdg.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    # An empty string flag should be treated as "not provided".
    got = paths.resolve_history_path(flag_value="")
    assert got == (tmp_path / "env.sqlite3")