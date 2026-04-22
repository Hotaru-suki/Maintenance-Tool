from __future__ import annotations

from pathlib import Path

import typer

from maintenancetool.cli.runtime import build_runtime_app
from maintenancetool.cli.runtime import console
from maintenancetool.dev.sandbox import build_sandbox_path_resolver, validate_sandbox_root
from maintenancetool.services.analyze import run_analyze_service
from maintenancetool.services.cleanup import run_cleanup_service


def verify_sandbox_command(
    sandbox_root: str = typer.Option(
        ...,
        envvar="MAINTENANCETOOL_SANDBOX_ROOT",
        help="Sandbox root with sentinel file",
    ),
    apply_quarantine: bool = typer.Option(
        False,
        help="Apply sandbox quarantine after verification planning",
    ),
) -> None:
    sandbox_path = validate_sandbox_root(Path(sandbox_root))
    config_dir = sandbox_path / "config"
    state_dir = sandbox_path / "state"
    report_dir = sandbox_path / "reports"
    quarantine_dir = sandbox_path / ".quarantine"
    sandbox_resolver = build_sandbox_path_resolver(sandbox_path)

    console.print("[bold cyan]Sandbox verification started[/bold cyan]")
    analyze_result = run_analyze_service(
        config_path=config_dir,
        state_path=state_dir,
        local_path_resolver=sandbox_resolver,
    )
    cleanup_result = run_cleanup_service(
        config_path=config_dir,
        report_dir=report_dir,
        quarantine_dir=quarantine_dir,
        mode="quarantine" if apply_quarantine else "dry-run",
        apply=apply_quarantine,
        local_path_resolver=sandbox_resolver,
    )
    plan = cleanup_result.plan
    console.print(f"sandbox_root={sandbox_path}")
    console.print(f"snapshot entries = {len(analyze_result.entries)}")
    console.print(f"pending suggestions = {len(analyze_result.suggestions)}")
    console.print(f"{plan.mode} items = {len(plan.items)}")
    console.print(f"{plan.mode} report = {cleanup_result.report_path}")
    if cleanup_result.execution is not None:
        execution = cleanup_result.execution
        applied = [item for item in execution.items if item.outcome == "applied"]
        skipped = [item for item in execution.items if item.outcome == "skipped"]
        failed = [item for item in execution.items if item.outcome == "failed"]
        console.print(f"applied items = {len(applied)}")
        console.print(f"skipped items = {len(skipped)}")
        console.print(f"failed items = {len(failed)}")
        console.print(f"execution report = {cleanup_result.execution_report_path}")
    console.print("[green]Sandbox verification complete.[/green]")


app = build_runtime_app(restrict_advanced_cli=False)
app.command(name="verify-sandbox")(verify_sandbox_command)
