"""Tidy TUI application — full-screen terminal dashboard.

Keys:
  b  backup all repos      p  pull all repos
  r  refresh               t  cycle theme
  Enter  backup selected repo      q  quit
"""

from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Footer, Header, Static

from tidy import config, logger, repos, sync
from tidy.tui.themes import accent_for, cycle_theme
from tidy.tui.views import LogPanel, RepoList
from tidy.tui.worker import run_in_background

__all__ = ["SyncFinished", "TidyApp"]


class SyncFinished(Message):
    """Posted (on the UI thread) when a background sync/pull completes."""

    def __init__(self, results: list[dict]) -> None:
        super().__init__()
        self.results = results


class TidyApp(App[None]):
    """Textual application for Tidy."""

    TITLE = "TIDY"
    SUB_TITLE = "keep your folders tidy"
    CSS = """
    #busy {
        height: 1;
        display: none;
    }
    #busy.busy {
        display: block;
        color: $accent;
    }
    #repos {
        height: auto;
        max-height: 12;
        border: round $accent;
    }
    #logs {
        height: 1fr;
        border: round $primary;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("b", "backup_all", "Backup all"),
        Binding("p", "pull_all", "Pull all"),
        Binding("r", "refresh", "Refresh"),
        Binding("t", "cycle_theme", "Theme"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._busy = False
        # Observable test hook: set after every background operation completes.
        self.last_results: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield Static("◉ working…", id="busy")
            yield RepoList(id="repos")
            yield LogPanel(id="logs", highlight=True, max_lines=2000)
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_all()
        self.set_interval(2.0, self._poll_log)

    # ---------- UI helpers ----------

    def repos_widget(self) -> RepoList:
        return self.query_one("#repos", RepoList)

    def logs_widget(self) -> LogPanel:
        return self.query_one("#logs", LogPanel)

    def busy_widget(self) -> Static:
        return self.query_one("#busy", Static)

    def refresh_all(self) -> None:
        cfg = config.load()
        accent = accent_for(cfg["theme"])
        self.repos_widget().update_repos(cfg, accent)
        self.logs_widget().write_line(f"[{accent}]══ TIDY · theme: {cfg['theme']}[/]")

    def refresh_repos(self) -> None:
        cfg = config.load()
        self.repos_widget().update_repos(cfg, accent_for(cfg["theme"]))

    def _poll_log(self) -> None:
        for entry in logger.get_logs(30):
            level = entry["level"]
            style = {"INFO": "green", "WARN": "yellow", "ERROR": "red"}.get(level, "dim")
            repo = f"[bold cyan]{entry['repo']}[/] " if entry.get("repo") else ""
            self.logs_widget().write_line(
                f"[dim]{entry['ts']}[/] [{style}]{level:5s}[/] {repo}{entry['message']}"
            )

    # ---------- background sync ----------

    def action_backup_all(self) -> None:
        self._start_sync(sync.sync_repo, sync.sync_all, "all")

    def action_pull_all(self) -> None:
        self._start_sync(sync.pull_repo, sync.pull_all, "all")

    def _start_sync(self, run_one, run_all, target: str) -> None:
        if self._busy:
            self.notify("sync already running", severity="warning")
            return
        cfg = config.load()
        if not cfg["repos"]:
            self.notify("no repos configured — run: tidy add <path>", severity="error")
            return
        self._busy = True
        self.busy_widget().add_class("busy")
        run_in_background(
            self._run_sync,
            lambda result: self.call_from_thread(self._sync_finished, result),
            run_one,
            run_all,
            cfg,
            target,
        )

    @staticmethod
    def _run_sync(run_one, run_all, cfg: dict, target: str) -> list[dict]:
        if target == "all":
            return run_all(cfg)["results"]
        repo = repos.find_repo(cfg, target)
        if repo is None:
            return [{"ok": False, "message": f"repo not found: {target}"}]
        return [run_one(cfg, repo)]

    def _sync_finished(self, results: list[dict]) -> None:
        self._busy = False
        self.busy_widget().remove_class("busy")
        self.last_results = results
        for result in results:
            marker = "✓" if result["ok"] else "✗"
            style = "green" if result["ok"] else "red"
            self.logs_widget().write_line(f"[{style}]{marker}[/] {result['message']}")
        self.refresh_repos()

    # ---------- actions ----------

    def action_refresh(self) -> None:
        self.refresh_all()
        self.notify("refreshed")

    def action_cycle_theme(self) -> None:
        cfg = config.load()
        next_theme = cycle_theme(cfg["theme"])
        cfg["theme"] = next_theme
        config.save(cfg)
        self.refresh_repos()
        self.logs_widget().write_line(f"theme → [bold]{next_theme}[/]")
        self.notify(f"theme: {next_theme}")

    def on_list_view_selected(self, event) -> None:
        repo_id = getattr(event.item, "repo_id", None)
        if repo_id:
            self._start_sync(sync.sync_repo, sync.sync_all, repo_id)
