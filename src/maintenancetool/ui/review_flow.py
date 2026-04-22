from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from maintenancetool.services.review import run_review_pending_service
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

    selected = _prompt_index_selection(
        console,
        prompt_text="Select items to accept (a, 1,3, 2-4, n, q)",
        total_items=len(pending_state.suggestions),
        cancelled_message="Review cancelled.",
    )
    if selected is None:
        return

    accept_ids = {pending_state.suggestions[index - 1].id for index in sorted(selected)}

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


def _render_pending_review(console: Console, *, pending_state) -> None:
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
