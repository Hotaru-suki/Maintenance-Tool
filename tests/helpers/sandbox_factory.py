from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


SANDBOX_SENTINEL = ".maintenance_sandbox_root"


@dataclass(slots=True)
class SandboxWorkspace:
    root: Path
    config_dir: Path
    state_dir: Path
    report_dir: Path
    quarantine_dir: Path
    fixtures_dir: Path

    def write_sentinel(self) -> Path:
        sentinel = self.root / SANDBOX_SENTINEL
        sentinel.write_text("", encoding="utf-8")
        return sentinel

    def create_file(self, relative_path: str, content: bytes = b"") -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path


class SandboxFactory:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self._counter = 0
        self._allocated: list[SandboxWorkspace] = []

    def create(self, *, prefix: str = "MaintenanceToolSandbox") -> SandboxWorkspace:
        self._counter += 1
        root = self.base_dir / f"{prefix}-{self._counter:04d}"
        workspace = SandboxWorkspace(
            root=root,
            config_dir=root / "config",
            state_dir=root / "state",
            report_dir=root / "reports",
            quarantine_dir=root / ".quarantine",
            fixtures_dir=root / "fixtures",
        )
        workspace.root.mkdir(parents=True, exist_ok=True)
        workspace.config_dir.mkdir(parents=True, exist_ok=True)
        workspace.state_dir.mkdir(parents=True, exist_ok=True)
        workspace.report_dir.mkdir(parents=True, exist_ok=True)
        workspace.quarantine_dir.mkdir(parents=True, exist_ok=True)
        workspace.fixtures_dir.mkdir(parents=True, exist_ok=True)
        workspace.write_sentinel()
        self._allocated.append(workspace)
        return workspace

    def cleanup(self) -> None:
        for workspace in reversed(self._allocated):
            if workspace.root.exists():
                shutil.rmtree(workspace.root)
        self._allocated.clear()
