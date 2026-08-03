"""Rich terminal rendering helpers for the Tidy CLI."""

from __future__ import annotations

from contextlib import contextmanager

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tidy.logger import get_logs

__all__ = [
    "console",
    "print_error",
    "print_info",
    "print_ok",
    "print_sync_result",
    "print_warn",
    "render_status",
    "status",
]

console = Console()


def print_ok(message: str) -> None:
    console.print(f"[bold green]✓[/] {message}")


def print_warn(message: str) -> None:
    console.print(f"[bold yellow]⚠[/] {message}")


def print_error(message: str) -> None:
    console.print(f"[bold red]✗[/] {message}")


def print_info(message: str) -> None:
    console.print(message)


@contextmanager
def status(text: str):
    with console.status(text, spinner="dots"):
        yield


def print_sync_result(result: dict) -> None:
    if result["ok"]:
        console.print(f"[bold green]✓[/] {result['message']}")
    else:
        console.print(f"[bold red]✗[/] {result['message']}")


def _last_activity(repo_id: str) -> tuple[str | None, str | None]:
    for entry in reversed(get_logs(200)):
        if entry.get("repo") == repo_id:
            return entry.get("level"), entry.get("message")
    return None, None


def _level_style(level: str | None) -> str:
    return {"INFO": "green", "WARN": "yellow", "ERROR": "red"}.get(level or "", "dim")


def render_status(cfg: dict) -> None:
    table = Table(title="TIDY — status", show_lines=False)
    table.add_column("Repo", style="bold cyan")
    table.add_column("Path")
    table.add_column("Schedules", style="magenta")
    table.add_column("Remote")
    table.add_column("Last activity")

    for repo in cfg["repos"]:
        times = ", ".join(s["time"] for s in repo["schedules"]) or "—"
        remote = "✓" if repo.get("remote") else "—"
        level, message = _last_activity(repo["id"])
        activity = f"[{_level_style(level)}]{message}[/]" if message else "—"
        table.add_row(repo["id"], repo["path"], times, remote, activity)

    console.print(table)

    stats = cfg["stats"]
    lines = [
        f"repos: [bold cyan]{len(cfg['repos'])}[/] · pushes: [bold green]{stats.get('total_pushes', 0)}[/]",
        f"last run: {stats.get('last_run') or 'never'}",
    ]
    if stats.get("last_error"):
        lines.append(f"last error: [bold red]{stats['last_error']}[/]")
    console.print(Panel("\n".join(lines), title="summary", border_style="dim"))
