"""Unit tests for the JSONL activity logger."""

from __future__ import annotations

import json

import pytest

from tidy import logger


@pytest.fixture(autouse=True)
def cfg_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TIDY_CONFIG_DIR", str(tmp_path / "cfg"))


def test_log_appends_entries():
    logger.log_info("hello", repo="notes")
    logger.log_warn("careful")
    logger.log_error("boom", repo="notes")

    entries = logger.get_logs()
    assert len(entries) == 3
    assert entries[0]["level"] == "INFO" and entries[0]["message"] == "hello"
    assert entries[0]["repo"] == "notes"
    assert entries[1]["level"] == "WARN"
    assert entries[2]["level"] == "ERROR"
    assert all(e["ts"] for e in entries)


def test_get_logs_limit_and_order():
    for i in range(10):
        logger.log_info(f"entry-{i}")
    last_three = logger.get_logs(3)
    assert [e["message"] for e in last_three] == ["entry-7", "entry-8", "entry-9"]


def test_get_logs_missing_file_returns_empty():
    assert logger.get_logs() == []


def test_corrupt_line_is_skipped():
    path = logger.log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        handle.write("{not json}\n")
        handle.write(json.dumps({"ts": "t", "level": "INFO", "message": "ok", "repo": None}) + "\n")

    entries = logger.get_logs()
    assert len(entries) == 1 and entries[0]["message"] == "ok"


def test_log_never_raises_on_io_error(monkeypatch):
    # Point the log path at a directory: appending to it raises OSError,
    # which log() must swallow and still return the entry.
    monkeypatch.setattr(logger, "log_path", lambda: logger.config_dir())
    entry = logger.log_info("will not be written")
    assert entry["message"] == "will not be written"
