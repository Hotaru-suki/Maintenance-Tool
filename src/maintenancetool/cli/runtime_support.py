from __future__ import annotations

import os
from contextvars import ContextVar

from rich.console import Console

from maintenancetool.core.runtime_paths import get_runtime_workspace
from maintenancetool.ui.admin import is_admin_session

console = Console()
DEFAULT_WORKSPACE = get_runtime_workspace()
ADVANCED_CLI_GUARD_ENABLED: ContextVar[bool] = ContextVar(
    "advanced_cli_guard_enabled",
    default=True,
)


def is_windows_runtime() -> bool:
    return os.name == "nt"


def require_advanced_cli(command_name: str) -> None:
    if not ADVANCED_CLI_GUARD_ENABLED.get():
        return
    if not is_windows_runtime():
        return
    if is_admin_session():
        return
    raise SystemExit(print_advanced_cli_blocked(command_name))


def print_advanced_cli_blocked(command_name: str) -> int:
    console.print(
        f"[red]{command_name} is available only in advanced mode when running as Administrator on Windows.[/red]"
    )
    console.print("[yellow]Use the ordinary launcher for guided operations.[/yellow]")
    return 1
