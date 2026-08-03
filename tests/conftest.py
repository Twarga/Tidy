"""Shared test fixtures and git helpers for the Tidy test suite."""

from __future__ import annotations

import subprocess

import pytest

from tidy import config


def run(*args, cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def make_pair(tmp_path):
    """Create a work repo plus a matching bare 'origin' (returned as a tuple)."""
    bare = tmp_path / "origin.git"
    run("git", "init", "--bare", str(bare))
    run("git", "--git-dir", str(bare), "symbolic-ref", "HEAD", "refs/heads/main")

    work = tmp_path / "work"
    work.mkdir()
    run("git", "init", "-b", "main", cwd=work)
    run("git", "config", "user.email", "a@b", cwd=work)
    run("git", "config", "user.name", "Tidy", cwd=work)
    run("git", "remote", "add", "origin", str(bare), cwd=work)
    (work / "a.txt").write_text("hello\n")
    run("git", "add", "-A", cwd=work)
    run("git", "commit", "-m", "init", cwd=work)
    run("git", "push", "-u", "origin", "main", cwd=work)
    return work, bare


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("TIDY_CONFIG_DIR", str(tmp_path / "cfg"))
    return config.load()
