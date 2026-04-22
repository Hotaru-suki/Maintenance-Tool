from __future__ import annotations

from pathlib import Path

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from maintenancetool import __version__
from maintenancetool.core.discovery_roots import discover_root_summary
from maintenancetool.services.update import UpdateStatus


def render_welcome(
    console: Console,
    *,
    advanced_enabled: bool,
    command_cards: list[object],
    update_status: UpdateStatus | None = None,
) -> None:
    mode = "Advanced" if advanced_enabled else "Standard"
    overview = Panel.fit(
        "\n".join(
            [
                f"[bold cyan]MaintenanceTool[/bold cyan] v{__version__}",
                f"[bold]Mode[/bold]: {mode}",
                "[bold]Launcher[/bold]: type `/` to list commands and narrow by typing.",
                "[bold]Recommended[/bold]: open `/status` first for a live dashboard.",
            ]
        ),
        title="Welcome",
        border_style="cyan",
    )
    quickstart = Panel.fit(
        "\n".join(
            [
                "Type `/status` for a dashboard of config, pending, and learning state.",
                "Type `/help` to reopen the command palette.",
                "Type `/exit` to close MaintenanceTool.",
                "Advanced commands appear only in administrator sessions.",
            ]
        ),
        title="Quick Start",
        border_style="blue",
    )
    cards: list[object] = [overview, quickstart, build_flow_panel()]
    if update_status is not None:
        cards.append(build_update_panel(update_status))
    console.print(Columns(cards, equal=True, expand=True))
    console.print(Columns(command_cards, equal=True, expand=True))


def build_command_match_cards(
    *,
    commands: list[object],
    query: str,
    advanced_enabled: bool,
) -> list[object]:
    table = Table(title=f"Launcher Matches: {query}")
    table.add_column("Command")
    table.add_column("Description")
    selected = commands[0] if commands else None
    for command in commands[:8]:
        label = f"[bold cyan]{command.name}[/bold cyan]" if selected is not None and command.name == selected.name else command.name
        table.add_row(label, command.description)
    renderables: list[object] = [table]
    if commands:
        renderables.append(build_command_detail_panel(commands[0], advanced_enabled=advanced_enabled))
    return renderables


def render_status_dashboard(
    console: Console,
    *,
    advanced_enabled: bool,
    config_path: Path,
    state_path: Path,
    report_dir: Path,
    quarantine_dir: Path,
    config_summary: dict[str, object] | None,
    pending_state,
    learning_state,
    update_status: UpdateStatus | None = None,
) -> None:
    config_table: Table | None = None
    console.print(
        Columns(
            [
                Panel.fit(
                    "\n".join(
                        [
                            "[bold cyan]MaintenanceTool Status[/bold cyan]",
                            f"[bold]Mode[/bold]: {'Advanced' if advanced_enabled else 'Standard'}",
                            f"[bold]Config[/bold]: {config_path}",
                            f"[bold]State[/bold]: {state_path}",
                            f"[bold]Reports[/bold]: {report_dir}",
                            f"[bold]Quarantine[/bold]: {quarantine_dir}",
                        ]
                    ),
                    title="Status",
                    border_style="cyan",
                ),
                build_flow_panel(),
            ],
            equal=True,
            expand=True,
        )
    )
    if config_summary is not None:
        config_table = Table(title="Configuration")
        config_table.add_column("Key")
        config_table.add_column("Value")
        config_table.add_row("profile", str(config_summary["profile"]))
        config_table.add_row("discover_root_source", str(config_summary.get("discover_root_source", "n/a")))
        config_table.add_row("discover_root_count", str(config_summary.get("discover_root_count", 0)))
        config_table.add_row("hit_rules_total", str(config_summary.get("hit_rules_total", 0)))
    pending_table = _build_pending_table(pending_state)
    learning_table = _build_learning_table(learning_state)
    console.print(Columns([pending_table, learning_table], equal=True, expand=True))
    lower_cards: list[object] = [build_recommended_next_panel(pending_state, learning_state)]
    if config_table is not None:
        lower_cards.insert(0, config_table)
    if update_status is not None:
        lower_cards.append(build_update_panel(update_status))
    console.print(Columns(lower_cards, equal=True, expand=True))


def render_analyze_result(console: Console, *, result, fixed_targets, discover_config) -> None:
    root_summary = discover_root_summary(fixed_targets, discover_config)
    console.print(
        build_key_value_panel(
            "Analyze Result",
            [
                ("discover_root_source", root_summary["discover_root_source"]),
                ("discover_root_count", root_summary["discover_root_count"]),
                ("snapshot_entries", len(result.entries)),
                ("pending_suggestions", len(result.suggestions)),
                ("snapshot_path", str(result.snapshot_path)),
                ("pending_path", str(result.pending_path)),
            ],
            border_style="green",
        )
    )
    if not result.suggestions:
        return
    grouped: dict[str, int] = {}
    for item in result.suggestions:
        key = item.hitRule or "unknown"
        grouped[key] = grouped.get(key, 0) + 1
    console.print(
        build_key_value_panel(
            "Pending By Hit Rule",
            [(name, count) for name, count in sorted(grouped.items(), key=lambda pair: (-pair[1], pair[0]))],
            border_style="yellow",
        )
    )
    suggestion_table = Table(title="Pending Suggestions")
    suggestion_table.add_column("Path")
    suggestion_table.add_column("Action")
    suggestion_table.add_column("Hit Rule")
    for item in result.suggestions[:8]:
        suggestion_table.add_row(item.path, item.suggestedAction, item.hitRule or "-")
    console.print(suggestion_table)


def render_cleanup_plan_summary(console: Console, *, title: str, result) -> None:
    allowed_items = [item for item in result.plan.items if item.allowed]
    blocked_items = [item for item in result.plan.items if not item.allowed]
    console.print(
        build_key_value_panel(
            title,
            [
                ("mode", result.plan.mode),
                ("total_items", len(result.plan.items)),
                ("allowed_items", len(allowed_items)),
                ("blocked_items", len(blocked_items)),
                ("report_path", str(result.report_path)),
            ],
            border_style="green" if result.plan.mode == "dry-run" else "yellow",
        )
    )
    if result.plan.items:
        preview_table = Table(title="Cleanup Candidates")
        preview_table.add_column("Path")
        preview_table.add_column("Action")
        preview_table.add_column("Risk")
        preview_table.add_column("Allowed")
        for item in result.plan.items[:8]:
            preview_table.add_row(item.path, item.action, item.riskLevel, "yes" if item.allowed else "no")
        console.print(preview_table)


def render_post_action_hint(
    console: Console,
    *,
    primary: str,
    aliases: tuple[str, ...] = (),
    note: str,
    alternate: str | None = None,
    alternate_aliases: tuple[str, ...] = (),
) -> None:
    lines = [
        f"[bold]Next[/bold]: {primary}",
        f"[bold]Aliases[/bold]: {', '.join(aliases) if aliases else '-'}",
        note,
    ]
    if alternate is not None:
        lines.append(f"[bold]Alternate[/bold]: {alternate}")
        lines.append(f"[bold]Alternate Aliases[/bold]: {', '.join(alternate_aliases) if alternate_aliases else '-'}")
    lines.append("Type `/` at any time to reopen the full command palette.")
    console.print(Panel.fit("\n".join(lines), title="Next Step", border_style="green"))


def build_command_detail_panel(command, *, advanced_enabled: bool) -> Panel:
    mode_label = "Advanced" if command.advanced_only else "Standard"
    affects = ", ".join(command.affects) if command.affects else "read-only"
    body = "\n".join(
        [
            f"[bold]{command.name}[/bold]",
            command.details or command.description,
            f"Mode: {mode_label}{' (hidden in current mode)' if command.advanced_only and not advanced_enabled else ''}",
            f"Aliases: {', '.join(command.aliases) if command.aliases else '-'}",
            f"Affects: {affects}",
            f"Recommended next: {command.recommended_next or '-'}",
        ]
    )
    return Panel.fit(body, title="Command Details", border_style="blue")


def build_recommended_next_panel(pending_state, learning_state) -> Panel:
    if pending_state is not None and pending_state.summary.totalSuggestions > 0:
        message = "Pending suggestions exist. Recommended next step: /review"
    elif learning_state is not None and learning_state.summary.totalDecisions > 0:
        message = "Learning history exists. Recommended next step: /dryrun"
    else:
        message = "No pending work yet. Recommended next step: /analyze"
    return Panel.fit(message, title="Recommended Next", border_style="green")


def build_flow_panel() -> Panel:
    return Panel.fit(
        "\n".join(
            [
                "[bold]/analyze[/bold] discover candidates and refresh pending suggestions",
                "[bold]/review[/bold] accept or reject learned targets",
                "[bold]/dryrun[/bold] preview cleanup candidates without changes",
                "[bold]/delete-safe[/bold] remove low-risk allowed targets",
                "[bold]/restore[/bold] recover quarantined items if needed",
                "[bold]/report[/bold] inspect generated state, reports, and feedback bundles",
            ]
        ),
        title="Primary Flow",
        border_style="blue",
    )


def build_update_panel(update_status: UpdateStatus) -> Panel:
    status_line = "Update available" if update_status.update_available else "Up to date"
    latest_version = update_status.latest_version or "unknown"
    checked_at = update_status.checked_at or "not checked yet"
    lines = [
        f"[bold]{status_line}[/bold]",
        f"Current: {update_status.current_version}",
        f"Latest: {latest_version}",
        f"Checked: {checked_at}",
        f"Source: {update_status.source}",
    ]
    if update_status.update_available:
        lines.append("Use `/check-update` to open the release download page.")
    elif update_status.error:
        lines.append(update_status.error)
    return Panel.fit(
        "\n".join(lines),
        title="Updates",
        border_style="magenta" if update_status.update_available else "cyan",
    )


def build_key_value_panel(title: str, rows: list[tuple[str, object]], *, border_style: str) -> Panel:
    body = "\n".join(f"[bold]{key}[/bold]: {value}" for key, value in rows)
    return Panel.fit(body, title=title, border_style=border_style)


def _build_pending_table(pending_state) -> Table:
    pending_table = Table(title="Pending")
    pending_table.add_column("Key")
    pending_table.add_column("Value")
    if pending_state is not None:
        pending_table.add_row("pending_total", str(pending_state.summary.totalSuggestions))
        pending_table.add_row("pending_by_hit_rule", str(pending_state.summary.byHitRule))
        pending_table.add_row("pending_by_category", str(pending_state.summary.byCategory))
    else:
        pending_table.add_row("pending_total", "0")
        pending_table.add_row("pending_by_hit_rule", "{}")
        pending_table.add_row("pending_by_category", "{}")
    return pending_table


def _build_learning_table(learning_state) -> Table:
    learning_table = Table(title="Learning")
    learning_table.add_column("Key")
    learning_table.add_column("Value")
    if learning_state is not None:
        learning_table.add_row("learning_total", str(learning_state.summary.totalDecisions))
        learning_table.add_row("learning_accepted", str(learning_state.summary.acceptedCount))
        learning_table.add_row("learning_rejected", str(learning_state.summary.rejectedCount))
        learning_table.add_row("learning_by_hit_rule", str(learning_state.summary.byHitRule))
    else:
        learning_table.add_row("learning_total", "0")
        learning_table.add_row("learning_accepted", "0")
        learning_table.add_row("learning_rejected", "0")
        learning_table.add_row("learning_by_hit_rule", "{}")
    return learning_table
