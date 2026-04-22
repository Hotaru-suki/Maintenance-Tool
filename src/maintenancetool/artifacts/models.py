from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ArtifactInput:
    source: Path
    destination_name: str


@dataclass(slots=True)
class ArtifactBundleResult:
    bundle_dir: Path
    manifest_path: Path
    package_path: Path | None
