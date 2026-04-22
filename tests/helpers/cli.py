from __future__ import annotations

import os

from typer.testing import CliRunner


runner = CliRunner()
TEST_SCOPE_NAME = "windows" if os.name == "nt" else "wsl"


__all__ = ["runner", "TEST_SCOPE_NAME"]
