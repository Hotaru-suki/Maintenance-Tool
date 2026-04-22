from __future__ import annotations

import typer


def prompt_yes_no(message: str) -> bool:
    while True:
        raw = typer.prompt(f"{message} [Y/N]", default="", show_default=False).strip()
        parsed = parse_yes_no(raw)
        if parsed is not None:
            return parsed
        typer.echo("Enter Y or N.")


def parse_yes_no(raw: str) -> bool | None:
    value = raw.strip().lower()
    if value == "y":
        return True
    if value == "n":
        return False
    return None
