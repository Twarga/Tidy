"""Tests for the GUI layer: API bridge, theme registry, tray fallback, assets.

The pywebview *window* itself can't open in a headless test, so we exercise
everything that is pure logic (the Api class, theme CSS, tray headless guard)
and confirm the web assets + offline fonts are bundled.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import make_pair

from tidy import config, repos
from tidy.gui.api import Api
from tidy.gui.themes import THEMES, theme_names, validate_theme


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("TIDY_CONFIG_DIR", str(tmp_path / "cfg"))
    return config.load()


def _api(cfg=None) -> Api:
    return Api(dialog_provider=lambda: None)


# ------------------------------------------------------------------- Api read


def test_api_list_repos_and_settings(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    repos.add_repo(config.load(), work, time="18:00")
    api = _api()
    assert len(api.list_repos()) == 1
    settings = api.get_settings()
    assert "themes" in settings and settings["themes"] == theme_names()
    assert settings["stats"]["total_pushes"] == 0


def test_api_theme_roundtrip(cfg):
    api = _api()
    assert api.set_theme("paper")["theme"] == "paper"
    assert api.get_theme() == "paper"
    assert "error" in api.set_theme("nope")


def test_api_toggles(cfg):
    api = _api()
    assert api.set_autosync(False)["autosync"] is False
    assert api.set_notifications(False)["notifications"] is False


def test_api_schedules(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    repo = repos.add_repo(config.load(), work, time="18:00")
    api = _api()
    assert api.add_schedule(repo["id"], "09:30")["ok"] is True
    assert [s["time"] for s in api.list_repos()[0]["schedules"]] == ["09:30", "18:00"]
    assert api.remove_schedule(repo["id"], "09:30")["ok"] is True
    assert "error" in api.add_schedule(repo["id"], "banana")  # invalid time


# ------------------------------------------------------------ Api add repo


def test_api_add_repo_via_dialog(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    api = Api(dialog_provider=lambda: str(work))
    result = api.add_repo()
    assert result["ok"] is True
    assert result["repo"]["id"] == "work"


def test_api_add_repo_cancel(cfg):
    api = Api(dialog_provider=lambda: None)
    assert api.add_repo()["ok"] is False


def test_api_remove_repo(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    repo = repos.add_repo(config.load(), work)
    api = _api()
    assert api.remove_repo(repo["id"])["ok"] is True
    assert "error" in api.remove_repo(repo["id"])  # already gone


# ------------------------------------------------------------------- sync


def test_api_backup_all(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    repos.add_repo(config.load(), work)
    (work / "new.txt").write_text("hi\n")
    api = _api()
    result = api.backup_now("all")
    assert result["ok"] is True
    assert result["results"][0]["committed"] is True


def test_api_pull_all(cfg, tmp_path):
    work, _ = make_pair(tmp_path)
    repos.add_repo(config.load(), work)
    api = _api()
    result = api.pull_now("all")
    assert result["ok"] is True


def test_api_backup_unknown_repo(cfg):
    api = _api()
    result = api.backup_now("missing")
    assert result["ok"] is False and "error" in result


# ------------------------------------------------------------------ themes


def test_five_themes_with_full_palette():
    assert theme_names() == ["neon", "crt", "gameboy", "watermelon", "paper"]
    required = {"bg", "panel", "panel2", "border", "accent", "text", "muted", "ok", "warn", "bad"}
    for name, palette in THEMES.items():
        assert required <= set(palette)
        for value in palette.values():
            assert value.startswith("#") and len(value) == 7, f"{name}: bad color {value}"


def test_validate_theme():
    assert validate_theme("gameboy") is True
    assert validate_theme("pixel-unknown") is False


# -------------------------------------------------------------------- tray


def test_tray_disabled_headless():
    import os

    old_display = os.environ.get("DISPLAY")
    old_wayland = os.environ.get("WAYLAND_DISPLAY")
    os.environ.pop("DISPLAY", None)
    os.environ.pop("WAYLAND_DISPLAY", None)
    try:
        from tidy.gui.tray import TidyTray

        tray = TidyTray(show_window=lambda: None, quit_app=lambda: None)
        assert tray.start() is False  # no display -> gracefully off
    finally:
        if old_display:
            os.environ["DISPLAY"] = old_display
        if old_wayland:
            os.environ["WAYLAND_DISPLAY"] = old_wayland


# ------------------------------------------------------------------- assets


def test_web_assets_present():
    web = Path(__file__).resolve().parents[1] / "src" / "tidy" / "gui" / "web"
    for name in ("index.html", "app.js"):
        assert (web / name).exists(), f"missing {name}"
    html = (web / "index.html").read_text()
    assert "app.js" in html
    assert "fonts/vt323.woff2" in html
    assert "fonts/pressstart2p.woff2" in html
    for font in ("vt323.woff2", "pressstart2p.woff2"):
        assert (web / "fonts" / font).stat().st_size > 1000, f"font {font} looks empty"
