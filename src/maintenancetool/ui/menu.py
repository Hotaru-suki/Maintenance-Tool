from __future__ import annotations

from collections import Counter
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from maintenancetool.core.discovery_roots import discover_root_summary
from maintenancetool.core.path_adapter import resolve_local_path
from maintenancetool.services.analyze import run_analyze_service
from maintenancetool.services.cleanup import run_cleanup_service
from maintenancetool.services.feedback import dispatch_feedback, run_feedback_service
from maintenancetool.services.quarantine import run_restore_quarantine_service
from maintenancetool.services.review import run_review_pending_service
from maintenancetool.services.results import CleanupServiceResult
from maintenancetool.services.update import get_update_status, open_update_download
from maintenancetool.ui.admin import is_admin_session
from maintenancetool.ui.confirm import prompt_yes_no
from maintenancetool.ui.selection import parse_selection


def run_menu(console: Console, *, config_dir: str, state_dir: str, report_dir: str, quarantine_dir: str) -> None:
    config_path = Path(config_dir)
    state_path = Path(state_dir)
    reports_path = Path(report_dir)
    quarantine_path = Path(quarantine_dir)
    update_status = get_update_status(state_path, refresh_if_stale=True)

    while True:
        choice = _prompt_main_menu(
            console,
            show_advanced=is_admin_session(),
            update_status=update_status,
        )
        if choice == "0":
            return
        if choice == "1":
            with console.status("Running analyze..."):
                result = run_analyze_service(
                    config_path=config_path,
                    state_path=state_path,
                    local_path_resolver=resolve_local_path,
                )
            console.print("[green]Analyze complete.[/green]")
            _render_analyze_summary(console, result=result)
            if not result.entries and not result.suggestions:
                guidance = (
                    "No scan results were produced. Discover roots are available, but no candidate matched the built-in hit rules."
                    if result.initial_discovery_ready
                    else "No scan results were produced. Check config/discover roots in the packaged template before retrying."
                )
                console.print(f"[yellow]{guidance}[/yellow]")
            elif result.suggestions and prompt_yes_no(
                f"Review {len(result.suggestions)} pending learning suggestion(s) now?"
            ):
                _run_review_pending_menu(console, config_path=config_path, state_path=state_path)
            if not _prompt_return(console):
                return
            continue
        if choice == "2":
            _run_review_pending_menu(console, config_path=config_path, state_path=state_path)
            if not _prompt_return(console):
                return
            continue
        if choice == "3":
            _run_cleanup_menu(
                console,
                config_path=config_path,
                report_dir=reports_path,
                quarantine_dir=quarantine_path,
                mode="dry-run",
                safe_only=False,
            )
            if not _prompt_return(console):
                return
            continue
        if choice == "4":
            _run_cleanup_menu(
                console,
                config_path=config_path,
                report_dir=reports_path,
                quarantine_dir=quarantine_path,
                mode="delete",
                safe_only=True,
            )
            if not _prompt_return(console):
                return
            continue
        if choice == "5":
            _run_restore_menu(
                console,
                report_dir=reports_path,
                quarantine_dir=quarantine_path,
            )
            if not _prompt_return(console):
                return
            continue
        if choice == "6":
            console.print(f"Reports directory: {reports_path}")
            if not _prompt_return(console):
                return
            continue
        if choice == "7":
            update_status = _run_update_menu(console, state_path=state_path)
            if not _prompt_return(console):
                return
            continue
        if choice == "8":
            _run_feedback_menu(
                console,
                config_path=config_path,
                state_path=state_path,
                report_dir=reports_path,
            )
            if not _prompt_return(console):
                return
            continue
        if choice == "9" and is_admin_session():
            _run_advanced_menu(console, config_path=config_path, state_path=state_path, report_dir=reports_path, quarantine_dir=quarantine_path)
            if not _prompt_return(console):
                return


def _prompt_main_menu(console: Console, *, show_advanced: bool, update_status) -> str:
    console.print("\n[bold cyan]MaintenanceTool[/bold cyan]")
    if update_status.update_available and update_status.latest_version is not None:
        console.print(f"[magenta]Update available: v{update_status.latest_version}[/magenta]")
    console.print("1. Analyze")
    console.print("2. Review Pending")
    console.print("3. Dry Run")
    console.print("4. Delete Safe")
    console.print("5. Restore From Quarantine")
    console.print("6. View Reports")
    console.print("7. Check Updates")
    console.print("8. Send Feedback")
    if show_advanced:
        console.print("9. Advanced")
    console.print("0. Exit")
    return typer.prompt("Select").strip()


def _run_update_menu(console: Console, *, state_path: Path):
    status = get_update_status(state_path, force_refresh=True)
    console.print(f"Current version: {status.current_version}")
    console.print(f"Latest version: {status.latest_version or 'unknown'}")
    console.print(f"Checked at: {status.checked_at or 'n/a'}")
    console.print(f"Release page: {status.release_url}")
    if not status.update_available:
        console.print("[green]No newer release was found.[/green]")
        return status
    console.print("[magenta]A newer release is available.[/magenta]")
    if prompt_yes_no("Open the latest release download page now?"):
        if open_update_download(status):
            console.print("[green]Release page opened in your default browser.[/green]")
        else:
            console.print("[yellow]Could not open the browser automatically.[/yellow]")
    return status


def _run_review_pending_menu(console: Console, *, config_path: Path, state_path: Path) -> None:
    pending_result = run_review_pending_service(
        config_path=config_path,
        state_path=state_path,
        accept_all=False,
        accept_ids=set(),
    )
    pending_state = pending_result.pending_state
    if pending_state is None or not pending_state.suggestions:
        console.print("[yellow]No pending suggestions to review.[/yellow]")
        return

    console.print(f"pending review items={len(pending_state.suggestions)}")
    console.print("fields=Action | Category | Hit Rule | Rule Reason | Bytes | Source | Path | Reason")
    first_item = pending_state.suggestions[0]
    console.print(
        "first item: "
        f"path={first_item.path} "
        f"category={first_item.category or '-'} "
        f"bytes={first_item.sizeBytes if first_item.sizeBytes is not None else '-'} "
        f"source={first_item.derivedFrom or '-'} "
        f"hit_rule={first_item.hitRule or '-'}"
    )
    table = Table(title="Pending Suggestions")
    table.add_column("#")
    table.add_column("Action")
    table.add_column("Category")
    table.add_column("Hit Rule")
    table.add_column("Rule Reason")
    table.add_column("Bytes")
    table.add_column("Source")
    table.add_column("Path")
    table.add_column("Reason")
    for index, item in enumerate(pending_state.suggestions, start=1):
        table.add_row(
            str(index),
            item.suggestedAction,
            item.category or "-",
            item.hitRule or "-",
            item.hitRuleReason or "-",
            str(item.sizeBytes) if item.sizeBytes is not None else "-",
            item.derivedFrom or "-",
            item.path,
            item.reason,
        )
    console.print(table)

    while True:
        raw = typer.prompt("Select items to accept (a, 1,3, 2-4, n, q)").strip()
        try:
            selected = parse_selection(raw, len(pending_state.suggestions))
        except ValueError as exc:
            if str(exc) == "cancelled":
                console.print("[yellow]Review cancelled.[/yellow]")
                return
            console.print(f"[red]{exc}[/red]")
            continue
        break

    accept_ids = {
        pending_state.suggestions[index - 1].id
        for index in sorted(selected)
    }

    while True:
        raw_reject = typer.prompt("Select items to reject (n, 1,3, 2-4, q)", default="n").strip()
        try:
            rejected_selection = parse_selection(raw_reject, len(pending_state.suggestions))
        except ValueError as exc:
            if str(exc) == "cancelled":
                console.print("[yellow]Review cancelled.[/yellow]")
                return
            console.print(f"[red]{exc}[/red]")
            continue
        break

    reject_ids = {
        pending_state.suggestions[index - 1].id
        for index in sorted(rejected_selection)
        if pending_state.suggestions[index - 1].id not in accept_ids
    }
    result = run_review_pending_service(
        config_path=config_path,
        state_path=state_path,
        accept_all=False,
        accept_ids=accept_ids,
        reject_ids=reject_ids,
    )
    console.print(f"[green]Accepted[/green] {len(result.accepted)} suggestion(s)")
    console.print(f"[yellow]Rejected[/yellow] {len(result.rejected)} suggestion(s)")
    console.print(f"Remaining suggestions = {len(result.remaining)}")


def _run_cleanup_menu(
    console: Console,
    *,
    config_path: Path,
    report_dir: Path,
    quarantine_dir: Path,
    mode: str,
    safe_only: bool,
) -> None:
    with console.status(f"Preparing {mode} plan..."):
        planned_result = run_cleanup_service(
            config_path=config_path,
            report_dir=report_dir,
            quarantine_dir=quarantine_dir,
            mode="dry-run" if safe_only else mode,
            apply=False,
            local_path_resolver=resolve_local_path,
        )
    plan = planned_result.plan
    candidates = [item for item in plan.items if item.allowed]
    if safe_only:
        candidates = [
            item for item in candidates
            if item.riskLevel == "low" and not item.requiresManualConfirm
        ]
    if not candidates:
        console.print("[yellow]No eligible targets.[/yellow]")
        return

    table = Table(title=f"{'Delete Safe' if safe_only else mode.capitalize()} Candidates")
    table.add_column("#")
    table.add_column("Path")
    table.add_column("Bytes")
    table.add_column("Risk")
    for index, item in enumerate(candidates, start=1):
        table.add_row(str(index), item.path, str(item.sizeBytes), item.riskLevel)
    console.print(table)

    while True:
        raw = typer.prompt("Select items (a, 1,3, 2-4, n, q)").strip()
        try:
            selected = parse_selection(raw, len(candidates))
        except ValueError as exc:
            if str(exc) == "cancelled":
                console.print("[yellow]Cleanup cancelled.[/yellow]")
                return
            console.print(f"[red]{exc}[/red]")
            continue
        break

    if not selected:
        console.print("[yellow]No targets selected.[/yellow]")
        return

    selected_ids = {candidates[index - 1].targetId for index in sorted(selected)}
    total_bytes = sum(candidates[index - 1].sizeBytes for index in sorted(selected))
    if not prompt_yes_no(f"Proceed with {mode if not safe_only else 'safe delete'} for {len(selected_ids)} target(s), total {total_bytes} bytes?"):
        console.print("[yellow]Cleanup cancelled.[/yellow]")
        return

    if mode == "dry-run" and not safe_only:
        _render_plan_preview(
            console,
            result=planned_result,
            selected_count=len(selected_ids),
            total_bytes=total_bytes,
        )
        return

    execute_mode = "delete" if safe_only else mode
    with console.status(f"Applying {execute_mode}..."):
        result = run_cleanup_service(
            config_path=config_path,
            report_dir=report_dir,
            quarantine_dir=quarantine_dir,
            mode=execute_mode,
            apply=True,
            delete_confirmation="DELETE" if execute_mode == "delete" else None,
            confirmed_target_ids=selected_ids,
            local_path_resolver=resolve_local_path,
        )
    _render_execution_summary(console, result)


def _render_plan_preview(
    console: Console,
    *,
    result: CleanupServiceResult,
    selected_count: int,
    total_bytes: int,
) -> None:
    console.print(f"mode={result.plan.mode}")
    console.print(f"selected items = {selected_count}")
    console.print(f"selected bytes = {total_bytes}")
    console.print(f"report_path={result.report_path}")
    console.print("[yellow]Dry-run preview generated only. No cleanup executed.[/yellow]")


def _render_analyze_summary(console: Console, *, result) -> None:
    root_summary = discover_root_summary(
        result.configs["fixedTargets"],
        result.configs["discover"],
    )
    console.print(
        f"discover roots={root_summary['discover_root_count']} "
        f"source={root_summary['discover_root_source']} "
        f"entries={len(result.entries)} pending={len(result.suggestions)}"
    )
    if result.suggestions:
        category_counts = Counter(item.category or "uncategorized" for item in result.suggestions)
        hit_rule_counts = Counter(item.hitRule or "unknown" for item in result.suggestions)
        top_categories = ", ".join(
            f"{name}:{count}"
            for name, count in sorted(category_counts.items(), key=lambda item: (-item[1], item[0]))[:3]
        )
        top_rules = ", ".join(
            f"{name}:{count}"
            for name, count in sorted(hit_rule_counts.items(), key=lambda item: (-item[1], item[0]))[:3]
        )
        console.print(f"pending categories={top_categories}")
        console.print(f"pending hit rules={top_rules}")
        _render_analyze_rule_details(console, result=result)
    console.print(f"snapshot_path={result.snapshot_path}")
    console.print(f"pending_path={result.pending_path}")


def _render_analyze_rule_details(console: Console, *, result) -> None:
    grouped: dict[str, list] = {}
    for item in result.suggestions:
        grouped.setdefault(item.hitRule or "unknown", []).append(item)

    table = Table(title="Analyze Rule Details")
    table.add_column("Hit Rule")
    table.add_column("Rule Reason")
    table.add_column("Count")
    table.add_column("Top Category")
    table.add_column("Example Path")
    for rule_name, items in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0]))[:5]:
        category_counts = Counter(item.category or "uncategorized" for item in items)
        top_category = sorted(category_counts.items(), key=lambda pair: (-pair[1], pair[0]))[0][0]
        example = sorted(items, key=lambda item: (-(item.sizeBytes or 0), item.path))[0]
        table.add_row(
            rule_name,
            example.hitRuleReason or "-",
            str(len(items)),
            top_category,
            example.path,
        )
    console.print(table)


def _render_execution_summary(console: Console, result: CleanupServiceResult) -> None:
    plan = result.plan
    console.print(f"mode={plan.mode}")
    console.print(f"report_path={result.report_path}")
    if result.execution is None:
        return
    execution = result.execution
    applied = [item for item in execution.items if item.outcome == "applied"]
    skipped = [item for item in execution.items if item.outcome == "skipped"]
    failed = [item for item in execution.items if item.outcome == "failed"]
    console.print(f"applied items = {len(applied)}")
    console.print(f"skipped items = {len(skipped)}")
    console.print(f"failed items = {len(failed)}")
    console.print(f"execution_report_path={result.execution_report_path}")


def _run_advanced_menu(console: Console, *, config_path: Path, state_path: Path, report_dir: Path, quarantine_dir: Path) -> None:
    console.print("\n[bold magenta]Advanced[/bold magenta]")
    console.print("1. Config Check")
    console.print("2. Advanced Dry Run")
    console.print("3. Advanced Quarantine")
    console.print("4. Restore From Quarantine")
    console.print("5. Back")
    choice = typer.prompt("Select").strip()
    if choice == "1":
        from maintenancetool.services.config import run_config_check_service

        result = run_config_check_service(config_path)
        if result.ok:
            console.print("[green]Configuration check passed.[/green]")
        else:
            console.print("[red]Configuration check failed.[/red]")
            for error in result.errors:
                console.print(f"- {error}")
    elif choice == "2":
        _run_cleanup_menu(
            console,
            config_path=config_path,
            report_dir=report_dir,
            quarantine_dir=quarantine_dir,
            mode="dry-run",
            safe_only=False,
        )
    elif choice == "3":
        _run_cleanup_menu(
            console,
            config_path=config_path,
            report_dir=report_dir,
            quarantine_dir=quarantine_dir,
            mode="quarantine",
            safe_only=False,
        )
    elif choice == "4":
        _run_restore_menu(console, report_dir=report_dir, quarantine_dir=quarantine_dir)


def _run_restore_menu(console: Console, *, report_dir: Path, quarantine_dir: Path) -> None:
    result = run_restore_quarantine_service(
        quarantine_dir=quarantine_dir,
        report_dir=report_dir,
        record_ids=set(),
        apply=False,
        local_path_resolver=resolve_local_path,
    )
    records = result.records
    if not records:
        console.print("[yellow]No active quarantine records.[/yellow]")
        return

    table = Table(title="Restore From Quarantine")
    table.add_column("#")
    table.add_column("Quarantined At")
    table.add_column("Path")
    table.add_column("Bytes")
    for index, record in enumerate(records, start=1):
        table.add_row(str(index), record.quarantinedAt, record.sourcePath, str(record.sizeBytes))
    console.print(table)

    while True:
        raw = typer.prompt("Select records to restore (a, 1,3, 2-4, n, q)").strip()
        try:
            selected = parse_selection(raw, len(records))
        except ValueError as exc:
            if str(exc) == "cancelled":
                console.print("[yellow]Restore cancelled.[/yellow]")
                return
            console.print(f"[red]{exc}[/red]")
            continue
        break

    if not selected:
        console.print("[yellow]No records selected.[/yellow]")
        return

    selected_ids = {records[index - 1].recordId for index in sorted(selected)}
    if not prompt_yes_no(f"Proceed with restore for {len(selected_ids)} record(s)?"):
        console.print("[yellow]Restore cancelled.[/yellow]")
        return

    execution_result = run_restore_quarantine_service(
        quarantine_dir=quarantine_dir,
        report_dir=report_dir,
        record_ids=selected_ids,
        apply=True,
        local_path_resolver=resolve_local_path,
    )
    if execution_result.execution is None:
        console.print("[yellow]No restore execution was performed.[/yellow]")
        return
    applied = [item for item in execution_result.execution.items if item.outcome == "applied"]
    skipped = [item for item in execution_result.execution.items if item.outcome == "skipped"]
    failed = [item for item in execution_result.execution.items if item.outcome == "failed"]
    console.print(f"restored items = {len(applied)}")
    console.print(f"skipped items = {len(skipped)}")
    console.print(f"failed items = {len(failed)}")
    console.print(f"restore_report_path={execution_result.report_path}")


def _run_feedback_menu(console: Console, *, config_path: Path, state_path: Path, report_dir: Path) -> None:
    category = typer.prompt("Feedback category", default="issue").strip()
    title = typer.prompt("Short title").strip()
    details = typer.prompt("Details").strip()
    result = run_feedback_service(
        feedback_dir=report_dir / "feedback",
        config_dir=config_path,
        state_dir=state_path,
        report_dir=report_dir,
        category=category,
        title=title,
        details=details,
        include_config=False,
    )
    channel, opened = dispatch_feedback(result)
    console.print(f"Feedback issue: {result.issue_url}")
    console.print(f"Fallback email: {result.email_url}")
    if opened:
        console.print(f"[green]Opened feedback target via {channel}.[/green]")
    else:
        console.print("[yellow]Could not open the feedback target automatically.[/yellow]")


def _prompt_return(console: Console) -> bool:
    console.print("1. Return to main menu")
    console.print("2. Exit")
    choice = typer.prompt("Select").strip()
    return choice != "2"
