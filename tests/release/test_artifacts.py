from pathlib import Path

from typer.testing import CliRunner

from maintenancetool.artifacts.cli import app
from maintenancetool.artifacts.exporter import export_ci_artifact_bundle
from maintenancetool.artifacts.models import ArtifactInput


def test_export_ci_artifact_bundle_copies_files_and_directories(tmp_path: Path) -> None:
    output_root = tmp_path / "artifacts"
    source_file = tmp_path / "junit.xml"
    source_file.write_text("<testsuite />\n", encoding="utf-8")
    source_dir = tmp_path / "reports"
    source_dir.mkdir()
    (source_dir / "cleanup-plan-dry-run.json").write_text("{}", encoding="utf-8")

    result = export_ci_artifact_bundle(
        output_root=output_root,
        bundle_name="ci-run-001",
        files=[ArtifactInput(source=source_file, destination_name="junit.xml")],
        directories=[ArtifactInput(source=source_dir, destination_name="reports")],
        metadata={"runId": "001"},
        notes=["windows-validation"],
    )

    assert result.bundle_dir.exists()
    assert result.manifest_path.exists()
    assert result.package_path is not None and result.package_path.exists()
    assert (result.bundle_dir / "attachments" / "junit.xml").exists()
    assert (result.bundle_dir / "attachments" / "reports").is_dir()
    manifest = result.manifest_path.read_text(encoding="utf-8")
    assert '"bundleType": "ci-artifact-bundle"' in manifest
    assert '"runId": "001"' in manifest
    assert "reports.summary.txt" in manifest


def test_artifacts_cli_bundles_inputs(tmp_path: Path) -> None:
    runner = CliRunner()
    output_root = tmp_path / "artifacts"
    source_file = tmp_path / "junit.xml"
    source_file.write_text("<testsuite />\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "bundle-ci",
            "--output-root",
            str(output_root),
            "--bundle-name",
            "ci-run-002",
            "--file",
            f"{source_file}=junit.xml",
            "--metadata",
            "branch=main",
            "--no-zip",
        ],
    )

    assert result.exit_code == 0
    assert "bundle_dir=" in result.stdout
    assert (output_root / "ci-run-002" / "attachments" / "junit.xml").exists()
