import json
import subprocess

import pytest

from tidy import config, repos
from tidy.cli import main


def run(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def make_git(folder, bare=None):
    folder.mkdir()
    run("git", "init", "-b", "main", cwd=folder)
    run("git", "config", "user.email", "a@b", cwd=folder)
    run("git", "config", "user.name", "Tidy", cwd=folder)
    if bare:
        run("git", "remote", "add", "origin", str(bare), cwd=folder)
        (folder / "a.txt").write_text("hi\n")
        run("git", "add", "-A", cwd=folder)
        run("git", "commit", "-m", "init", cwd=folder)
        run("git", "push", "-u", "origin", "main", cwd=folder)


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("TIDY_CONFIG_DIR", str(tmp_path / "cfg"))
    return config.load()


def test_no_command_prints_help(capsys):
    assert main([]) == 0
    assert "usage" in capsys.readouterr().out


def test_version_prints(capsys):
    with pytest.raises(SystemExit):
        main(["--version"])
    assert "tidy" in capsys.readouterr().out


def test_add_repo(tmp_path, cfg):
    folder = tmp_path / "notes"
    folder.mkdir()
    assert main(["add", str(folder), "--at", "18:00"]) == 0
    repo = repos.find_repo(config.load(), str(folder))
    assert repo is not None
    assert repo["schedules"][0]["time"] == "18:00"


def test_add_bad_time_exits_1(tmp_path, cfg, capfd):
    folder = tmp_path / "notes"
    folder.mkdir()
    assert main(["add", str(folder), "--at", "25:99"]) == 1
    assert "✗" in capfd.readouterr().out


def test_schedule_routes(tmp_path, cfg):
    folder = tmp_path / "notes"
    folder.mkdir()
    repos.add_repo(config.load(), folder)
    assert main(["schedule", str(folder), "--at", "09:30"]) == 0
    assert main(["unschedule", str(folder), "--at", "09:30"]) == 0


def test_remove(tmp_path, cfg):
    folder = tmp_path / "notes"
    folder.mkdir()
    repos.add_repo(config.load(), folder)
    assert main(["remove", str(folder)]) == 0
    assert config.load()["repos"] == []


def test_theme_set_and_invalid(tmp_path, cfg):
    assert main(["theme", "gameboy"]) == 0
    assert config.load()["theme"] == "gameboy"
    with pytest.raises(SystemExit) as exc:
        main(["theme", "nope"])  # argparse rejects invalid choices
    assert exc.value.code == 2


def test_status_json_shape(tmp_path, cfg, capsys):
    folder = tmp_path / "notes"
    folder.mkdir()
    repos.add_repo(config.load(), folder)
    assert main(["status", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["repos"][0]["path"] == str(folder.resolve())
    assert set(payload) >= {"version", "theme", "stats", "repos"}


def test_backup_all_pushes(tmp_path, cfg):
    bare = tmp_path / "origin.git"
    run("git", "init", "--bare", str(bare))
    run("git", "--git-dir", str(bare), "symbolic-ref", "HEAD", "refs/heads/main")
    work = tmp_path / "work"
    make_git(work, bare=bare)
    repos.add_repo(config.load(), work)

    (work / "new.txt").write_text("hello\n")
    assert main(["backup", "all"]) == 0
    out = run("git", "-C", str(work), "log", "origin/main", "--oneline", "--max-count=1")
    assert "backup" in out.stdout


def test_backup_without_repos(tmp_path, cfg, capsys):
    assert main(["backup", "all"]) == 1
    assert "no repos" in capsys.readouterr().out


def test_logs_returns_ok(tmp_path, cfg, capfd):
    assert main(["logs"]) == 0
