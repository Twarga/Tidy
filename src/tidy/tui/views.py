"""Widgets for the Tidy TUI: repo list and activity log."""

from __future__ import annotations

from textual.widgets import Label, ListItem, ListView, Log

__all__ = ["LogPanel", "RepoList"]


class RepoList(ListView):
    """Per-repo rows: id, path, schedules, remote status."""

    def update_repos(self, cfg: dict, accent: str) -> None:
        self.clear()
        if not cfg["repos"]:
            self.append(ListItem(Label("no repos configured — run: tidy add <path>")))
            return
        for repo in cfg["repos"]:
            times = " ".join(s["time"] for s in repo["schedules"]) or "no schedule"
            remote = "remote ✓" if repo.get("remote") else "no remote"
            remote_style = "green" if repo.get("remote") else "red"
            label = (
                f"[{accent}]{repo['id']}[/]  [dim]{repo['path']}[/]\n"
                f"[magenta]{times}[/]  [{remote_style}]{remote}[/]"
            )
            item = ListItem(Label(label))
            # Store the repo id on the item (unique ids would collide on re-render).
            item.repo_id = repo["id"]
            self.append(item)
        # Highlight the first row so Enter (select) works without navigation.
        if self.index is None and self.children:
            self.index = 0


class LogPanel(Log):
    """Live activity log with a max line count."""
