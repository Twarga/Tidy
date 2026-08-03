"""Tests for the MCP server tools (FastMCP, in-process via call_tool)."""

from __future__ import annotations

import pytest
from conftest import make_pair

from tidy.mcp import mcp


async def _call(name: str, **kwargs) -> dict:
    result = await mcp.call_tool(name, kwargs or None)
    value = result.structured_content
    # FastMCP wraps bare-list returns as {"result": [...]} — unwrap
    if isinstance(value, dict) and set(value.keys()) == {"result"}:
        return value["result"]
    return value


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("TIDY_CONFIG_DIR", str(tmp_path / "cfg"))
    from tidy import config

    return config.load()


# ------------------------------------------------------------------ read


async def test_list_repos_and_status(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    await _call("add_repo", path=str(work), time="18:00")

    repos = await _call("list_repos")
    assert len(repos) == 1 and repos[0]["id"] == "work"

    status = await _call("get_status")
    assert status["theme"] == "neon"
    assert len(status["repos"]) == 1
    assert status["stats"]["total_pushes"] == 0


async def test_get_logs(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    await _call("add_repo", path=str(work))
    (work / "note.md").write_text("hello\n")
    await _call("backup_now", repo="work")

    logs = await _call("get_logs", n=10)
    assert logs and logs[0]["level"] == "INFO"
    assert any("work" in (entry.get("repo") or "") for entry in logs)


# ------------------------------------------------------------------ repos


async def test_add_repo_idempotent_and_remote(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    first = await _call("add_repo", path=str(work))
    assert first["ok"] is True
    assert first["repo"]["remote"] is not None  # auto-detected

    again = await _call("add_repo", path=str(work))  # same path -> existing
    assert again["repo"]["id"] == first["repo"]["id"]
    assert len(await _call("list_repos")) == 1


async def test_add_repo_bad_path(cfg, tmp_path):
    result = await _call("add_repo", path=str(tmp_path / "does-not-exist"))
    assert result["ok"] is False and "error" in result


async def test_remove_repo_by_path_and_id(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    added = await _call("add_repo", path=str(work))
    removed = await _call("remove_repo", path_or_id=added["repo"]["id"])
    assert removed["ok"] is True
    assert len(await _call("list_repos")) == 0


# --------------------------------------------------------------- schedules


async def test_schedule_lifecycle(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    added = await _call("add_repo", path=str(work))
    rid = added["repo"]["id"]

    updated = await _call("add_schedule", repo=rid, time="09:30")
    assert updated["ok"] is True
    assert [s["time"] for s in updated["schedules"]] == ["09:30"]

    bad = await _call("add_schedule", repo=rid, time="banana")
    assert bad["ok"] is False

    after_remove = await _call("remove_schedule", repo=rid, time="09:30")
    assert after_remove["ok"] is True and after_remove["schedules"] == []


# ------------------------------------------------------------------- sync


async def test_backup_now_commits(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    await _call("add_repo", path=str(work))
    (work / "dirty.md").write_text("new content\n")

    result = await _call("backup_now", repo="work")
    assert result["ok"] is True
    assert result["results"][0]["committed"] is True

    # second run with no changes -> skipped
    again = await _call("backup_now")
    assert again["ok"] is True
    assert again["results"][0]["skipped"] is True


async def test_backup_unknown_repo(cfg, tmp_path):
    result = await _call("backup_now", repo="nope")
    assert result["ok"] is False and "error" in result


async def test_pull_now(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    await _call("add_repo", path=str(work))
    result = await _call("pull_now", repo="work")
    assert result["ok"] is True


# --------------------------------------------------------------- settings


async def test_set_setting(cfg):
    theme = await _call("set_setting", key="theme", value="paper")
    assert theme["ok"] is True and theme["value"] == "paper"

    bad_theme = await _call("set_setting", key="theme", value="lava")
    assert bad_theme["ok"] is False

    autosync = await _call("set_setting", key="autosync", value=False)
    assert autosync["ok"] is True and autosync["value"] is False

    unknown = await _call("set_setting", key="port", value=True)
    assert unknown["ok"] is False
