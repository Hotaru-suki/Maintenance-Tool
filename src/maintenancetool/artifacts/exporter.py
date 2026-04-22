from __future__ import annotations

import json
import shutil
from pathlib import Path

from .models import ArtifactBundleResult, ArtifactInput


def export_ci_artifact_bundle(
    *,
    output_root: Path,
    bundle_name: str,
    files: list[ArtifactInput],
    directories: list[ArtifactInput],
    metadata: dict[str, str],
    notes: list[str],
    include_zip: bool = True,
) -> ArtifactBundleResult:
    output_root.mkdir(parents=True, exist_ok=True)
    bundle_dir = output_root / bundle_name
    attachments_dir = bundle_dir / "attachments"

    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    attachments_dir.mkdir(parents=True, exist_ok=True)

    attachment_entries: list[dict[str, object]] = []

    for artifact in files:
        source = artifact.source
        destination = attachments_dir / artifact.destination_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.exists():
            shutil.copy2(source, destination)
        attachment_entries.append(
            {
                "type": "file",
                "source": str(source),
                "destination": artifact.destination_name,
                "present": destination.exists(),
            }
        )

    for artifact in directories:
        source = artifact.source
        destination = attachments_dir / artifact.destination_name
        summary_name = f"{artifact.destination_name}.summary.txt"
        summary_path = attachments_dir / summary_name
        copied_files: list[str] = []
        if source.exists():
            shutil.copytree(source, destination, dirs_exist_ok=True)
            copied_files = sorted(
                str(path.relative_to(destination))
                for path in destination.rglob("*")
                if path.is_file()
            )
        summary_lines = copied_files or ["<empty>"]
        summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
        attachment_entries.append(
            {
                "type": "directory",
                "source": str(source),
                "destination": artifact.destination_name,
                "present": destination.exists(),
                "summary": summary_name,
                "files": copied_files,
            }
        )

    manifest_path = bundle_dir / "manifest.json"
    manifest = {
        "bundleType": "ci-artifact-bundle",
        "bundleName": bundle_name,
        "metadata": metadata,
        "notes": notes,
        "attachments": attachment_entries,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    package_path: Path | None = None
    if include_zip:
        archive_base = output_root / bundle_name
        archive_path = shutil.make_archive(str(archive_base), "zip", root_dir=bundle_dir)
        package_path = Path(archive_path)

    return ArtifactBundleResult(
        bundle_dir=bundle_dir,
        manifest_path=manifest_path,
        package_path=package_path,
    )
