"""Integration tests for the sync engine using a local bare repo as "origin"."""

import subprocess

import pytest

from tidy import config, repos, sync


def make_pair(tmp_path):
    """Create a work repo with a matching bare 'origin'."""

    def run(*args, cwd=None):
        return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)

    bare = tmp_path / "origin.git"
    run("git", "init", "--bare", str(bare))
    # Bare repos default HEAD to refs/heads/master; point it at main so clones
    # land on the main branch (matching how Tidy initializes work trees).
    run("git", "--git-dir", str(bare), "symbolic-ref", "HEAD", "refs/heads/main")

    work = tmp_path / "work"
    work.mkdir()
    run("git", "init", "-b", "main", cwd=work)
    run("git", "config", "user.email", "a@b.com", cwd=work)
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


def test_sync_pushes_then_skips_when_clean(tmp_path, cfg):
    work, _ = make_pair(tmp_path)
    repos.add_repo(cfg, work)

    # First sync: nothing changed locally -> skip, but remote present so it pushes as no-op.
    result = sync.sync_repo(cfg, repos.find_repo(cfg, work))
    assert result["ok"] is True
    assert result["skipped"] is True

    # Edit a file -> next sync must commit + push.
    (work / "new.md").write_text("note\n")
    result = sync.sync_repo(cfg, repos.find_repo(cfg, work))
    assert result["ok"] is True
    assert result["committed"] is True
    assert result["skipped"] is False

    # Confirm the commit landed on the bare origin.
    out = subprocess.run(
        ["git", "-C", str(work), "log", "origin/main", "--oneline", "--max-count=1"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert "backup" in out.stdout


def test_sync_two_way_merge(tmp_path, cfg):
    """A change pushed from 'another device' is pulled before our changes."""

    def run(*args, cwd=None):
        return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)

    work, bare = make_pair(tmp_path)
    repos.add_repo(cfg, work)

    # Simulate another device: clone the bare repo and push a change.
    other = tmp_path / "other"
    run("git", "clone", str(bare), str(other))
    run("git", "config", "user.name", "Other", cwd=other)
    run("git", "config", "user.email", "o@o.com", cwd=other)
    (other / "remote-note.md").write_text("from another device\n")
    run("git", "add", "-A", cwd=other)
    run("git", "commit", "-m", "remote edit", cwd=other)
    run("git", "push", "origin", "main", cwd=other)

    # Now our local repo has a fresh edit on top of a stale origin -> sync must merge.
    (work / "local-note.md").write_text("my change\n")
    result = sync.sync_repo(cfg, repos.find_repo(cfg, work))
    assert result["ok"] is True
    assert result["committed"] is True

    # After syncing, the local tree contains BOTH remote edits and our edit.
    out = run("git", "-C", str(work), "ls-tree", "origin/main", "--name-only")
    assert "remote-note.md" in out.stdout
    assert "local-note.md" in out.stdout


def test_sync_all_aggregates(tmp_path, cfg):
    work, _ = make_pair(tmp_path)
    repos.add_repo(cfg, work)
    result = sync.sync_all(cfg)
    assert result["ok"] is True
    assert len(result["results"]) == 1
