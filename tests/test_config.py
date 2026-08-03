import json

import pytest

from tidy import config


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("TIDY_CONFIG_DIR", str(tmp_path))
    return config.load()


def test_load_creates_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("TIDY_CONFIG_DIR", str(tmp_path))
    cfg = config.load()
    assert cfg["version"] == 1
    assert cfg["theme"] == "neon"
    assert cfg["repos"] == []
    assert config.config_path().exists()


def test_save_roundtrip(cfg):
    cfg["theme"] = "crt"
    cfg["stats"]["total_pushes"] = 7
    config.save(cfg)
    reloaded = config.load()
    assert reloaded["theme"] == "crt"
    assert reloaded["stats"]["total_pushes"] == 7


def test_corrupt_file_heals(tmp_path, monkeypatch):
    monkeypatch.setenv("TIDY_CONFIG_DIR", str(tmp_path))
    path = config.config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json!!")
    cfg = config.load()
    assert cfg["repos"] == []
    assert config.config_path().exists()
    # a backup of the corrupt file was kept
    assert (path.parent / "config.json.bak").exists()


def test_migration_merges_missing_keys(cfg):
    path = config.config_path()
    path.write_text(json.dumps({"theme": "paper"}))  # missing version + stats + repos
    fresh = config.load()
    assert fresh["theme"] == "paper"
    assert fresh["version"] == 1
    assert fresh["repos"] == []
    assert fresh["stats"] == config.DEFAULT_CONFIG["stats"]


def test_update_stats_clears_error(cfg):
    config.update_stats(cfg, total_pushes=3, last_error="boom")
    assert config.load()["stats"]["last_error"] == "boom"
    config.update_stats(cfg, last_error=None)
    assert config.load()["stats"]["last_error"] is None
