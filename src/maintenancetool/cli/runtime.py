from __future__ import annotations

import os
from pathlib import Path
from contextvars import ContextVar

import typer
from rich.console import Console

from maintenancetool.core.path_adapter import resolve_local_path
from maintenancetool.core.runtime_paths import get_runtime_workspace
from maintenancetool.services.analyze import run_analyze_service
from maintenancetool.services.cleanup import run_cleanup_service
from maintenancetool.services.config import run_config_check_service
from maintenancetool.services.feedback import dispatch_feedback, run_feedback_service
from maintenancetool.services.quarantine import run_restore_quarantine_service
from maintenancetool.services.review import run_review_pending_service
from maintenancetool.services.update import get_update_status, open_update_download
from maintenancetool.ui.admin import is_admin_session
from maintenancetool.ui.confirm import prompt_yes_no
from maintenancetool.ui.launcher import run_launcher
from maintenancetool.ui.menu import run_menu

console = Console()
DEFAULT_WORKSPACE = get_runtime_workspace()
ADVANCED_CLI_GUARD_ENABLED: ContextVar[bool] = ContextVar(
    "advanced_cli_guard_enabled",
    default=True,
)


def launch_default_launcher() -> None:
    run_launcher(
        console,
        config_dir=str(DEFAULT_WORKSPACE.config_dir),
        state_dir=str(DEFAULT_WORKSPACE.state_dir),
        report_dir=str(DEFAULT_WORKSPACE.report_dir),
        quarantine_dir=str(DEFAULT_WORKSPACE.quarantine_dir),
    )


def launch_default_menu() -> None:
    run_menu(
        console,
        config_dir=str(DEFAULT_WORKSPACE.config_dir),
        state_dir=str(DEFAULT_WORKSPACE.state_dir),
        report_dir=str(DEFAULT_WORKSPACE.report_dir),
        quarantine_dir=str(DEFAULT_WORKSPACE.quarantine_dir),
    )


def menu_command(
    config_dir: str = typer.Option(str(DEFAULT_WORKSPACE.config_dir), help="Configuration directory"),
    state_dir: str = typer.Option(str(DEFAULT_WORKSPACE.state_dir), help="State directory"),
    report_dir: str = typer.Option(str(DEFAULT_WORKSPACE.report_dir), help="Report directory"),
    quarantine_dir: str = typer.Option(str(DEFAULT_WORKSPACE.quarantine_dir), help="Quarantine directory"),
) -> None:
    run_menu(
        console,
        config_dir=config_dir,
        state_dir=state_dir,
        report_dir=report_dir,
        quarantine_dir=quarantine_dir,
    )


def launcher_command(
    config_dir: str = typer.Option(str(DEFAULT_WORKSPACE.config_dir), help="Configuration directory"),
    state_dir: str = typer.Option(str(DEFAULT_WORKSPACE.state_dir), help="State directory"),
    report_dir: str = typer.Option(str(DEFAULT_WORKSPACE.report_dir), help="Report directory"),
    quarantine_dir: str = typer.Option(str(DEFAULT_WORKSPACE.quarantine_dir), help="Quarantine directory"),
) -> None:
    run_launcher(
        console,
        config_dir=config_dir,
        state_dir=state_dir,
        report_dir=report_dir,
        quarantine_dir=quarantine_dir,
    )


def analyze_command(
    config_dir: str = typer.Option(str(DEFAULT_WORKSPACE.config_dir), help="Configuration directory"),
    state_dir: str = typer.Option(str(DEFAULT_WORKSPACE.state_dir), help="State directory"),
) -> None:
    _require_advanced_cli("analyze")
    result = run_analyze_service(
        config_path=Path(config_dir),
        state_path=Path(state_dir),
        local_path_resolver=resolve_local_path,
    )
    console.print("[bold cyan]Analyze complete[/bold cyan]")
    console.print(f"config_dir={config_dir}")
    console.print(f"state_dir={state_dir}")
    console.print(f"fixedTargets count = {len(result.configs['fixedTargets'])}")
    console.print(f"denyRules count = {len(result.configs['denyRules'])}")
    console.print(f"snapshot entries = {len(result.entries)}")
    console.print(f"pending suggestions = {len(result.suggestions)}")
    if result.suggestions:
        grouped: dict[str, int] = {}
        for item in result.suggestions:
            key = item.hitRule or "unknown"
            grouped[key] = grouped.get(key, 0) + 1
        console.print(
            "pending by hit rule = "
            + ", ".join(
                f"{name}:{count}"
                for name, count in sorted(grouped.items(), key=lambda pair: (-pair[1], pair[0]))[:5]
            )
        )
    console.print(f"snapshot_path={result.snapshot_path}")
    console.print(f"pending_path={result.pending_path}")


def review_pending_command(
    config_dir: str = typer.Option(str(DEFAULT_WORKSPACE.config_dir), help="Configuration directory"),
    state_dir: str = typer.Option(str(DEFAULT_WORKSPACE.state_dir), help="State directory"),
    accept_all: bool = typer.Option(False, help="Accept all pending suggestions"),
    accept: list[str] = typer.Option(None, "--accept", help="Accept specific pending suggestion ids"),
    reject: list[str] = typer.Option(None, "--reject", help="Reject specific pending suggestion ids"),
) -> None:
    _require_advanced_cli("review-pending")
    result = run_review_pending_service(
        config_path=Path(config_dir),
        state_path=Path(state_dir),
        accept_all=accept_all,
        accept_ids=set(accept or []),
        reject_ids=set(reject or []),
    )
    if result.pending_state is None:
        console.print("[yellow]No pending suggestions to review.[/yellow]")
        return
    console.print(f"accepted suggestions = {len(result.accepted)}")
    console.print(f"rejected suggestions = {len(result.rejected)}")
    console.print(f"remaining suggestions = {len(result.remaining)}")
    console.print(f"fixedTargets path = {result.fixed_targets_path}")
    console.print(f"pending path = {result.pending_path}")


def config_check_command(
    config_dir: str = typer.Option(str(DEFAULT_WORKSPACE.config_dir), help="Configuration directory"),
) -> None:
    _require_advanced_cli("config-check")
    result = run_config_check_service(Path(config_dir))
    if result.summary is not None:
        console.print(f"profile={result.summary['profile']}")
        console.print(f"fixed_targets={result.summary['fixed_targets_count']}")
        console.print(f"deny_rules={result.summary['deny_rules_count']}")
        console.print(f"enabled_fixed_targets={result.summary['enabled_fixed_targets']}")
        console.print(f"enabled_deny_rules={result.summary['enabled_deny_rules']}")
        console.print(f"scope_hints={','.join(result.summary['scope_hints']) or 'none'}")
        if "discover_root_source" in result.summary:
            console.print(f"discover_root_source={result.summary['discover_root_source']}")
            console.print(f"discover_root_count={result.summary['discover_root_count']}")
            console.print(f"explicit_override_count={result.summary['explicit_override_count']}")
            console.print(f"default_fallback_root_count={result.summary['default_fallback_root_count']}")
            console.print(f"default_environment_ready={result.summary['default_environment_ready']}")
        if "hit_rules_total" in result.summary:
            console.print(f"hit_rules_total={result.summary['hit_rules_total']}")
            console.print(f"hit_rules_name={result.summary['hit_rules_name']}")
            console.print(f"hit_rules_path_fragment={result.summary['hit_rules_path_fragment']}")
    for file_info in result.files:
        console.print(
            f"{file_info['name']}: exists={file_info['exists']} valid_json={file_info['valid_json']} "
            f"kind={file_info['actual_kind'] or 'n/a'} count={file_info['item_count'] if file_info['item_count'] is not None else 'n/a'}"
        )
        for note in file_info["notes"]:
            console.print(f"  note: {note}")
        for error in file_info["errors"]:
            console.print(f"  error: {error}")
    for warning in result.warnings:
        console.print(f"[yellow]warning:[/yellow] {warning}")
    if result.ok:
        console.print("[green]Configuration check passed.[/green]")
        return
    console.print("[red]Configuration check failed.[/red]")
    for error in result.errors:
        console.print(f"- {error}")
    raise typer.Exit(code=1)


def feedback_command(
    config_dir: str = typer.Option(str(DEFAULT_WORKSPACE.config_dir), help="Configuration directory"),
    state_dir: str = typer.Option(str(DEFAULT_WORKSPACE.state_dir), help="State directory"),
    report_dir: str = typer.Option(str(DEFAULT_WORKSPACE.report_dir), help="Report directory"),
    category: str = typer.Option("issue", help="Feedback category"),
    title: str = typer.Option(..., help="Short feedback title"),
    details: str = typer.Option(..., help="Feedback details"),
    include_config: bool = typer.Option(False, help="Include config diagnostics in the generated email body"),
    open_target: bool = typer.Option(True, "--open-target/--no-open-target", help="Open the GitHub issue page, then fall back to email if needed"),
) -> None:
    _require_advanced_cli("feedback")
    result = run_feedback_service(
        feedback_dir=Path(report_dir) / "feedback",
        config_dir=Path(config_dir),
        state_dir=Path(state_dir),
        report_dir=Path(report_dir),
        category=category,
        title=title,
        details=details,
        include_config=include_config,
    )
    channel, opened = dispatch_feedback(result) if open_target else ("manual", False)
    console.print(f"feedback_subject={result.subject}", markup=False)
    console.print(f"feedback_issue_url={result.issue_url}", markup=False)
    console.print(f"feedback_email_url={result.email_url}", markup=False)
    console.print(f"feedback_channel={channel}", markup=False)
    console.print(f"feedback_dispatched={opened}", markup=False)


def check_update_command(
    state_dir: str = typer.Option(str(DEFAULT_WORKSPACE.state_dir), help="State directory"),
    open_browser: bool = typer.Option(False, help="Open the latest release download page when an update is available"),
) -> None:
    result = get_update_status(Path(state_dir), force_refresh=True)
    console.print(f"current_version={result.current_version}")
    console.print(f"latest_version={result.latest_version or 'unknown'}")
    console.print(f"checked_at={result.checked_at or 'n/a'}")
    console.print(f"release_url={result.release_url}")
    console.print(f"installer_url={result.installer_url or '-'}")
    console.print(f"update_available={result.update_available}")
    console.print(f"source={result.source}")
    if result.error:
        console.print(f"warning={result.error}")
    if open_browser and result.update_available:
        opened = open_update_download(result)
        console.print(f"opened_browser={opened}")


def restore_quarantine_command(
    quarantine_dir: str = typer.Option(str(DEFAULT_WORKSPACE.quarantine_dir), help="Quarantine directory"),
    report_dir: str = typer.Option(str(DEFAULT_WORKSPACE.report_dir), help="Directory for restore execution reports"),
    all_records: bool = typer.Option(False, "--all", help="Restore all active quarantine records"),
    record_id: list[str] = typer.Option(None, "--record-id", help="Restore specific quarantine record ids"),
) -> None:
    _require_advanced_cli("restore-quarantine")
    selected_ids = set(record_id or [])
    preview = run_restore_quarantine_service(
        quarantine_dir=Path(quarantine_dir),
        report_dir=Path(report_dir),
        record_ids=set(),
        apply=False,
    )
    if not preview.records and not selected_ids:
        console.print("[yellow]No active quarantine records found.[/yellow]")
        return

    if all_records:
        selected_ids = {record.recordId for record in preview.records}

    if not selected_ids:
        for record in preview.records:
            console.print(f"{record.recordId} {record.quarantinedAt} {record.sourcePath}")
        console.print("[yellow]No restore executed. Use --all or --record-id.[/yellow]")
        return

    result = run_restore_quarantine_service(
        quarantine_dir=Path(quarantine_dir),
        report_dir=Path(report_dir),
        record_ids=selected_ids,
        apply=True,
    )
    if result.execution is None:
        console.print("[yellow]No restore execution was performed.[/yellow]")
        return
    applied = [item for item in result.execution.items if item.outcome == "applied"]
    skipped = [item for item in result.execution.items if item.outcome == "skipped"]
    failed = [item for item in result.execution.items if item.outcome == "failed"]
    console.print(f"restored items = {len(applied)}")
    console.print(f"skipped items = {len(skipped)}")
    console.print(f"failed items = {len(failed)}")
    console.print(f"restore_report_path={result.report_path}")


def clean_command(
    config_dir: str = typer.Option(str(DEFAULT_WORKSPACE.config_dir), help="Configuration directory"),
    report_dir: str = typer.Option(str(DEFAULT_WORKSPACE.report_dir), help="Directory for cleanup plan reports"),
    quarantine_dir: str = typer.Option(str(DEFAULT_WORKSPACE.quarantine_dir), help="Directory used for quarantine apply"),
    mode: str = typer.Option("dry-run", help="Cleanup mode: dry-run, quarantine, or delete"),
    apply: bool = typer.Option(False, help="Apply quarantine or delete mode after generating the plan"),
    interactive: bool = typer.Option(False, help="Use interactive confirmations before applying cleanup"),
    confirm_delete: str | None = typer.Option(None, help="Required literal token DELETE when applying delete mode"),
) -> None:
    _require_advanced_cli("clean")
    if mode not in {"dry-run", "quarantine", "delete"}:
        raise typer.BadParameter("mode must be one of: dry-run, quarantine, delete")
    if apply and mode == "dry-run":
        raise typer.BadParameter("--apply is only supported with --mode quarantine or delete")
    if mode == "delete" and apply and not interactive:
        raise typer.BadParameter("delete apply requires --interactive")
    if mode == "delete" and apply and confirm_delete != "DELETE":
        raise typer.BadParameter("delete apply requires --confirm-delete DELETE")

    planned_result = run_cleanup_service(
        config_path=Path(config_dir),
        report_dir=Path(report_dir),
        quarantine_dir=Path(quarantine_dir),
        mode=mode,
        apply=False,
        delete_confirmation=confirm_delete,
        local_path_resolver=resolve_local_path,
    )
    plan = planned_result.plan
    allowed = [item for item in plan.items if item.allowed]
    blocked = [item for item in plan.items if not item.allowed]
    total_bytes = sum(item.sizeBytes for item in allowed)
    confirmed_target_ids = _collect_confirmed_target_ids(
        plan=plan,
        mode=mode,
        apply=apply,
        interactive=interactive,
    )
    if apply and interactive and confirmed_target_ids is None:
        result = planned_result
        console.print(f"mode={plan.mode}")
        console.print(f"plan items = {len(plan.items)}")
        console.print(f"allowed items = {len(allowed)}")
        console.print(f"blocked items = {len(blocked)}")
        console.print(f"planned bytes = {total_bytes}")
        console.print(f"report_path={result.report_path}")
        console.print("[yellow]Cleanup apply cancelled by user.[/yellow]")
        return

    result = run_cleanup_service(
        config_path=Path(config_dir),
        report_dir=Path(report_dir),
        quarantine_dir=Path(quarantine_dir),
        mode=mode,
        apply=apply,
        delete_confirmation=confirm_delete,
        confirmed_target_ids=confirmed_target_ids,
        local_path_resolver=resolve_local_path,
    )

    console.print(f"mode={plan.mode}")
    console.print(f"plan items = {len(plan.items)}")
    console.print(f"allowed items = {len(allowed)}")
    console.print(f"blocked items = {len(blocked)}")
    console.print(f"planned bytes = {total_bytes}")
    console.print(f"report_path={result.report_path}")
    if result.execution is None:
        console.print("[yellow]Cleanup plan generated only. No cleanup executed.[/yellow]")
        return

    execution = result.execution
    applied = [item for item in execution.items if item.outcome == "applied"]
    skipped = [item for item in execution.items if item.outcome == "skipped"]
    failed = [item for item in execution.items if item.outcome == "failed"]
    console.print(f"applied items = {len(applied)}")
    console.print(f"skipped items = {len(skipped)}")
    console.print(f"failed items = {len(failed)}")
    console.print(f"execution_report_path={result.execution_report_path}")
    console.print(f"[yellow]{mode.capitalize()} apply completed.[/yellow]")


def build_runtime_app(*, restrict_advanced_cli: bool = True) -> typer.Typer:
    app = typer.Typer(help="MaintenanceTool CLI")

    @app.callback()
    def app_callback() -> None:
        ADVANCED_CLI_GUARD_ENABLED.set(restrict_advanced_cli)

    app.command(name="launcher")(launcher_command)
    app.command(name="menu")(menu_command)
    app.command(name="analyze")(analyze_command)
    app.command(name="review-pending")(review_pending_command)
    app.command(name="config-check")(config_check_command)
    app.command(name="feedback")(feedback_command)
    app.command(name="check-update")(check_update_command)
    app.command(name="clean")(clean_command)
    app.command(name="restore-quarantine")(restore_quarantine_command)
    return app


app = build_runtime_app()


def _collect_confirmed_target_ids(
    *,
    plan,
    mode: str,
    apply: bool,
    interactive: bool,
) -> set[str] | None:
    if not apply:
        return set()

    allowed_items = [item for item in plan.items if item.allowed]
    if not allowed_items:
        return set()

    if not interactive:
        return set()

    total_bytes = sum(item.sizeBytes for item in allowed_items)
    proceed = prompt_yes_no(
        f"Proceed with {mode} for {len(allowed_items)} target(s), total {total_bytes} bytes?",
    )
    if not proceed:
        return None

    confirmed: set[str] = set()
    for item in allowed_items:
        needs_item_confirmation = mode == "delete" or item.requiresManualConfirm
        if not needs_item_confirmation:
            confirmed.add(item.targetId)
            continue
        confirmed_item = prompt_yes_no(
            f"Confirm {mode} for {item.path} ({item.sizeBytes} bytes)?",
        )
        if confirmed_item:
            confirmed.add(item.targetId)
    return confirmed


def _require_advanced_cli(command_name: str) -> None:
    if not ADVANCED_CLI_GUARD_ENABLED.get():
        return
    if not _is_windows_runtime():
        return
    if is_admin_session():
        return
    raise typer.Exit(
        code=_print_advanced_cli_blocked(command_name),
    )


def _print_advanced_cli_blocked(command_name: str) -> int:
    console.print(
        f"[red]{command_name} is available only in advanced mode when running as Administrator on Windows.[/red]"
    )
    console.print("[yellow]Use the ordinary user menu for guided operations.[/yellow]")
    return 1


def _is_windows_runtime() -> bool:
    return os.name == "nt"
