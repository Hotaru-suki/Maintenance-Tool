from pathlib import Path

from scripts.ci.cleanup_test_artifacts import main as cleanup_main
from scripts.ci.collect_test_artifacts import main as collect_main
from scripts.ci.workflow_policy import PACKAGING_REQUIRED_SNIPPETS


def test_collect_test_artifacts_builds_bundle(monkeypatch, tmp_path: Path) -> None:
    output_root = tmp_path / "artifacts"
    junit_path = tmp_path / "junit.xml"
    dist_dir = tmp_path / "dist"
    junit_path.write_text("<testsuite />\n", encoding="utf-8")
    dist_dir.mkdir()
    (dist_dir / "app.zip").write_text("zip", encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "collect_test_artifacts.py",
            "--output-root",
            str(output_root),
            "--bundle-name",
            "ci-run-100",
            "--workflow",
            "ci",
            "--run-id",
            "100",
            "--sha",
            "abc123",
            "--ref-name",
            "main",
            "--pytest-status",
            "success",
            "--python-version",
            "3.12",
            "--junit",
            str(junit_path),
            "--dist-dir",
            str(dist_dir),
            "--note",
            "windows-validation",
        ],
    )

    result = collect_main()

    assert result == 0
    assert (output_root / "ci-run-100.zip").exists()


def test_cleanup_test_artifacts_removes_paths(monkeypatch, tmp_path: Path) -> None:
    raw_dir = tmp_path / "artifacts" / "raw"
    build_dir = tmp_path / "build"
    raw_dir.mkdir(parents=True)
    build_dir.mkdir()
    (raw_dir / "junit.xml").write_text("<testsuite />\n", encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "cleanup_test_artifacts.py",
            "--path",
            str(raw_dir),
            "--path",
            str(build_dir),
        ],
    )

    result = cleanup_main()

    assert result == 0
    assert not raw_dir.exists()
    assert not build_dir.exists()


def test_packaging_boundary_policy_mentions_release_assets_only() -> None:
    joined = "\n".join(PACKAGING_REQUIRED_SNIPPETS)

    assert 'excludes=["pytest", "tests"]' in joined
    assert "config_templates" in joined
    assert "README.md" in joined
    assert "README.zh-CN.md" in joined
    assert "MyTool.iss" in joined
    assert "sign-release.ps1" in joined
    assert 'Get-Command "ISCC.exe"' in joined
    assert 'icon=str(icon_path)' in joined
    assert "workspace-root.txt" in (Path("packaging/installer/MyTool.iss").read_text(encoding="utf-8"))
