from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkflowPolicy:
    name: str
    filename: str
    required_snippets: tuple[str, ...]
    forbidden_snippets: tuple[str, ...] = ()


WORKFLOW_POLICIES: tuple[WorkflowPolicy, ...] = (
    WorkflowPolicy(
        name="ci",
        filename="ci.yml",
        required_snippets=(
            'python-version: ["3.10", "3.11", "3.12"]',
            "pytest -q --junitxml=artifacts/raw/junit.xml",
            "python scripts/ci/collect_test_artifacts.py",
            "python scripts/ci/cleanup_test_artifacts.py",
        ),
        forbidden_snippets=(
            "./packaging/build-release.ps1 -PythonExe python -PlatformTag win-x64",
            "softprops/action-gh-release@v2",
            "python -m pip install pyinstaller",
        ),
    ),
    WorkflowPolicy(
        name="candidate-build",
        filename="candidate-build.yml",
        required_snippets=(
            'python-version: "3.12"',
            "python -m pip install pyinstaller",
            "choco install innosetup --no-progress -y",
            "./packaging/build-release.ps1 -PythonExe python -PlatformTag win-x64",
            "--dist-dir dist",
            "upload-artifact@v4",
        ),
        forbidden_snippets=(
            "softprops/action-gh-release@v2",
        ),
    ),
    WorkflowPolicy(
        name="release",
        filename="release.yml",
        required_snippets=(
            'python-version: "3.12"',
            "python -m pip install pyinstaller",
            "choco install innosetup --no-progress -y",
            "./packaging/build-release.ps1 -PythonExe python -PlatformTag win-x64",
            "--dist-dir dist",
            "softprops/action-gh-release@v2",
            "Validate tag version",
            "generate_release_notes: true",
        ),
        forbidden_snippets=(),
    ),
)


PACKAGING_REQUIRED_SNIPPETS: tuple[str, ...] = (
    'excludes=["pytest", "tests"]',
    '$InstallerScriptPath = Join-Path $ProjectRoot "packaging\\installer\\MaintenanceTool.iss"',
    '$SignScriptPath = Join-Path $ProjectRoot "packaging\\sign-release.ps1"',
    'Copy-Item -Recurse -Force $TemplateDir (Join-Path $ReleaseRoot "config_templates")',
    'Copy-Item -Force (Join-Path $LauncherDir "mtool.cmd") (Join-Path $ReleaseRoot "mtool.cmd")',
    'Copy-Item -Force (Join-Path $ProjectRoot "README.md") (Join-Path $ReleaseRoot "README.md")',
    'Copy-Item -Force (Join-Path $ProjectRoot "README.zh-CN.md") (Join-Path $ReleaseRoot "README.zh-CN.md")',
    '$WingetManifestScriptPath = Join-Path $ProjectRoot "scripts\\packaging\\generate_winget_manifest.py"',
    'Get-Command "ISCC.exe" -ErrorAction SilentlyContinue',
    'ChangesEnvironment=yes',
    'icon=str(icon_path)',
)
