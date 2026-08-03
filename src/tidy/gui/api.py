"""pywebview JS <-> Python bridge.

Every method here is exposed to the web UI as ``pywebview.api.<name>``.
Methods return JSON-serializable dicts and never raise into JS: errors are
returned as ``{"error": "..."}``.
"""

from __future__ import annotations

from collections.abc import Callable

from tidy import config, logger, repos, schedules, sync

__all__ = ["Api"]


class Api:
    def __init__(self, dialog_provider: Callable[[], str | None] | None = None) -> None:
        # Default: native folder picker via the pywebview window.
        self._dialog = dialog_provider or self._default_dialog

    @staticmethod
    def _default_dialog() -> str | None:
        import webview

        if not webview.windows:
            return None
        result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        if not result:
            return None
        return result[0] if isinstance(result, (list, tuple)) else str(result)

    # ---------------------------------------------------------------- helpers

    def _cfg(self) -> dict:
        return config.load()

    # -------------------------------------------------------------- read side

    def list_repos(self) -> list[dict]:
        return self._cfg()["repos"]

    def get_theme(self) -> str:
        return config.get_theme(self._cfg())

    def get_settings(self) -> dict:
        from tidy.gui.themes import theme_names

        cfg = self._cfg()
        return {
            "theme": cfg["theme"],
            "autosync": cfg["autosync"],
            "notifications": cfg["notifications"],
            "stats": cfg["stats"],
            "themes": theme_names(),
        }

    def get_stats(self) -> dict:
        return config.get_stats(self._cfg())

    def get_logs(self, n: int = 30) -> list[dict]:
        return logger.get_logs(n)

    # ------------------------------------------------------------- write side

    def set_theme(self, name: str) -> dict:
        from tidy.gui.themes import validate_theme

        if not validate_theme(name):
            return {"error": f"unknown theme: {name}"}
        cfg = self._cfg()
        cfg["theme"] = name
        config.save(cfg)
        return {"ok": True, "theme": name}

    def set_autosync(self, enabled: bool) -> dict:
        cfg = self._cfg()
        cfg["autosync"] = bool(enabled)
        config.save(cfg)
        return {"ok": True, "autosync": cfg["autosync"]}

    def set_notifications(self, enabled: bool) -> dict:
        cfg = self._cfg()
        cfg["notifications"] = bool(enabled)
        config.save(cfg)
        return {"ok": True, "notifications": cfg["notifications"]}

    # ------------------------------------------------------------------- repos

    def add_repo(self) -> dict:
        path = self._dialog()
        if not path:
            return {"ok": False, "error": "no folder selected"}
        try:
            repo = repos.add_repo(self._cfg(), path)
        except (ValueError, OSError) as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "repo": repo}

    def remove_repo(self, repo_id: str) -> dict:
        try:
            removed = repos.remove_repo(self._cfg(), repo_id)
        except ValueError as exc:
            return {"error": str(exc)}
        return {"ok": True, "id": removed["id"]}

    def add_schedule(self, repo_id: str, time: str) -> dict:
        try:
            result = schedules.add_schedule(self._cfg(), repo_id, time)
        except ValueError as exc:
            return {"error": str(exc)}
        return {"ok": True, "schedules": result}

    def remove_schedule(self, repo_id: str, time: str) -> dict:
        try:
            result = schedules.remove_schedule(self._cfg(), repo_id, time)
        except ValueError as exc:
            return {"error": str(exc)}
        return {"ok": True, "schedules": result}

    # ------------------------------------------------------------------- sync

    def backup_now(self, repo_id: str = "all") -> dict:
        cfg = self._cfg()
        if repo_id == "all":
            return sync.sync_all(cfg)
        repo = repos.find_repo(cfg, repo_id)
        if repo is None:
            return {"ok": False, "error": f"repo not found: {repo_id}", "results": []}
        return {"ok": True, "results": [sync.sync_repo(cfg, repo)]}

    def pull_now(self, repo_id: str = "all") -> dict:
        cfg = self._cfg()
        if repo_id == "all":
            return sync.pull_all(cfg)
        repo = repos.find_repo(cfg, repo_id)
        if repo is None:
            return {"ok": False, "error": f"repo not found: {repo_id}", "results": []}
        return {"ok": True, "results": [sync.pull_repo(cfg, repo)]}
