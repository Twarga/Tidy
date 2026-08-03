import subprocess

import pytest

from tidy import config, repos, schedules


def make_git_dir(folder, commit="init"):
    subprocess.run(["git", "init", "-b", "main"], cwd=folder, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test"], cwd=folder, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Tidy Test"], cwd=folder, check=True, capture_output=True
    )
    if commit:
        (folder / "a.txt").write_text("hello\n")
        subprocess.run(["git", "add", "-A"], cwd=folder, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", commit], cwd=folder, check=True, capture_output=True)


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("TIDY_CONFIG_DIR", str(tmp_path / "cfg"))
    return config.load()


def test_slugify():
    assert repos.slugify("My Notes/") == "my-notes"
    assert repos.slugify(" 42!! ") == "42"


def test_is_git_repo_and_auto_init(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert repos.is_git_repo(plain) is False
    repos.ensure_git_repo(plain)
    assert repos.is_git_repo(plain) is True


def test_add_repo_idempotent_and_unique(tmp_path, cfg):
    one = tmp_path / "one"
    one.mkdir()
    repos.ensure_git_repo(one)
    r1 = repos.add_repo(cfg, one)
    r2 = repos.add_repo(cfg, str(one))
    assert r1["id"] == r2["id"]
    assert len(cfg["repos"]) == 1

    two = tmp_path / "sub" / "one"
    two.mkdir(parents=True)
    r3 = repos.add_repo(cfg, two)
    assert r3["id"] != r1["id"]  # unique id despite same basename
    assert len(cfg["repos"]) == 2


def test_find_and_remove(tmp_path, cfg):
    folder = tmp_path / "notes"
    folder.mkdir()
    repos.ensure_git_repo(folder)
    added = repos.add_repo(cfg, folder)
    assert repos.find_repo(cfg, added["id"]) == added
    assert repos.find_repo(cfg, str(folder)) == added
    removed = repos.remove_repo(cfg, added["id"])
    assert removed["id"] == added["id"]
    assert cfg["repos"] == []


def test_remote_detection(tmp_path, cfg):
    work = tmp_path / "work"
    work.mkdir()
    make_git_dir(work)
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", str(bare)], cwd=work, check=True, capture_output=True
    )
    repo = repos.add_repo(cfg, work)
    assert repo["remote"] == str(bare)


def test_schedules_many_per_repo(tmp_path, cfg):
    folder = tmp_path / "notes"
    folder.mkdir()
    repos.ensure_git_repo(folder)
    repo = repos.add_repo(cfg, folder)
    schedules.add_schedule(cfg, repo["id"], "18:00")
    schedules.add_schedule(cfg, repo["id"], "08:00")
    schedules.add_schedule(cfg, repo["id"], "18:00")  # dup ignored
    times = [s["time"] for s in schedules.list_schedules(cfg, repo["id"])]
    assert times == ["08:00", "18:00"]  # sorted + deduped

    schedules.remove_schedule(cfg, repo["id"], "18:00")
    assert schedules.list_schedules(cfg, repo["id"]) == [{"time": "08:00", "enabled": True}]

    schedules.set_schedule_enabled(cfg, repo["id"], "08:00", False)
    assert schedules.list_schedules(cfg, repo["id"]) == [{"time": "08:00", "enabled": False}]


def test_normalize_time_rejects_bad():
    assert schedules.normalize_time("7:05") == "07:05"
    for bad in ["24:00", "12:60", "abc", "", "8:5"]:
        with pytest.raises(ValueError):
            schedules.normalize_time(bad)
