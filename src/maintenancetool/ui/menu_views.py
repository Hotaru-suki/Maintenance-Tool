from __future__ import annotations

from collections import Counter

from rich.console import Console
from rich.table import Table

from maintenancetool.core.discovery_roots import discover_root_summary
from maintenancetool.services.results import CleanupServiceResult


def render_main_menu(console: Console, *, show_advanced: bool, update_status) -> None:
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


def render_pending_review(console: Console, *, pending_state) -> None:
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


def render_cleanup_candidates(console: Console, *, title: str, candidates) -> None:
    table = Table(title=title)
    table.add_column("#")
    table.add_column("Path")
    table.add_column("Bytes")
    table.add_column("Risk")
    for index, item in enumerate(candidates, start=1):
        table.add_row(str(index), item.path, str(item.sizeBytes), item.riskLevel)
    console.print(table)


def render_plan_preview(
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


def render_analyze_summary(console: Console, *, result) -> None:
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
        render_analyze_rule_details(console, result=result)
    console.print(f"snapshot_path={result.snapshot_path}")
    console.print(f"pending_path={result.pending_path}")


def render_analyze_rule_details(console: Console, *, result) -> None:
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


def render_execution_summary(console: Console, result: CleanupServiceResult) -> None:
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


def render_restore_records(console: Console, *, records) -> None:
    table = Table(title="Restore From Quarantine")
    table.add_column("#")
    table.add_column("Quarantined At")
    table.add_column("Path")
    table.add_column("Bytes")
    for index, record in enumerate(records, start=1):
        table.add_row(str(index), record.quarantinedAt, record.sourcePath, str(record.sizeBytes))
    console.print(table)
