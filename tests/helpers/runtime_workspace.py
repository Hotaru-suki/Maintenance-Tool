from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from typer.testing import CliRunner


@dataclass(frozen=True, slots=True)
class RuntimeWorkspace:
    root: Path
    config_dir: Path
    state_dir: Path
    report_dir: Path
    quarantine_dir: Path

    def runtime_args(
        self,
        *,
        include_config: bool = True,
        include_state: bool = True,
        include_report: bool = True,
        include_quarantine: bool = True,
    ) -> list[str]:
        args: list[str] = []
        if include_config:
            args.extend(["--config-dir", str(self.config_dir)])
        if include_state:
            args.extend(["--state-dir", str(self.state_dir)])
        if include_report:
            args.extend(["--report-dir", str(self.report_dir)])
        if include_quarantine:
            args.extend(["--quarantine-dir", str(self.quarantine_dir)])
        return args


def create_runtime_workspace(root: Path) -> RuntimeWorkspace:
    config_dir = root / "config"
    state_dir = root / "state"
    report_dir = root / "reports"
    quarantine_dir = root / ".quarantine"
    config_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    return RuntimeWorkspace(
        root=root,
        config_dir=config_dir,
        state_dir=state_dir,
        report_dir=report_dir,
        quarantine_dir=quarantine_dir,
    )


def invoke_runtime_command(
    runner: CliRunner,
    app,
    workspace: RuntimeWorkspace,
    command: str,
    *extra_args: str,
    input_text: str | None = None,
    include_config: bool = True,
    include_state: bool = True,
    include_report: bool = True,
    include_quarantine: bool = True,
):
    return runner.invoke(
        app,
        [
            command,
            *workspace.runtime_args(
                include_config=include_config,
                include_state=include_state,
                include_report=include_report,
                include_quarantine=include_quarantine,
            ),
            *extra_args,
        ],
        input=input_text,
    )
