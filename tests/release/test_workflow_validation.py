from pathlib import Path

from scripts.ci.validate_workflows import run_workflow_smoke_checks
from scripts.ci.workflow_policy import PACKAGING_REQUIRED_SNIPPETS, WORKFLOW_POLICIES


def test_workflow_smoke_checks_pass_for_repo_layout() -> None:
    checks = run_workflow_smoke_checks()

    assert checks
    assert all(check.ok for check in checks)


def test_workflow_files_exist() -> None:
    assert Path("README.md").exists()
    assert Path("README.zh-CN.md").exists()
    assert Path(".github/workflows/ci.yml").exists()
    assert Path(".github/workflows/candidate-build.yml").exists()
    assert Path(".github/workflows/release.yml").exists()
    assert Path("packaging/installer/MyTool.iss").exists()
    assert Path("packaging/sign-release.ps1").exists()
    assert Path("packaging/assets/MyTool.ico").exists()


def test_workflow_policies_cover_repo_workflows() -> None:
    filenames = {policy.filename for policy in WORKFLOW_POLICIES}

    assert filenames == {"ci.yml", "candidate-build.yml", "release.yml"}


def test_workflow_policy_required_and_forbidden_snippets_match_repo_files() -> None:
    workflow_root = Path(".github/workflows")

    for policy in WORKFLOW_POLICIES:
        text = (workflow_root / policy.filename).read_text(encoding="utf-8")
        for snippet in policy.required_snippets:
            assert snippet in text, f"{policy.filename} missing required snippet: {snippet}"
        for snippet in policy.forbidden_snippets:
            assert snippet not in text, f"{policy.filename} should not contain: {snippet}"


def test_packaging_boundary_snippets_match_packaging_files() -> None:
    combined = (
        Path("packaging/pyinstaller/MyTool.spec").read_text(encoding="utf-8")
        + "\n"
        + Path("packaging/build-release.ps1").read_text(encoding="utf-8")
        + "\n"
        + Path("packaging/installer/MyTool.iss").read_text(encoding="utf-8")
    )

    for snippet in PACKAGING_REQUIRED_SNIPPETS:
        assert snippet in combined, f"packaging boundary snippet missing: {snippet}"
