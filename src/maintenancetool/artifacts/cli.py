from __future__ import annotations

from pathlib import Path

import typer

from .exporter import export_ci_artifact_bundle
from .models import ArtifactInput

app = typer.Typer(help="Artifact bundle utilities for CI and release workflows.")


@app.callback()
def main() -> None:
    """Artifact bundle command group."""


def _parse_mapping(raw: str) -> ArtifactInput:
    if "=" not in raw:
        raise typer.BadParameter("expected SOURCE=DESTINATION")
    source_text, destination_name = raw.split("=", 1)
    source_text = source_text.strip()
    destination_name = destination_name.strip()
    if not source_text or not destination_name:
        raise typer.BadParameter("expected SOURCE=DESTINATION")
    return ArtifactInput(source=Path(source_text), destination_name=destination_name)


def _parse_metadata(raw_values: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for raw in raw_values:
        if "=" not in raw:
            raise typer.BadParameter("metadata entries must use KEY=VALUE")
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key:
            raise typer.BadParameter("metadata key cannot be empty")
        metadata[key] = value.strip()
    return metadata


@app.command("bundle-ci")
def bundle_ci(
    output_root: Path = typer.Option(..., "--output-root"),
    bundle_name: str = typer.Option(..., "--bundle-name"),
    files: list[str] = typer.Option([], "--file"),
    directories: list[str] = typer.Option([], "--dir"),
    metadata_entries: list[str] = typer.Option([], "--metadata"),
    note_entries: list[str] = typer.Option([], "--note"),
    include_zip: bool = typer.Option(True, "--zip/--no-zip"),
) -> None:
    result = export_ci_artifact_bundle(
        output_root=output_root,
        bundle_name=bundle_name,
        files=[_parse_mapping(raw) for raw in files],
        directories=[_parse_mapping(raw) for raw in directories],
        metadata=_parse_metadata(metadata_entries),
        notes=note_entries,
        include_zip=include_zip,
    )
    typer.echo(f"bundle_dir={result.bundle_dir}")
    typer.echo(f"manifest_path={result.manifest_path}")
    if result.package_path is not None:
        typer.echo(f"package_path={result.package_path}")
