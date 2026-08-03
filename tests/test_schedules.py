"""Unit tests for the schedule manager (many backup times per repo)."""

from __future__ import annotations

import pytest

from tidy import config, schedules


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("TIDY_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = config.load()
    cfg["repos"] = [
        {"id": "notes", "path": "/tmp/notes", "remote": None, "branch": "main", "schedules": []}
    ]
    config.save(cfg)
    return cfg


# ------------------------------------------------------------- normalization


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("18:00", "18:00"),
        ("9:05", "09:05"),
        ("00:00", "00:00"),
        ("23:59", "23:59"),
        (" 12:30 ", "12:30"),
    ],
)
def test_normalize_time_ok(raw, expected):
    assert schedules.normalize_time(raw) == expected


@pytest.mark.parametrize("bad", ["25:00", "12:60", "7:3", "abc", "", "18:00:00", "6 pm", None])
def test_normalize_time_invalid(bad):
    with pytest.raises(ValueError):
        schedules.normalize_time(bad)


# ------------------------------------------------------------------ add/remove


def test_add_schedule_normalizes_and_sorts(cfg):
    schedules.add_schedule(cfg, "notes", "18:00")
    schedules.add_schedule(cfg, "notes", "9:00")
    assert [s["time"] for s in schedules.list_schedules(cfg, "notes")] == ["09:00", "18:00"]


def test_add_schedule_dedupes(cfg):
    schedules.add_schedule(cfg, "notes", "12:30")
    schedules.add_schedule(cfg, "notes", "12:30")  # duplicate — no-op
    assert len(schedules.list_schedules(cfg, "notes")) == 1


def test_repo_holds_many_times(cfg):
    for t in ("08:00", "12:00", "18:00", "21:30"):
        schedules.add_schedule(cfg, "notes", t)
    assert [s["time"] for s in schedules.list_schedules(cfg, "notes")] == [
        "08:00",
        "12:00",
        "18:00",
        "21:30",
    ]


def test_remove_schedule(cfg):
    schedules.add_schedule(cfg, "notes", "12:30")
    schedules.add_schedule(cfg, "notes", "18:00")
    updated = schedules.remove_schedule(cfg, "notes", "12:30")
    assert [s["time"] for s in updated] == ["18:00"]


def test_remove_missing_schedule_is_noop(cfg):
    schedules.add_schedule(cfg, "notes", "12:30")
    updated = schedules.remove_schedule(cfg, "notes", "06:00")
    assert [s["time"] for s in updated] == ["12:30"]


def test_unknown_repo_raises(cfg):
    with pytest.raises(ValueError):
        schedules.add_schedule(cfg, "ghost", "12:30")
    with pytest.raises(ValueError):
        schedules.remove_schedule(cfg, "ghost", "12:30")
    with pytest.raises(ValueError):
        schedules.list_schedules(cfg, "ghost")


def test_set_schedule_enabled(cfg):
    schedules.add_schedule(cfg, "notes", "12:30")
    updated = schedules.set_schedule_enabled(cfg, "notes", "12:30", False)
    assert updated == [{"time": "12:30", "enabled": False}]
    # enabling again
    updated = schedules.set_schedule_enabled(cfg, "notes", "12:30", True)
    assert updated[0]["enabled"] is True


def test_invalid_time_raises(cfg):
    with pytest.raises(ValueError):
        schedules.add_schedule(cfg, "notes", "banana")
