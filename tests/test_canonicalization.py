"""Tests for cwd canonicalization (logical vs physical)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from nu_workdir_hist import paths


def test_normalize_logical_strips_trailing_slash(isolated_cwd):
    norm = paths.normalize_logical(Path("/home/alice/proj/"))
    assert norm == "/home/alice/proj"


def test_normalize_logical_preserves_root():
    # Root keeps its single separator.
    assert paths.normalize_logical(Path("/")) == "/"


def test_normalize_logical_makes_relative_absolute(isolated_cwd):
    # A relative path is resolved against the process cwd.
    norm = paths.normalize_logical(Path("."))
    assert norm == str(isolated_cwd)
    assert not norm.endswith("/")


def test_normalize_logical_keeps_symlink_components(tmp_path, isolated_cwd, monkeypatch):
    # An *arbitrary absolute path* containing a symlink is preserved verbatim
    # (NOT realpath-resolved) — matching nushell's stored logical PWD form.
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)

    norm = paths.normalize_logical(link)
    assert norm == str(link)


def test_current_workdir_logical_honors_pwd_env(tmp_path, isolated_cwd, monkeypatch):
    # When run inside a symlinked dir, current_workdir(physical=False) must use
    # nushell's logical PWD ($PWD), NOT os.getcwd()'s physical resolution.
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    monkeypatch.chdir(link)
    monkeypatch.setenv("PWD", str(link))

    assert paths.current_workdir(physical=False) == str(link)


def test_normalize_physical_resolves_symlinks(tmp_path, isolated_cwd, monkeypatch):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    monkeypatch.chdir(link)
    monkeypatch.setenv("PWD", str(link))

    norm = paths.normalize_physical()
    assert norm == str(real.resolve())
    assert norm != str(link)


def test_current_workdir_logical_default(tmp_path, isolated_cwd, monkeypatch):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    monkeypatch.chdir(link)
    monkeypatch.setenv("PWD", str(link))

    assert paths.current_workdir(physical=False) == str(link)
    assert paths.current_workdir(physical=True) == str(real.resolve())


def test_current_workdir_logical_falls_back_when_pwd_unset(tmp_path, isolated_cwd, monkeypatch):
    # Without $PWD set, fall back to Path.cwd() (physical) normalized.
    monkeypatch.delenv("PWD", raising=False)
    got = paths.current_workdir(physical=False)
    assert got == str(isolated_cwd)


def test_physical_env_truthy(monkeypatch):
    assert paths.physical_from_env("1") is True
    assert paths.physical_from_env("true") is True
    assert paths.physical_from_env("TRUE") is True
    assert paths.physical_from_env("yes") is True


def test_physical_env_falsy(monkeypatch):
    assert paths.physical_from_env("0") is False
    assert paths.physical_from_env("") is False
    assert paths.physical_from_env("no") is False
    assert paths.physical_from_env(None) is False