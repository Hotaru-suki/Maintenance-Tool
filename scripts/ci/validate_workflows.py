from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ROOT = PROJECT_ROOT / ".github" / "workflows"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dataclass(slots=True)
class ValidationCheck:
    name: str
    ok: bool
    detail: str


def main() -> int:
    checks = run_workflow_smoke_checks()
    failures = [check for check in checks if not check.ok]
    for check in checks:
        status = "OK" if check.ok else "FAIL"
        print(f"[{status}] {check.name}: {check.detail}")
    return 1 if failures else 0


def run_workflow_smoke_checks() -> list[ValidationCheck]:
    checks = [
        _check_file_exists("ci workflow", WORKFLOW_ROOT / "ci.yml"),
        _check_file_exists("candidate workflow", WORKFLOW_ROOT / "candidate-build.yml"),
        _check_file_exists("release workflow", WORKFLOW_ROOT / "release.yml"),
        _check_file_exists("release build script", PROJECT_ROOT / "packaging" / "build-release.ps1"),
        _check_file_exists("pyinstaller spec", PROJECT_ROOT / "packaging" / "pyinstaller" / "MaintenanceTool.spec"),
        _check_workflow_references(),
        _check_packaging_boundary(),
        _check_artifacts_help(),
    ]
    return checks


def _check_file_exists(name: str, path: Path) -> ValidationCheck:
    return ValidationCheck(
        name=name,
        ok=path.exists(),
        detail=str(path),
    )


def _check_workflow_references() -> ValidationCheck:
    from scripts.ci.workflow_policy import WORKFLOW_POLICIES

    missing: list[str] = []
    for policy in WORKFLOW_POLICIES:
        workflow_path = WORKFLOW_ROOT / policy.filename
        if not workflow_path.exists():
            missing.append(f"{policy.filename}: file missing")
            continue
        text = workflow_path.read_text(encoding="utf-8")
        for snippet in policy.required_snippets:
            if snippet not in text:
                missing.append(f"{policy.filename}: missing snippet {snippet!r}")
        for snippet in policy.forbidden_snippets:
            if snippet in text:
                missing.append(f"{policy.filename}: forbidden snippet present {snippet!r}")
    return ValidationCheck(
        name="workflow command references",
        ok=not missing,
        detail="; ".join(missing) if missing else "required command snippets present",
    )


def _check_packaging_boundary() -> ValidationCheck:
    from scripts.ci.workflow_policy import PACKAGING_REQUIRED_SNIPPETS

    spec_path = PROJECT_ROOT / "packaging" / "pyinstaller" / "MaintenanceTool.spec"
    build_script_path = PROJECT_ROOT / "packaging" / "build-release.ps1"
    installer_script_path = PROJECT_ROOT / "packaging" / "installer" / "MaintenanceTool.iss"
    missing: list[str] = []
    for path, label in (
        (spec_path, "spec"),
        (build_script_path, "build script"),
        (installer_script_path, "installer script"),
    ):
        if not path.exists():
            missing.append(f"{label}: file missing")
    if missing:
        return ValidationCheck(
            name="packaging boundary",
            ok=False,
            detail="; ".join(missing),
        )

    text = (
        spec_path.read_text(encoding="utf-8")
        + "\n"
        + build_script_path.read_text(encoding="utf-8")
        + "\n"
        + installer_script_path.read_text(encoding="utf-8")
    )
    for snippet in PACKAGING_REQUIRED_SNIPPETS:
        if snippet not in text:
            missing.append(f"packaging: missing snippet {snippet!r}")
    return ValidationCheck(
        name="packaging boundary",
        ok=not missing,
        detail="; ".join(missing) if missing else "release package includes only runtime assets and excludes tests",
    )


def _check_artifacts_help() -> ValidationCheck:
    command = [
        sys.executable,
        "-m",
        "maintenancetool.artifacts",
        "bundle-ci",
        "--help",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return ValidationCheck(
            name="artifact cli help",
            ok=False,
            detail=str(exc),
        )

    ok = completed.returncode == 0 and "--output-root" in completed.stdout
    detail = "artifact CLI help available" if ok else completed.stderr.strip() or completed.stdout.strip()
    return ValidationCheck(
        name="artifact cli help",
        ok=ok,
        detail=detail,
    )


if __name__ == "__main__":
    raise SystemExit(main())
