from pathlib import Path

from scripts.packaging.generate_winget_manifest import generate_manifest_text, write_manifest


def test_generate_manifest_text_uses_expected_fields() -> None:
    text = generate_manifest_text(
        version="0.1.0",
        installer_url="https://example.invalid/MyTool-v0.1.0-win-x64-setup.exe",
        installer_sha256="abc123",
    )

    assert 'PackageIdentifier: "HotaruSuki.MyTool"' in text
    assert 'PackageVersion: "0.1.0"' in text
    assert 'InstallerType: "inno"' in text
    assert 'InstallerUrl: "https://example.invalid/MyTool-v0.1.0-win-x64-setup.exe"' in text
    assert 'InstallerSha256: "ABC123"' in text
    assert 'ManifestType: "singleton"' in text


def test_write_manifest_creates_output_file(tmp_path: Path) -> None:
    output_path = tmp_path / "MyTool-v0.1.0-win-x64-winget.yaml"

    write_manifest(
        version="0.1.0",
        installer_url="https://example.invalid/MyTool-v0.1.0-win-x64-setup.exe",
        installer_sha256="def456",
        output_path=output_path,
    )

    assert output_path.exists()
    assert 'InstallerSha256: "DEF456"' in output_path.read_text(encoding="utf-8")
