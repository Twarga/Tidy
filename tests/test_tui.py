"""Behaviour tests for the Tidy TUI, driven through textual's Pilot.

We launch the actual app headless (run_test), press keys, and assert on
real observable state (app.last_results after a background op, config on
disk, and the bare origin we pushed to).
"""

from __future__ import annotations

import asyncio
import subprocess

from conftest import make_pair

from tidy import config, repos
from tidy.tui.app import TidyApp


async def wait_until(condition, timeout: float = 5.0) -> None:
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if condition():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("condition not met before timeout")


def repo_readout(app) -> str:
    """All repo-row label text joined, for readable assertions."""
    from textual.widgets import Label

    labels = app.query(Label)
    return " || ".join(str(label.render()) for label in labels)


async def test_tui_starts_and_shows_repo(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    repos.add_repo(config.load(), work, time="18:00")

    app = TidyApp()
    async with app.run_test() as _pilot:
        list_view = app.query_one("#repos")
        await wait_until(lambda: len(list_view.children) >= 1)
        text = repo_readout(app)
        assert "work" in text
        assert "18:00" in text


async def test_tui_reports_no_repos(cfg):
    app = TidyApp()
    async with app.run_test() as _pilot:
        await wait_until(lambda: len(app.query_one("#repos").children) >= 1)
        assert "no repos" in repo_readout(app)


async def test_key_b_backs_up_all(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    repos.add_repo(config.load(), work)
    (work / "new.txt").write_text("hello\n")

    app = TidyApp()
    async with app.run_test() as pilot:
        await pilot.press("b")
        await wait_until(lambda: app.last_results != [])
        assert app.last_results[0]["ok"] is True
        assert app.last_results[0]["committed"] is True
        assert "✗" not in "".join(r["message"] for r in app.last_results)

    # The commit really landed on the remote.
    out = await asyncio.to_thread(
        subprocess.run,
        ["git", "-C", str(work), "log", "origin/main", "--oneline", "--max-count=1"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert "backup" in out.stdout


async def test_key_p_pulls_only(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    repos.add_repo(config.load(), work)

    app = TidyApp()
    async with app.run_test() as pilot:
        await pilot.press("p")
        await wait_until(lambda: app.last_results != [])
        assert app.last_results[0]["ok"] is True
        assert "pulled" in app.last_results[0]["message"]


async def test_enter_backs_up_selected_repo(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    repos.add_repo(config.load(), work)
    (work / "extra.txt").write_text("data\n")

    app = TidyApp()
    async with app.run_test() as pilot:
        list_view = app.query_one("#repos")
        list_view.focus()
        await pilot.pause()
        await pilot.press("enter")
        await wait_until(lambda: app.last_results != [])
        assert app.last_results[0]["ok"] is True


async def test_key_t_cycles_theme(cfg):
    config.load()  # ensure config exists in the fixture dir
    app = TidyApp()
    async with app.run_test() as pilot:
        await pilot.press("t")
        await pilot.pause()
        assert config.load()["theme"] == "crt"  # neon -> crt


async def test_refresh_repaints_new_repo(cfg, tmp_path):
    app = TidyApp()
    async with app.run_test() as pilot:
        # add a repo while the app is running
        work = tmp_path / "later"
        work.mkdir()
        await asyncio.to_thread(
            subprocess.run,
            ["git", "init", "-b", "main", str(work)],
            check=True,
            capture_output=True,
        )
        repos.add_repo(config.load(), work)

        await pilot.press("r")
        await wait_until(lambda: "later" in repo_readout(app))


async def test_key_q_quits(cfg):
    app = TidyApp()
    async with app.run_test() as pilot:
        await pilot.press("q")
