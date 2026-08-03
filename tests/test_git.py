import subprocess

import pytest

from tidy import git


def make_repo(folder):
    folder.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=folder, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "a@b"], cwd=folder, check=True, capture_output=True
    )
    subprocess.run(["git", "config", "user.name", "T"], cwd=folder, check=True, capture_output=True)
    return folder


def test_branch_detection(tmp_path):
    repo = make_repo(tmp_path / "r")
    assert git.default_branch(str(repo)) == "main"


def test_commit_all_and_skip(tmp_path):
    repo = make_repo(tmp_path / "r")
    (repo / "a.txt").write_text("x\n")
    assert git.has_changes(str(repo)) is True
    assert git.commit_all(str(repo), "first") is True
    assert git.has_changes(str(repo)) is False
    assert git.commit_all(str(repo), "again") is False  # clean -> no commit
    assert git.has_commits(str(repo)) is True


def test_has_remote(tmp_path):
    repo = make_repo(tmp_path / "r")
    bare = tmp_path / "o.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", str(bare)], cwd=repo, check=True, capture_output=True
    )
    assert git.has_remote(str(repo)) is True


def test_bad_command_raises(tmp_path):
    repo = make_repo(tmp_path / "r")
    with pytest.raises(git.GitError):
        git.run_git(str(repo), "this-command-does-not-exist")
