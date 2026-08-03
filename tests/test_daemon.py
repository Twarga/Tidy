"""Tests for the 24/7 daemon: scheduler jobs, lock file, notifications."""

import os
import signal
import subprocess
import sys
import time

import pytest
from conftest import make_pair

from tidy import config, repos, schedules
from tidy.daemon import acquire_lock
from tidy.notify import notify
from tidy.scheduler import SyncScheduler, build_job_id

# ------------------------------------------------------------------- job ids


def test_build_job_id_format():
    assert build_job_id("twarga-system", "18:00") == "repo:twarga-system:1800"


def test_reconfigure_creates_jobs_for_enabled_schedules(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    repo = repos.add_repo(config.load(), work, time="18:00")
    sch = SyncScheduler()
    try:
        sch.reconfigure(config.load())
        assert set(sch.jobs()) == {build_job_id(repo["id"], "18:00")}
    finally:
        sch.shutdown()


def test_reconfigure_ignores_disabled_and_removes_stale(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    repo = repos.add_repo(config.load(), work, time="18:00")
    schedules.set_schedule_enabled(config.load(), repo["id"], "18:00", False)

    sch = SyncScheduler()
    try:
        sch.reconfigure(config.load())
        assert sch.jobs() == []

        # re-enable and add another, then drop the repo -> jobs update
        schedules.set_schedule_enabled(config.load(), repo["id"], "18:00", True)
        schedules.add_schedule(config.load(), repo["id"], "09:30")
        sch.reconfigure(config.load())
        assert set(sch.jobs()) == {
            build_job_id(repo["id"], "18:00"),
            build_job_id(repo["id"], "09:30"),
        }

        repos.remove_repo(config.load(), repo["id"])
        sch.reconfigure(config.load())
        assert sch.jobs() == []
    finally:
        sch.shutdown()


# ------------------------------------------------------------------- lock


def test_lock_single_instance(tmp_path, monkeypatch):
    monkeypatch.setenv("TIDY_CONFIG_DIR", str(tmp_path))
    first = acquire_lock()
    assert first.name == "tidy.lock"
    with pytest.raises(SystemExit):
        acquire_lock()


# -------------------------------------------------------------- notifications


def test_notify_skips_headless(tmp_path, monkeypatch):
    monkeypatch.setenv("TIDY_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    config.load()
    assert notify("hi", "there") is False  # no display -> nothing sent


def test_notify_respects_disabled_setting(tmp_path, monkeypatch):
    monkeypatch.setenv("TIDY_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("DISPLAY", ":0")
    cfg = config.load()
    cfg["notifications"] = False
    config.save(cfg)
    assert notify("hi", "there") is False


# --------------------------------------------------------------------- daemon


def test_daemon_start_stop_cleanly(tmp_path, monkeypatch):
    """Run `tidy serve` as a subprocess, then SIGTERM it."""
    cfg_dir = str(tmp_path / "cfg")
    monkeypatch.setenv("TIDY_CONFIG_DIR", cfg_dir)
    work, _ = make_pair(tmp_path)
    repos.add_repo(config.load(), work, time="06:00")  # far-future, no firing

    env = dict(os.environ, TIDY_CONFIG_DIR=cfg_dir)
    proc = subprocess.Popen(
        [sys.executable, "-m", "tidy", "serve"],  # uses tidy.cli:main
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    time.sleep(1.5)  # let it start + reconfigure
    assert proc.poll() is None, "daemon should still be running"
    proc.send_signal(signal.SIGTERM)
    out, _ = proc.communicate(timeout=15)
    assert proc.returncode == 0, f"daemon exit != 0, output: {out}"
    assert "daemon started" in out and "daemon stopped" in out
