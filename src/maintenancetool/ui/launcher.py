from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import typer
from rich.console import Console
from rich.table import Table

from maintenancetool.branding import PRODUCT_NAME
from maintenancetool.core.learning_decisions import load_learning_decision_state
from maintenancetool.core.path_adapter import resolve_local_path
from maintenancetool.core.pending import load_pending_state
from maintenancetool.services.analyze import run_analyze_service
from maintenancetool.services.cleanup import run_cleanup_service
from maintenancetool.services.config import run_config_check_service
from maintenancetool.services.feedback import dispatch_feedback, run_feedback_service
from maintenancetool.services.quarantine import run_restore_quarantine_service
from maintenancetool.services.update import get_update_status, open_update_download
from maintenancetool.ui.admin import is_admin_session
from maintenancetool.ui.confirm import prompt_yes_no
from maintenancetool.ui.launcher_views import (
    build_command_match_cards,
    build_key_value_panel,
    build_update_panel,
    render_analyze_result,
    render_cleanup_plan_summary,
    render_status_dashboard,
    render_welcome,
)
from maintenancetool.ui.review_flow import run_review_pending_interaction, run_review_promotion_interaction


@dataclass(frozen=True, slots=True)
class LauncherContext:
    console: Console
    config_path: Path
    state_path: Path
    report_dir: Path
    quarantine_dir: Path
    advanced_enabled: bool


@dataclass(frozen=True, slots=True)
class LauncherCommand:
    name: str
    description: str
    handler: Callable[[LauncherContext], bool]
    aliases: tuple[str, ...] = ()
    advanced_only: bool = False


def run_launcher(console: Console, *, config_dir: str, state_dir: str, report_dir: str, quarantine_dir: str) -> None:
    context = LauncherContext(
        console=console,
        config_path=Path(config_dir),
        state_path=Path(state_dir),
        report_dir=Path(report_dir),
        quarantine_dir=Path(quarantine_dir),
        advanced_enabled=is_admin_session(),
    )
    commands = build_launcher_commands()
    update_status = get_update_status(context.state_path, refresh_if_stale=True)
    render_welcome(
        console,
        advanced_enabled=context.advanced_enabled,
        command_cards=build_command_match_cards(
            commands=filter_launcher_commands(commands, "/", advanced_enabled=context.advanced_enabled),
            query="/",
            advanced_enabled=context.advanced_enabled,
        ),
        state_path=context.state_path,
        report_dir=context.report_dir,
        update_status=update_status,
    )
    if supports_prompt_toolkit_launcher():
        handled = _run_prompt_toolkit_launcher(context, commands)
        if handled:
            return

    while True:
        query = typer.prompt(">", default="/", show_default=False).strip() or "/"
        if query == "/":
            _render_command_matches(context, commands=commands, query=query)
            continue

        exact = resolve_exact_command(commands, query, advanced_enabled=context.advanced_enabled)
        if exact is not None:
            should_continue = exact.handler(context)
            if not should_continue:
                return
            continue

        matches = filter_launcher_commands(commands, query, advanced_enabled=context.advanced_enabled)
        if not matches:
            context.console.print("[yellow]no matching commands in current mode[/yellow]")
            continue
        _render_command_matches(context, commands=matches, query=query)


def supports_prompt_toolkit_launcher() -> bool:
    if importlib.util.find_spec("prompt_toolkit") is None:
        return False
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except Exception:
        return False


def build_launcher_commands() -> list[LauncherCommand]:
    return [
        LauncherCommand("/", "List commands", _handle_help, aliases=("/help", "/?")),
        LauncherCommand("/analyze", "Scan drives and find cleanup candidates", _handle_analyze, aliases=("/a",)),
        LauncherCommand("/analyze-fixed", "Scan fixed targets only", _handle_analyze_fixed, aliases=("/af",)),
        LauncherCommand("/review", "Accept or reject learned candidates", _handle_review, aliases=("/r",)),
        LauncherCommand("/promote-review", "Promote review-list targets to fixed targets", _handle_promote_review, aliases=("/pr",)),
        LauncherCommand("/dryrun", "Preview what can be cleaned", _handle_dryrun, aliases=("/d",)),
        LauncherCommand("/stage", "Move safe fixed targets to recoverable staged area", _handle_stage_safe, aliases=("/st",)),
        LauncherCommand("/restore", "Restore from staged area", _handle_restore, aliases=("/rs",)),
        LauncherCommand("/report", "Show config, state, report, and staged paths", _handle_report, aliases=("/rp",)),
        LauncherCommand("/status", "Show current scan and learning status", _handle_status, aliases=("/s",)),
        LauncherCommand("/update", "Check for updates", _handle_check_update, aliases=("/u",)),
        LauncherCommand("/feedback", "Send feedback", _handle_feedback, aliases=("/f",)),
        LauncherCommand("/config-check", "Validate config files", _handle_config_check, aliases=("/cc",), advanced_only=True),
        LauncherCommand("/advanced-dryrun", "Preview all allowed cleanup actions", _handle_advanced_dryrun, aliases=("/ad",), advanced_only=True),
        LauncherCommand("/exit", f"Exit {PRODUCT_NAME}", _handle_exit, aliases=("/q", "/quit")),
    ]


def filter_launcher_commands(
    commands: list[LauncherCommand],
    query: str,
    *,
    advanced_enabled: bool,
) -> list[LauncherCommand]:
    normalized = query.strip().lower()
    visible = [
        command
        for command in commands
        if advanced_enabled or not command.advanced_only
    ]
    if normalized in {"", "/"}:
        return visible

    def sort_key(command: LauncherCommand) -> tuple[int, int, str]:
        names = (command.name, *command.aliases)
        prefix_rank = 0 if any(name.lower().startswith(normalized) for name in names) else 1
        exact_rank = 0 if any(name.lower() == normalized for name in names) else 1
        return (exact_rank, prefix_rank, command.name)

    filtered = [
        command
        for command in visible
        if _command_matches(command, normalized)
    ]
    return sorted(filtered, key=sort_key)


def resolve_exact_command(
    commands: list[LauncherCommand],
    query: str,
    *,
    advanced_enabled: bool,
) -> LauncherCommand | None:
    normalized = query.strip().lower()
    for command in filter_launcher_commands(commands, normalized, advanced_enabled=advanced_enabled):
        if command.name.lower() == normalized:
            return command
        if any(alias.lower() == normalized for alias in command.aliases):
            return command
    return None


def _command_matches(command: LauncherCommand, normalized_query: str) -> bool:
    if command.name.lower().startswith(normalized_query):
        return True
    for alias in command.aliases:
        if alias.lower().startswith(normalized_query):
            return True
    if normalized_query.strip("/") in command.name.lower():
        return True
    return normalized_query.strip("/") in command.description.lower()


def _render_command_matches(context: LauncherContext, *, commands: list[LauncherCommand], query: str) -> None:
    context.console.print(
        *build_command_match_cards(
            commands=commands,
            query=query,
            advanced_enabled=context.advanced_enabled,
        ),
        sep="\n",
    )


def _run_prompt_toolkit_launcher(context: LauncherContext, commands: list[LauncherCommand]) -> bool:
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.application.current import get_app
        from prompt_toolkit.formatted_text import HTML
        from prompt_toolkit.key_binding import KeyBindings
    except Exception:
        return False

    state = {
        "query": "/",
        "selected_index": 0,
        "submitted": None,
    }

    def current_query() -> str:
        try:
            buffer_text = get_app().current_buffer.text
        except Exception:
            buffer_text = state["query"]
        return buffer_text.strip() or "/"

    def current_matches() -> list[LauncherCommand]:
        matches = filter_launcher_commands(commands, current_query(), advanced_enabled=context.advanced_enabled)
        return matches or []

    def toolbar_text() -> HTML:
        matches = current_matches()
        if not matches:
            return HTML("<style fg='ansiyellow'>no matching commands in current mode</style>")
        lines: list[str] = []
        for index, command in enumerate(matches[:8]):
            prefix = "&gt;" if index == state["selected_index"] else " "
            lines.append(f"{prefix} <b>{command.name}</b>  {command.description}")
        lines.append("<style fg='ansibrightblack'>type / to list commands, arrows to move, enter to run</style>")
        return HTML("\n".join(lines))

    bindings = KeyBindings()

    @bindings.add("up")
    def _move_up(event) -> None:
        matches = current_matches()
        if not matches:
            state["selected_index"] = 0
            return
        state["selected_index"] = max(0, state["selected_index"] - 1)
        event.app.invalidate()

    @bindings.add("down")
    def _move_down(event) -> None:
        matches = current_matches()
        if not matches:
            state["selected_index"] = 0
            return
        state["selected_index"] = min(len(matches[:8]) - 1, state["selected_index"] + 1)
        event.app.invalidate()

    @bindings.add("c-m")
    def _accept(event) -> None:
        matches = current_matches()
        if not matches:
            event.current_buffer.validate_and_handle()
            return
        selected = matches[min(state["selected_index"], len(matches[:8]) - 1)]
        state["submitted"] = selected.name
        event.app.exit(result=selected.name)

    session = PromptSession(
        message=HTML("<b><ansicyan>&gt;</ansicyan></b> "),
        key_bindings=bindings,
        bottom_toolbar=toolbar_text,
    )

    while True:
        try:
            text = session.prompt(default="/")
        except (EOFError, KeyboardInterrupt):
            context.console.print(f"[yellow]exiting {PRODUCT_NAME}[/yellow]")
            return True

        query = state["submitted"] or text.strip() or "/"
        state["submitted"] = None
        state["query"] = query
        state["selected_index"] = 0
        if query == "/":
            _render_command_matches(context, commands=filter_launcher_commands(commands, query, advanced_enabled=context.advanced_enabled), query=query)
            continue

        exact = resolve_exact_command(commands, query, advanced_enabled=context.advanced_enabled)
        if exact is not None:
            should_continue = exact.handler(context)
            if not should_continue:
                return True
            continue

        matches = filter_launcher_commands(commands, query, advanced_enabled=context.advanced_enabled)
        if not matches:
            context.console.print("[yellow]no matching commands in current mode[/yellow]")
            continue
        _render_command_matches(context, commands=matches, query=query)


def _handle_help(context: LauncherContext) -> bool:
    _render_command_matches(
        context,
        commands=filter_launcher_commands(build_launcher_commands(), "/", advanced_enabled=context.advanced_enabled),
        query="/",
    )
    return True


def _handle_status(context: LauncherContext) -> bool:
    config_result = run_config_check_service(context.config_path)
    pending_state = load_pending_state(context.state_path / "pending.json")
    learning_state = load_learning_decision_state(context.state_path / "learningDecisions.json")
    render_status_dashboard(
        context.console,
        advanced_enabled=context.advanced_enabled,
        config_path=context.config_path,
        state_path=context.state_path,
        report_dir=context.report_dir,
        quarantine_dir=context.quarantine_dir,
        config_summary=config_result.summary,
        pending_state=pending_state,
        learning_state=learning_state,
        update_status=get_update_status(context.state_path, refresh_if_stale=True),
    )
    return True


def _handle_analyze(context: LauncherContext) -> bool:
    with context.console.status("Scanning discover roots..."):
        result = run_analyze_service(
            config_path=context.config_path,
            state_path=context.state_path,
            discover_mode="full",
            local_path_resolver=resolve_local_path,
        )
    render_analyze_result(
        context.console,
        result=result,
        fixed_targets=[*result.configs["fixedTargets"], *result.configs["reviewTargets"]],
        discover_config=result.configs["discover"],
    )
    if result.suggestions:
        if prompt_yes_no(f"Review {len(result.suggestions)} pending learning suggestion(s) now?"):
            run_review_pending_interaction(context.console, config_path=context.config_path, state_path=context.state_path)
            return True
        return True
    return True


def _handle_analyze_fixed(context: LauncherContext) -> bool:
    with context.console.status("Scanning fixed targets..."):
        result = run_analyze_service(
            config_path=context.config_path,
            state_path=context.state_path,
            discover_mode="fixed-only",
            local_path_resolver=resolve_local_path,
        )
    render_analyze_result(
        context.console,
        result=result,
        fixed_targets=[*result.configs["fixedTargets"], *result.configs["reviewTargets"]],
        discover_config=result.configs["discover"],
    )
    return True


def _handle_review(context: LauncherContext) -> bool:
    run_review_pending_interaction(context.console, config_path=context.config_path, state_path=context.state_path)
    return True


def _handle_promote_review(context: LauncherContext) -> bool:
    run_review_promotion_interaction(context.console, config_path=context.config_path)
    return True


def _handle_dryrun(context: LauncherContext) -> bool:
    result = run_cleanup_service(
        config_path=context.config_path,
        report_dir=context.report_dir,
        quarantine_dir=context.quarantine_dir,
        mode="dry-run",
        apply=False,
        include_review_targets=False,
        local_path_resolver=resolve_local_path,
    )
    render_cleanup_plan_summary(context.console, title="Dry-run Preview", result=result)
    return True


def _handle_stage_safe(context: LauncherContext) -> bool:
    preview_result = run_cleanup_service(
        config_path=context.config_path,
        report_dir=context.report_dir,
        quarantine_dir=context.quarantine_dir,
        mode="dry-run",
        apply=False,
        include_review_targets=False,
        local_path_resolver=resolve_local_path,
    )
    safe_items = [
        item for item in preview_result.plan.items
        if item.allowed and item.riskLevel == "low" and not item.requiresManualConfirm
    ]
    context.console.print(
        build_key_value_panel(
            "Stage Safe",
            [
                ("safe_stage_candidates", len(safe_items)),
                ("report_path", str(preview_result.report_path)),
            ],
            border_style="green",
        )
    )
    if safe_items:
        context.console.print("safe_stage_candidates")
        for item in safe_items[:8]:
            context.console.print(
                f"- {item.path} | bytes={item.sizeBytes} | category={item.category or '-'}"
            )
        total_bytes = sum(item.sizeBytes for item in safe_items)
        if prompt_yes_no(
            f"Move {len(safe_items)} safe target(s), total {total_bytes} bytes, to the recoverable staged area?"
        ):
            execution_result = run_cleanup_service(
                config_path=context.config_path,
                report_dir=context.report_dir,
                quarantine_dir=context.quarantine_dir,
                mode="quarantine",
                apply=True,
                include_review_targets=False,
                confirmed_target_ids={item.targetId for item in safe_items},
                local_path_resolver=resolve_local_path,
            )
            applied_items = [
                item for item in (execution_result.execution.items if execution_result.execution is not None else [])
                if item.outcome == "applied"
            ]
            skipped_items = [
                item for item in (execution_result.execution.items if execution_result.execution is not None else [])
                if item.outcome == "skipped"
            ]
            context.console.print(
                build_key_value_panel(
                    "Stage Safe Execution",
                    [
                        ("applied_items", len(applied_items)),
                        ("skipped_items", len(skipped_items)),
                        ("plan_report_path", str(execution_result.report_path)),
                        (
                            "execution_report_path",
                            str(execution_result.execution_report_path)
                            if execution_result.execution_report_path is not None
                            else "-",
                        ),
                    ],
                    border_style="green",
                )
            )
            for item in applied_items[:8]:
                context.console.print(f"- staged: {item.path}")
        else:
            context.console.print("[yellow]safe staging cancelled[/yellow]")
    return True


def _handle_restore(context: LauncherContext) -> bool:
    preview = run_restore_quarantine_service(
        quarantine_dir=context.quarantine_dir,
        report_dir=context.report_dir,
        record_ids=set(),
        apply=False,
        local_path_resolver=resolve_local_path,
    )
    context.console.print(
        build_key_value_panel(
            "Restore Quarantine",
            [
                ("active_records", len(preview.records)),
                ("staged_dir", str(context.quarantine_dir)),
                ("report_dir", str(context.report_dir)),
            ],
            border_style="cyan",
        )
    )
    if preview.records:
        restore_table = Table(title="Active Quarantine Records")
        restore_table.add_column("Record")
        restore_table.add_column("Source Path")
        restore_table.add_column("Bytes")
        for record in preview.records[:8]:
            restore_table.add_row(record.recordId, record.sourcePath, str(record.sizeBytes))
        context.console.print(restore_table)
    return True


def _handle_report(context: LauncherContext) -> bool:
    context.console.print(
        build_key_value_panel(
            "Runtime Paths",
            [
                ("config_dir", str(context.config_path)),
                ("state_dir", str(context.state_path)),
                ("report_dir", str(context.report_dir)),
                ("staged_dir", str(context.quarantine_dir)),
            ],
            border_style="blue",
        )
    )
    return True


def _handle_check_update(context: LauncherContext) -> bool:
    status = get_update_status(context.state_path, force_refresh=True)
    context.console.print(build_update_panel(status))
    if not status.update_available:
        return True

    if prompt_yes_no("Open the latest release download page now?"):
        opened = open_update_download(status)
        message = "Release page opened in your default browser." if opened else "Could not open the browser automatically."
    else:
        message = "Update detected. You can open `/update` again later."
    context.console.print(message)
    return True


def _handle_feedback(context: LauncherContext) -> bool:
    title = typer.prompt("Feedback title").strip()
    details = typer.prompt("Feedback details").strip()
    result = run_feedback_service(
        feedback_dir=context.report_dir / "feedback",
        config_dir=context.config_path,
        state_dir=context.state_path,
        report_dir=context.report_dir,
        category="issue",
        title=title,
        details=details,
        include_config=False,
    )
    channel, opened = dispatch_feedback(result)
    context.console.print(
        build_key_value_panel(
            "Feedback",
            [
                ("feedback_subject", result.subject),
                ("issue_url", result.issue_url),
                ("email_url", result.email_url),
                ("opened_channel", channel if opened else "manual"),
            ],
            border_style="magenta",
        )
    )
    return True


def _handle_config_check(context: LauncherContext) -> bool:
    result = run_config_check_service(context.config_path)
    rows: list[tuple[str, object]] = [("config_check_ok", result.ok)]
    if result.summary is not None:
        rows.extend(
            [
                ("profile", result.summary["profile"]),
                ("fixed_targets_count", result.summary.get("fixed_targets_count", 0)),
                ("discover_root_count", result.summary.get("discover_root_count", 0)),
                ("hit_rules_total", result.summary.get("hit_rules_total", 0)),
            ]
        )
    context.console.print(build_key_value_panel("Config Check", rows, border_style="cyan"))
    if result.warnings:
        warning_table = Table(title="Warnings")
        warning_table.add_column("Message")
        for warning in result.warnings:
            warning_table.add_row(warning)
        context.console.print(warning_table)
    return True


def _handle_advanced_dryrun(context: LauncherContext) -> bool:
    result = run_cleanup_service(
        config_path=context.config_path,
        report_dir=context.report_dir,
        quarantine_dir=context.quarantine_dir,
        mode="dry-run",
        apply=False,
        include_review_targets=False,
        local_path_resolver=resolve_local_path,
    )
    render_cleanup_plan_summary(context.console, title="Advanced Dry-run", result=result)
    return True


def _handle_advanced_quarantine(context: LauncherContext) -> bool:
    result = run_cleanup_service(
        config_path=context.config_path,
        report_dir=context.report_dir,
        quarantine_dir=context.quarantine_dir,
        mode="quarantine",
        apply=False,
        include_review_targets=False,
        local_path_resolver=resolve_local_path,
    )
    render_cleanup_plan_summary(context.console, title="Advanced Quarantine Preview", result=result)
    return True


def _handle_exit(context: LauncherContext) -> bool:
    context.console.print(f"[yellow]exiting {PRODUCT_NAME}[/yellow]")
    return False
