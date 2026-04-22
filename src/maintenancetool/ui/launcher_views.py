from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rich.console import Console

from maintenancetool import __version__
from maintenancetool.core.discovery_roots import discover_root_summary
from maintenancetool.services.update import UpdateStatus


def render_welcome(
    console: Console,
    *,
    advanced_enabled: bool,
    command_cards: list[object],
    state_path: Path,
    report_dir: Path,
    update_status: UpdateStatus | None = None,
) -> None:
    mode = "advanced" if advanced_enabled else "standard"
    console.print(f"MaintenanceTool v{__version__}")
    console.print(f"mode: {mode}")
    recent_actions = _build_recent_actions(state_path=state_path, report_dir=report_dir)
    console.print("recent:")
    if recent_actions:
        for action in recent_actions:
            console.print(f"- {action}")
    else:
        console.print("- no local activity recorded yet")
    if update_status is not None and update_status.update_available:
        latest = update_status.latest_version or "unknown"
        console.print(f"update: v{latest} available")
    console.print("type `/` for commands, `/status` for current state, `/exit` to quit")
    console.print()
    for card in command_cards:
        console.print(card)


def build_command_match_cards(
    *,
    commands: list[object],
    query: str,
    advanced_enabled: bool,
) -> list[object]:
    lines = [f"commands matching `{query}`"]
    if not commands:
        lines.append("- no matches")
        return ["\n".join(lines)]

    selected = commands[0]
    for index, command in enumerate(commands[:8]):
        prefix = ">" if index == 0 else " "
        visibility = " [advanced]" if command.advanced_only and advanced_enabled else ""
        lines.append(f"{prefix} {command.name:<20} {command.description}{visibility}")
    lines.append("")
    lines.append(build_command_detail_panel(selected, advanced_enabled=advanced_enabled))
    return ["\n".join(lines)]


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
    console.print("status")
    console.print(f"- mode: {'advanced' if advanced_enabled else 'standard'}")
    console.print(f"- config_dir: {config_path}")
    console.print(f"- state_dir: {state_path}")
    console.print(f"- report_dir: {report_dir}")
    console.print(f"- quarantine_dir: {quarantine_dir}")
    if config_summary is not None:
        console.print("config")
        console.print(f"- profile: {config_summary['profile']}")
        console.print(f"- discover_root_source: {config_summary.get('discover_root_source', 'n/a')}")
        console.print(f"- discover_root_count: {config_summary.get('discover_root_count', 0)}")
        console.print(f"- hit_rules_total: {config_summary.get('hit_rules_total', 0)}")
    console.print("pending")
    if pending_state is not None:
        console.print(f"- total: {pending_state.summary.totalSuggestions}")
        console.print(f"- by_hit_rule: {pending_state.summary.byHitRule}")
        console.print(f"- by_category: {pending_state.summary.byCategory}")
    else:
        console.print("- total: 0")
    console.print("learning")
    if learning_state is not None:
        console.print(f"- total: {learning_state.summary.totalDecisions}")
        console.print(f"- accepted: {learning_state.summary.acceptedCount}")
        console.print(f"- rejected: {learning_state.summary.rejectedCount}")
        console.print(f"- by_hit_rule: {learning_state.summary.byHitRule}")
    else:
        console.print("- total: 0")
    if update_status is not None:
        console.print(build_update_panel(update_status))


def render_analyze_result(console: Console, *, result, fixed_targets, discover_config) -> None:
    root_summary = discover_root_summary(fixed_targets, discover_config)
    console.print("analyze")
    console.print(f"- discover_root_source: {root_summary['discover_root_source']}")
    console.print(f"- discover_root_count: {root_summary['discover_root_count']}")
    console.print(f"- snapshot_entries: {len(result.entries)}")
    console.print(f"- pending_suggestions: {len(result.suggestions)}")
    console.print(f"- snapshot_path: {result.snapshot_path}")
    console.print(f"- pending_path: {result.pending_path}")
    if not result.suggestions:
        return
    grouped: dict[str, int] = {}
    for item in result.suggestions:
        key = item.hitRule or "unknown"
        grouped[key] = grouped.get(key, 0) + 1
    console.print("pending_by_hit_rule")
    for name, count in sorted(grouped.items(), key=lambda pair: (-pair[1], pair[0])):
        console.print(f"- {name}: {count}")
    console.print("pending_preview")
    for item in result.suggestions[:8]:
        console.print(
            f"- {item.path} | action={item.suggestedAction} | hit_rule={item.hitRule or '-'}"
        )


def render_cleanup_plan_summary(console: Console, *, title: str, result) -> None:
    allowed_items = [item for item in result.plan.items if item.allowed]
    blocked_items = [item for item in result.plan.items if not item.allowed]
    console.print(title.lower())
    console.print(f"- mode: {result.plan.mode}")
    console.print(f"- total_items: {len(result.plan.items)}")
    console.print(f"- allowed_items: {len(allowed_items)}")
    console.print(f"- blocked_items: {len(blocked_items)}")
    console.print(f"- report_path: {result.report_path}")
    if result.plan.items:
        console.print("candidates")
        for item in result.plan.items[:8]:
            console.print(
                f"- {item.path} | action={item.action} | risk={item.riskLevel} | allowed={'yes' if item.allowed else 'no'}"
            )


def render_post_action_hint(
    console: Console,
    *,
    primary: str,
    aliases: tuple[str, ...] = (),
    note: str,
    alternate: str | None = None,
    alternate_aliases: tuple[str, ...] = (),
) -> None:
    console.print("next")
    console.print(f"- primary: {primary}")
    console.print(f"- aliases: {', '.join(aliases) if aliases else '-'}")
    console.print(f"- note: {note}")
    if alternate is not None:
        console.print(f"- alternate: {alternate}")
        console.print(
            f"- alternate_aliases: {', '.join(alternate_aliases) if alternate_aliases else '-'}"
        )


def build_command_detail_panel(command, *, advanced_enabled: bool) -> str:
    mode_label = "advanced" if command.advanced_only else "standard"
    hidden_note = " hidden_in_current_mode=true" if command.advanced_only and not advanced_enabled else ""
    affects = ", ".join(command.affects) if command.affects else "read-only"
    aliases = ", ".join(command.aliases) if command.aliases else "-"
    return "\n".join(
        [
            f"selected: {command.name}",
            f"description: {command.details or command.description}",
            f"mode: {mode_label}{hidden_note}",
            f"aliases: {aliases}",
            f"affects: {affects}",
            f"recommended_next: {command.recommended_next or '-'}",
        ]
    )


def build_update_panel(update_status: UpdateStatus) -> str:
    status_line = "update available" if update_status.update_available else "up to date"
    latest_version = update_status.latest_version or "unknown"
    checked_at = update_status.checked_at or "not checked yet"
    lines = [
        "update",
        f"- status: {status_line}",
        f"- current: {update_status.current_version}",
        f"- latest: {latest_version}",
        f"- checked: {checked_at}",
        f"- source: {update_status.source}",
    ]
    if update_status.update_available:
        lines.append("- action: run `/check-update` to open the download page")
    elif update_status.error:
        lines.append(f"- error: {update_status.error}")
    return "\n".join(lines)


def build_key_value_panel(title: str, rows: list[tuple[str, object]], *, border_style: str) -> str:
    del border_style
    lines = [title.lower()]
    lines.extend(f"- {key}: {value}" for key, value in rows)
    return "\n".join(lines)


def _build_recent_actions(*, state_path: Path, report_dir: Path) -> list[str]:
    candidates = [
        ("analyze snapshot", state_path / "lastSnapshot.json"),
        ("pending suggestions", state_path / "pending.json"),
        ("learning decisions", state_path / "learningDecisions.json"),
        ("dry-run report", report_dir / "cleanup-plan-dry-run.json"),
        ("delete execution", report_dir / "cleanup-execution-delete.json"),
        ("quarantine execution", report_dir / "cleanup-execution-quarantine.json"),
        ("restore execution", report_dir / "restore-execution.json"),
    ]
    events: list[tuple[float, str]] = []
    for label, path in candidates:
        if not path.exists():
            continue
        try:
            timestamp = path.stat().st_mtime
        except OSError:
            continue
        rendered = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        events.append((timestamp, f"{rendered} {label}"))
    events.sort(reverse=True)
    return [label for _, label in events[:5]]
