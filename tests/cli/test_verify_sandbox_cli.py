from pathlib import Path

from maintenancetool.cli.dev import app
from tests.helpers.cli import runner
from tests.helpers.configuration import write_legacy_sandbox_config
from tests.helpers.sandbox_factory import SandboxFactory


def test_verify_sandbox_runs_non_destructive_flow(tmp_path: Path) -> None:
    sandbox = SandboxFactory(tmp_path).create()
    fixture_dir = sandbox.fixtures_dir / "browser" / "cache"
    fixture_dir.mkdir(parents=True)
    (fixture_dir / "blob.bin").write_bytes(b"x" * 32)

    write_legacy_sandbox_config(
        sandbox.config_dir,
        fixed_targets=[
            {
                "path": f"C:\\{sandbox.root.name}\\fixtures\\browser\\cache",
                "scopeHint": "windows",
                "depth": 2,
                "deleteMode": "contents",
                "source": "manual",
                "enabled": True,
            }
        ],
        deny_rules=[
            {
                "path": f"C:\\{sandbox.root.name}\\state",
                "scopeHint": "windows",
                "reason": "protected",
                "enabled": True,
            }
        ],
    )

    result = runner.invoke(app, ["verify-sandbox", "--sandbox-root", str(sandbox.root)])

    assert result.exit_code == 0
    assert (sandbox.state_dir / "lastSnapshot.json").exists()
    assert (sandbox.state_dir / "pending.json").exists()
    assert "Sandbox verification complete." in result.stdout


def test_verify_sandbox_can_apply_quarantine(tmp_path: Path) -> None:
    sandbox = SandboxFactory(tmp_path).create()
    fixture_dir = sandbox.fixtures_dir / "browser" / "cache"
    fixture_dir.mkdir(parents=True)
    (fixture_dir / "blob.bin").write_bytes(b"x" * 32)

    write_legacy_sandbox_config(
        sandbox.config_dir,
        fixed_targets=[
            {
                "path": f"C:\\{sandbox.root.name}\\fixtures\\browser\\cache",
                "scopeHint": "windows",
                "depth": 2,
                "deleteMode": "contents",
                "source": "manual",
                "enabled": True,
            }
        ],
        deny_rules=[],
    )

    result = runner.invoke(
        app,
        ["verify-sandbox", "--sandbox-root", str(sandbox.root), "--apply-quarantine"],
    )

    assert result.exit_code == 0
    assert fixture_dir.exists()
    assert list(fixture_dir.iterdir()) == []
    assert any(sandbox.quarantine_dir.iterdir())
