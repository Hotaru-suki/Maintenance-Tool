from __future__ import annotations

import ctypes
import os
import traceback
import sys

from maintenancetool.core.runtime_paths import bootstrap_runtime_workspace
from maintenancetool.cli.runtime import app as runtime_app
from maintenancetool.cli.runtime import launch_default_launcher


def run() -> None:
    _set_console_title()
    bootstrap_runtime_workspace()
    if len(sys.argv) <= 1:
        launch_default_launcher()
        return
    runtime_app()


def main() -> int:
    try:
        run()
        return 0
    except Exception:
        traceback.print_exc()
        _pause_on_error()
        return 1


def _set_console_title() -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.kernel32.SetConsoleTitleW("MaintenanceTool")
    except Exception:
        return


def _pause_on_error() -> None:
    if not _should_pause_on_error():
        return
    try:
        input("MaintenanceTool failed to start. Press Enter to exit...")
    except EOFError:
        return


def _should_pause_on_error() -> bool:
    if os.name != "nt":
        return False
    return sys.stdin is not None and sys.stdin.isatty()


if __name__ == "__main__":
    raise SystemExit(main())
