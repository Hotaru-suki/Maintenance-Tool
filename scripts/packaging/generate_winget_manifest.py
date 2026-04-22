from __future__ import annotations

import argparse
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from maintenancetool.release import (
    APP_LICENSE,
    APP_NAME,
    APP_PUBLISHER,
    APP_REPOSITORY_URL,
    APP_WINGET_ID,
    winget_manifest_name,
)

MANIFEST_VERSION = "1.12.0"
PACKAGE_LOCALE = "en-US"
SHORT_DESCRIPTION = "Lightweight Windows local maintenance tool for safe, reviewable cleanup."


def generate_manifest_text(*, version: str, installer_url: str, installer_sha256: str) -> str:
    lines = [
        f'PackageIdentifier: "{APP_WINGET_ID}"',
        f'PackageVersion: "{version}"',
        f'PackageLocale: "{PACKAGE_LOCALE}"',
        f'Publisher: "{APP_PUBLISHER}"',
        f'PackageName: "{APP_NAME}"',
        f'PackageUrl: "{APP_REPOSITORY_URL}"',
        f'License: "{APP_LICENSE}"',
        f'ShortDescription: "{SHORT_DESCRIPTION}"',
        "Installers:",
        '  - Architecture: "x64"',
        '    InstallerType: "inno"',
        '    Scope: "machine"',
        f'    InstallerUrl: "{installer_url}"',
        f'    InstallerSha256: "{installer_sha256.upper()}"',
        'ManifestType: "singleton"',
        f'ManifestVersion: "{MANIFEST_VERSION}"',
        "",
    ]
    return "\n".join(lines)


def write_manifest(*, version: str, installer_url: str, installer_sha256: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        generate_manifest_text(
            version=version,
            installer_url=installer_url,
            installer_sha256=installer_sha256,
        ),
        encoding="utf-8",
    )
    return output_path


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a singleton winget manifest for the current release installer.")
    parser.add_argument("--version", required=True, help="Package version, for example 0.1.0")
    parser.add_argument("--installer-url", required=True, help="Public HTTPS URL for the installer asset")
    parser.add_argument("--installer-sha256", required=True, help="SHA256 for the installer asset")
    parser.add_argument(
        "--output-path",
        default=None,
        help="Output YAML path. Defaults to dist/<generated-name>.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    output_path = Path(args.output_path) if args.output_path else PROJECT_ROOT / "dist" / winget_manifest_name(version=args.version)
    write_manifest(
        version=args.version,
        installer_url=args.installer_url,
        installer_sha256=args.installer_sha256,
        output_path=output_path,
    )
    print(f"winget_manifest_path={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
