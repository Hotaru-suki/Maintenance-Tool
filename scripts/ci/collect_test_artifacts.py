from __future__ import annotations

import argparse
from pathlib import Path

from maintenancetool.artifacts.exporter import export_ci_artifact_bundle
from maintenancetool.artifacts.models import ArtifactInput


def main() -> int:
    args = parse_args()
    files: list[ArtifactInput] = []
    directories: list[ArtifactInput] = []

    junit_path = Path(args.junit)
    files.append(ArtifactInput(source=junit_path, destination_name="junit.xml"))

    if args.dist_dir:
        directories.append(ArtifactInput(source=Path(args.dist_dir), destination_name="dist"))

    metadata = {
        "workflow": args.workflow,
        "runId": args.run_id,
        "sha": args.sha,
        "ref": args.ref_name,
        "pytestStatus": args.pytest_status,
    }
    if args.python_version:
        metadata["pythonVersion"] = args.python_version

    result = export_ci_artifact_bundle(
        output_root=Path(args.output_root),
        bundle_name=args.bundle_name,
        files=files,
        directories=directories,
        metadata=metadata,
        notes=list(args.note),
        include_zip=True,
    )
    print(f"bundle_dir={result.bundle_dir}")
    print(f"manifest_path={result.manifest_path}")
    if result.package_path is not None:
        print(f"package_path={result.package_path}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect pytest and build artifacts into a CI bundle.")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--bundle-name", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--ref-name", required=True)
    parser.add_argument("--pytest-status", required=True)
    parser.add_argument("--python-version")
    parser.add_argument("--junit", required=True)
    parser.add_argument("--dist-dir")
    parser.add_argument("--note", action="append", default=[])
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
