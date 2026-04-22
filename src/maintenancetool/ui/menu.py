from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console

from maintenancetool.core.path_adapter import resolve_local_path
from maintenancetool.services.analyze import run_analyze_service
from maintenancetool.services.cleanup import run_cleanup_service
from maintenancetool.services.feedback import dispatch_feedback, run_feedback_service
from maintenancetool.services.quarantine import run_restore_quarantine_service
from maintenancetool.services.review import run_review_pending_service
from maintenancetool.services.update import get_update_status, open_update_download
from maintenancetool.ui.admin import is_admin_session
from maintenancetool.ui.confirm import prompt_yes_no
from maintenancetool.ui.menu_views import (
    render_analyze_summary,
    render_cleanup_candidates,
    render_execution_summary,
    render_main_menu,
    render_pending_review,
    render_plan_preview,
    render_restore_records,
)
from maintenancetool.ui.selection import parse_selection


@dataclass(frozen=True, slots=True)
class CleanupSelection:
    target_ids: set[str]
    total_bytes: int
    selected_count: int


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
            render_analyze_summary(console, result=result)
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
    render_main_menu(console, show_advanced=show_advanced, update_status=update_status)
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

    render_pending_review(console, pending_state=pending_state)

    selected = _prompt_index_selection(
        console,
        prompt_text="Select items to accept (a, 1,3, 2-4, n, q)",
        total_items=len(pending_state.suggestions),
        cancelled_message="Review cancelled.",
    )
    if selected is None:
        return

    accept_ids = {
        pending_state.suggestions[index - 1].id
        for index in sorted(selected)
    }

    rejected_selection = _prompt_index_selection(
        console,
        prompt_text="Select items to reject (n, 1,3, 2-4, q)",
        total_items=len(pending_state.suggestions),
        cancelled_message="Review cancelled.",
        default="n",
    )
    if rejected_selection is None:
        return

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

    render_cleanup_candidates(
        console,
        title=f"{'Delete Safe' if safe_only else mode.capitalize()} Candidates",
        candidates=candidates,
    )

    selection = _prompt_cleanup_selection(console, candidates=candidates)
    if selection is None:
        return

    if not prompt_yes_no(
        f"Proceed with {mode if not safe_only else 'safe delete'} for {selection.selected_count} target(s), total {selection.total_bytes} bytes?"
    ):
        console.print("[yellow]Cleanup cancelled.[/yellow]")
        return

    if mode == "dry-run" and not safe_only:
        render_plan_preview(
            console,
            result=planned_result,
            selected_count=selection.selected_count,
            total_bytes=selection.total_bytes,
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
            confirmed_target_ids=selection.target_ids,
            local_path_resolver=resolve_local_path,
        )
    render_execution_summary(console, result)


def _prompt_cleanup_selection(console: Console, *, candidates) -> CleanupSelection | None:
    selected = _prompt_index_selection(
        console,
        prompt_text="Select items (a, 1,3, 2-4, n, q)",
        total_items=len(candidates),
        cancelled_message="Cleanup cancelled.",
    )
    if selected is None:
        return None
    if not selected:
        console.print("[yellow]No targets selected.[/yellow]")
        return None
    return CleanupSelection(
        target_ids={candidates[index - 1].targetId for index in sorted(selected)},
        total_bytes=sum(candidates[index - 1].sizeBytes for index in sorted(selected)),
        selected_count=len(selected),
    )


def _prompt_index_selection(
    console: Console,
    *,
    prompt_text: str,
    total_items: int,
    cancelled_message: str,
    default: str | None = None,
) -> set[int] | None:
    while True:
        if default is None:
            raw = typer.prompt(prompt_text).strip()
        else:
            raw = typer.prompt(prompt_text, default=default).strip()
        try:
            return parse_selection(raw, total_items)
        except ValueError as exc:
            if str(exc) == "cancelled":
                console.print(f"[yellow]{cancelled_message}[/yellow]")
                return None
            console.print(f"[red]{exc}[/red]")


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

    render_restore_records(console, records=records)

    selected = _prompt_index_selection(
        console,
        prompt_text="Select records to restore (a, 1,3, 2-4, n, q)",
        total_items=len(records),
        cancelled_message="Restore cancelled.",
    )
    if selected is None:
        return

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
