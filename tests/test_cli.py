"""Tests for CLI argument parsing and end-to-end behavior."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from nu_workdir_hist import __version__, cli


def run_cli(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "nu_workdir_hist", *args],
        capture_output=True,
        text=True,
        env=env,
    )


# ---------- argument parsing ----------

def test_parse_default_last_is_50():
    ns = cli.parse_args([])
    assert ns.last == 50
    assert ns.verbose is False
    assert ns.physical is False
    assert ns.history_path is None


def test_parse_last_long_flag():
    assert cli.parse_args(["--last", "10"]).last == 10


def test_parse_last_short_flag():
    assert cli.parse_args(["-n", "7"]).last == 7


def test_parse_last_zero_means_all():
    assert cli.parse_args(["-n", "0"]).last == 0


def test_parse_verbose():
    assert cli.parse_args(["-v"]).verbose is True
    assert cli.parse_args(["--verbose"]).verbose is True


def test_parse_physical():
    assert cli.parse_args(["--physical"]).physical is True


def test_parse_history_path():
    assert cli.parse_args(["--history-path", "/x/y.sqlite3"]).history_path == "/x/y.sqlite3"


def test_parse_last_negative_rejected(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.parse_args(["-n", "-3"])
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "non-negative" in err.lower()


def test_parse_last_non_integer_rejected(capsys):
    with pytest.raises(SystemExit):
        cli.parse_args(["-n", "abc"])


# ---------- --version ----------

def test_version_flag_exits_zero_and_prints_version(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.parse_args(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert __version__ in out
    assert "nu-workdir-hist" in out


def test_version_subprocess_exits_zero():
    proc = run_cli("--version")
    assert proc.returncode == 0
    assert __version__ in proc.stdout
    assert "nu-workdir-hist" in proc.stdout


# ---------- last limit + env ----------

def test_last_from_env(monkeypatch):
    monkeypatch.setenv("NU_WORKDIR_HIST_LAST", "25")
    ns = cli.parse_args([])
    assert ns.last == 25


def test_flag_overrides_env(monkeypatch):
    monkeypatch.setenv("NU_WORKDIR_HIST_LAST", "25")
    ns = cli.parse_args(["-n", "5"])
    assert ns.last == 5


def test_invalid_env_last_falls_back_to_default(monkeypatch, capsys):
    monkeypatch.setenv("NU_WORKDIR_HIST_LAST", "notanint")
    ns = cli.parse_args([])
    assert ns.last == 50


def test_negative_env_last_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("NU_WORKDIR_HIST_LAST", "-1")
    ns = cli.parse_args([])
    assert ns.last == 50


def test_physical_from_env(monkeypatch):
    monkeypatch.setenv("NU_WORKDIR_HIST_PHYSICAL", "1")
    ns = cli.parse_args([])
    assert ns.physical is True


def test_physical_flag_overrides_env_false(monkeypatch):
    monkeypatch.setenv("NU_WORKDIR_HIST_PHYSICAL", "0")
    ns = cli.parse_args(["--physical"])
    assert ns.physical is True


# ---------- end to end via main() ----------

def test_main_prints_commands_for_cwd(populated_db, proj_dir, chdir_to):
    chdir_to(str(proj_dir))
    rc = cli.main([
        "--history-path", str(populated_db),
        "-n", "50",
    ])
    assert rc == 0


def test_main_output_oldest_first(populated_db, proj_dir, chdir_to, capsys):
    chdir_to(str(proj_dir))
    cli.main(["--history-path", str(populated_db)])
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["ls -la", "git status", "rm -rf build"]


def test_main_limit_caps(populated_db, proj_dir, chdir_to, capsys):
    # --last 2 selects the 2 most-recent then prints oldest-first.
    chdir_to(str(proj_dir))
    cli.main(["--history-path", str(populated_db), "-n", "2"])
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["git status", "rm -rf build"]


def test_main_zero_means_all(populated_db, proj_dir, chdir_to, capsys):
    chdir_to(str(proj_dir))
    cli.main(["--history-path", str(populated_db), "-n", "0"])
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["ls -la", "git status", "rm -rf build"]


def test_main_no_matches_prints_nothing(populated_db, proj_dir, chdir_to, capsys):
    chdir_to(str(proj_dir))
    cli.main(["--history-path", str(populated_db), "-n", "0"])
    # switch to a real cwd that has no history rows
    empty = proj_dir.parent / "empty-cwd"
    empty.mkdir()
    chdir_to(str(empty))
    capsys.readouterr()  # drain
    rc = cli.main(["--history-path", str(populated_db)])
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_main_verbose_includes_timestamp_and_exit(populated_db, proj_dir, chdir_to, capsys):
    chdir_to(str(proj_dir))
    cli.main(["--history-path", str(populated_db), "-v", "-n", "1"])
    out = capsys.readouterr().out
    # --last 1 selects the single most-recent command (id 4).
    assert "rm -rf build" in out
    assert "2023-11-14T22:13:23Z" in out
    assert "exit=0" in out


def test_main_plaintext_only_errors_nonzero(tmp_path, chdir_to, capsys):
    cfg = tmp_path / "nushell"
    cfg.mkdir()
    (cfg / "history.txt").write_text("ls\n")
    chdir_to(tmp_path)
    rc = cli.main(["--history-path", str(cfg / "history.sqlite3")])
    assert rc != 0
    err = capsys.readouterr().err
    assert "plaintext" in err.lower()
    assert "sqlite" in err.lower()
    assert "history import" in err


def test_main_missing_db_errors_nonzero(tmp_path, chdir_to, capsys):
    chdir_to(tmp_path)
    rc = cli.main(["--history-path", str(tmp_path / "nope.sqlite3")])
    assert rc != 0
    err = capsys.readouterr().err
    assert "sqlite" in err.lower()


def test_main_uses_env_history_path(populated_db, proj_dir, chdir_to, monkeypatch, capsys):
    chdir_to(str(proj_dir))
    monkeypatch.setenv("NU_HISTORY_PATH", str(populated_db))
    rc = cli.main([])
    assert rc == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["ls -la", "git status", "rm -rf build"]


def test_main_history_path_flag_overrides_env(populated_db, proj_dir, chdir_to, monkeypatch, capsys):
    chdir_to(str(proj_dir))
    monkeypatch.setenv("NU_HISTORY_PATH", "/nonexistent/env.sqlite3")
    rc = cli.main(["--history-path", str(populated_db)])
    assert rc == 0


def test_main_physical_mode_matches_resolved_path(populated_db, tmp_path, chdir_to, capsys, monkeypatch):
    # Create a symlink to proj_dir; stored cwd is the real proj_dir path.
    # With --physical the tool resolves the symlinked cwd back to proj_dir and
    # matches; without --physical (using $PWD=the symlink) it would not match.
    proj = tmp_path / "proj"
    link = tmp_path / "link-to-proj"
    link.symlink_to(proj, target_is_directory=True)
    chdir_to(str(link))
    monkeypatch.setenv("PWD", str(link))  # logical PWD points at the symlink
    capsys.readouterr()
    rc = cli.main(["--history-path", str(populated_db), "--physical", "-n", "10"])
    assert rc == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["ls -la", "git status", "rm -rf build"]


# ---------- subprocess end-to-end (real installed entry point path) ----------

def test_subprocess_help():
    proc = run_cli("--help")
    assert proc.returncode == 0
    assert "last" in proc.stdout.lower()
    assert "physical" in proc.stdout.lower()
    assert "history-path" in proc.stdout.lower()


def test_subprocess_runs_against_temp_db(tmp_path):
    # Build a DB whose cwd equals this tmp_path and run the CLI from tmp_path.
    from nu_workdir_hist.schema import connect_for_writing, populate
    db = tmp_path / "h.sqlite3"
    con = connect_for_writing(db)
    populate(con, [
        {"id": 1, "command_line": "echo first", "cwd": str(tmp_path),
         "start_timestamp": 1700000000000, "exit_status": 0},
        {"id": 2, "command_line": "echo second", "cwd": str(tmp_path),
         "start_timestamp": 1700000001000, "exit_status": 0},
    ])
    con.close()
    env = dict(os.environ)
    # Ensure $PWD matches the subprocess cwd so logical-mode matching works.
    env["PWD"] = str(tmp_path)
    proc = subprocess.run(
        [sys.executable, "-m", "nu_workdir_hist",
         "--history-path", str(db), "-n", "10"],
        capture_output=True, text=True, env=env, cwd=str(tmp_path),
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == ["echo first", "echo second"]