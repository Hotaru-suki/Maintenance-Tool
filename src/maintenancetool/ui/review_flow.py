from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from maintenancetool.core.config_loader import load_all_configs
from maintenancetool.services.review import run_review_pending_service
from maintenancetool.services.review import run_review_promotion_service
from maintenancetool.ui.selection import parse_selection


def run_review_pending_interaction(console: Console, *, config_path: Path, state_path: Path) -> None:
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

    _render_pending_review(console, pending_state=pending_state)

    accept_ids, reject_ids = _collect_review_decisions(console, pending_state=pending_state)
    if accept_ids is None or reject_ids is None:
        return
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


def run_review_promotion_interaction(console: Console, *, config_path: Path) -> None:
    configs = load_all_configs(config_path)
    review_targets = configs["reviewTargets"]
    if not review_targets:
        console.print("[yellow]No review-list targets to promote.[/yellow]")
        return

    table = Table(title="Review Targets")
    table.add_column("#")
    table.add_column("ID")
    table.add_column("Category")
    table.add_column("Path")
    table.add_column("Note")
    for index, target in enumerate(review_targets, start=1):
        table.add_row(
            str(index),
            target.id or "-",
            target.category or "-",
            target.path,
            target.note or "-",
        )
    console.print(table)

    selected_indexes = _prompt_index_selection(
        console,
        prompt_text="Promote review target indexes ([a]ll, [n]one, [q]uit, e.g. 1,3-5)",
        total_items=len(review_targets),
        cancelled_message="Review target promotion cancelled.",
        default="n",
    )
    if selected_indexes is None or not selected_indexes:
        return
    selected_ids = {
        review_targets[index - 1].id
        for index in selected_indexes
        if review_targets[index - 1].id
    }
    result = run_review_promotion_service(
        config_path=config_path,
        promote_all=False,
        target_ids=selected_ids,
    )
    console.print(f"[green]Promoted[/green] {len(result.promoted)} review target(s)")
    console.print(f"Remaining review targets = {len(result.remaining_review_targets)}")


def _prompt_index_selection(
    console: Console,
    *,
    prompt_text: str,
    total_items: int,
    cancelled_message: str,
    default: str | None = None,
) -> set[int] | None:
    import typer

    while True:
        raw = typer.prompt(prompt_text, default=default, show_default=default is not None).strip().lower()
        if raw == "q":
            console.print(f"[yellow]{cancelled_message}[/yellow]")
            return None
        if raw == "n":
            return set()
        if raw == "a":
            return set(range(1, total_items + 1))
        try:
            return parse_selection(raw, total_items)
        except ValueError as exc:
            console.print(f"[yellow]{exc}[/yellow]")


def _collect_review_decisions(console: Console, *, pending_state) -> tuple[set[str] | None, set[str] | None]:
    import typer

    console.print(
        "Review options: "
        "[s]tep through items one by one, "
        "[a]ccept all, "
        "[r]eject all, "
        "[q]uit"
    )
    mode = typer.prompt("Choose review mode", default="s", show_default=True).strip().lower()
    if mode == "q":
        console.print("[yellow]Review cancelled.[/yellow]")
        return None, None
    if mode == "a":
        return {item.id for item in pending_state.suggestions}, set()
    if mode == "r":
        return set(), {item.id for item in pending_state.suggestions}
    if mode != "s":
        console.print("[yellow]Unknown review mode. Review cancelled.[/yellow]")
        return None, None

    accept_ids: set[str] = set()
    reject_ids: set[str] = set()
    for index, item in enumerate(pending_state.suggestions, start=1):
        target_label = _suggested_destination_label(item)
        console.print(
            f"[{index}/{len(pending_state.suggestions)}] "
            f"{item.path} -> {target_label} | category={item.category or '-'} | bytes={item.sizeBytes or 0}"
        )
        console.print(f"reason: {item.reason}")
        response = typer.prompt(
            "Apply this suggestion? [y]es / [n]o / [q]uit",
            default="n",
            show_default=True,
        ).strip().lower()
        if response == "q":
            console.print("[yellow]Review cancelled.[/yellow]")
            return None, None
        if response == "y":
            accept_ids.add(item.id)
        else:
            reject_ids.add(item.id)
    return accept_ids, reject_ids


def _suggested_destination_label(item) -> str:
    if item.suggestedAction == "addFixedTarget":
        return "safe fixed list"
    if item.suggestedAction == "addReviewTarget":
        return "review list"
    if item.suggestedAction == "addDenyRule":
        return "deny list"
    if item.suggestedAction == "retireFixedTarget":
        return "retire fixed target"
    return item.suggestedAction


def _render_pending_review(console: Console, *, pending_state) -> None:
    console.print(f"pending review items={len(pending_state.suggestions)}")
    console.print("fields=Suggested List | Category | Hit Rule | Rule Reason | Bytes | Source | Path | Reason")
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
    table.add_column("Suggested List")
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
            _suggested_destination_label(item),
            item.category or "-",
            item.hitRule or "-",
            item.hitRuleReason or "-",
            str(item.sizeBytes) if item.sizeBytes is not None else "-",
            item.derivedFrom or "-",
            item.path,
            item.reason,
        )
    console.print(table)
