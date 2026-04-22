from pathlib import Path

from maintenancetool.cli.dev import app
from tests.helpers.cli import TEST_SCOPE_NAME, runner
from tests.helpers.configuration import write_standard_config
from tests.helpers.runtime_workspace import create_runtime_workspace, invoke_runtime_command


def write_cleanup_config(
    config_dir: Path,
    *,
    fixed_targets: list[dict[str, object]],
    learning: dict[str, object] | None = None,
) -> None:
    write_standard_config(
        config_dir,
        fixed_targets=fixed_targets,
        learning=learning,
    )


def invoke_clean(
    tmp_path: Path,
    *extra_args: str,
    input_text: str | None = None,
):
    workspace = create_runtime_workspace(tmp_path)
    result = invoke_runtime_command(
        runner,
        app,
        workspace,
        "clean",
        *extra_args,
        input_text=input_text,
        include_state=False,
    )
    return workspace, result


def test_clean_dry_run_generates_plan_summary(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "a.bin").write_bytes(b"a" * 32)

    workspace = create_runtime_workspace(tmp_path)
    write_cleanup_config(
        workspace.config_dir,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(cache_root),
                "scopeHint": TEST_SCOPE_NAME,
                "depth": 1,
                "deleteMode": "contents",
                "enabled": True,
            }
        ],
    )

    result = invoke_runtime_command(
        runner,
        app,
        workspace,
        "clean",
        "--mode",
        "dry-run",
        include_state=False,
    )

    assert result.exit_code == 0
    assert "plan items = 1" in result.stdout
    assert "allowed items = 1" in result.stdout
    assert "Cleanup plan generated only" in result.stdout
    assert (workspace.report_dir / "cleanup-plan-dry-run.json").exists()


def test_clean_quarantine_apply_moves_directory_contents(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "a.bin").write_bytes(b"a" * 32)
    (cache_root / "nested").mkdir()
    (cache_root / "nested" / "b.bin").write_bytes(b"b" * 16)

    workspace = create_runtime_workspace(tmp_path)
    write_cleanup_config(
        workspace.config_dir,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(cache_root),
                "scopeHint": TEST_SCOPE_NAME,
                "depth": 2,
                "deleteMode": "contents",
                "enabled": True,
            }
        ],
    )

    result = invoke_runtime_command(
        runner,
        app,
        workspace,
        "clean",
        "--mode",
        "quarantine",
        "--apply",
        include_state=False,
    )

    assert result.exit_code == 0
    assert "applied items = 1" in result.stdout
    assert cache_root.exists()
    assert list(cache_root.iterdir()) == []
    records_dir = workspace.quarantine_dir / "records"
    assert records_dir.exists()
    record_dirs = [path for path in records_dir.iterdir() if path.is_dir()]
    assert len(record_dirs) == 1
    manifest = (record_dirs[0] / "record.json").read_text(encoding="utf-8")
    assert '"status": "active"' in manifest
    assert (record_dirs[0] / "payload").exists()
    assert (workspace.report_dir / "cleanup-plan-quarantine.json").exists()
    assert (workspace.report_dir / "cleanup-execution-quarantine.json").exists()


def test_clean_quarantine_apply_moves_directory_target(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache-root"
    cache_root.mkdir()
    (cache_root / "a.bin").write_bytes(b"a" * 32)

    workspace = create_runtime_workspace(tmp_path)
    write_cleanup_config(
        workspace.config_dir,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(cache_root),
                "scopeHint": TEST_SCOPE_NAME,
                "depth": 1,
                "deleteMode": "directory",
                "enabled": True,
            }
        ],
    )

    result = invoke_runtime_command(
        runner,
        app,
        workspace,
        "clean",
        "--mode",
        "quarantine",
        "--apply",
        include_state=False,
    )

    assert result.exit_code == 0
    assert "applied items = 1" in result.stdout
    assert not cache_root.exists()
    assert (workspace.quarantine_dir / "records").exists()


def test_clean_quarantine_apply_skips_learned_target_without_extra_confirmation(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache-root"
    cache_root.mkdir()
    (cache_root / "a.bin").write_bytes(b"a" * 32)

    config_dir = tmp_path / "config"
    report_dir = tmp_path / "reports"
    quarantine_dir = tmp_path / ".quarantine"
    write_cleanup_config(
        config_dir,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(cache_root),
                "scopeHint": TEST_SCOPE_NAME,
                "depth": 1,
                "deleteMode": "directory",
                "enabled": True,
                "source": "learned",
            }
        ],
        learning={"safetyPolicy": {"requireManualConfirmForLearnedTargets": True}},
    )

    result = runner.invoke(
        app,
        [
            "clean",
            "--config-dir",
            str(config_dir),
            "--report-dir",
            str(report_dir),
            "--quarantine-dir",
            str(quarantine_dir),
            "--mode",
            "quarantine",
            "--apply",
        ],
    )

    assert result.exit_code == 0
    assert "skipped items = 1" in result.stdout
    assert cache_root.exists()
    assert not quarantine_dir.exists() or list(quarantine_dir.iterdir()) == []


def test_clean_quarantine_apply_rejects_budget_overflow(tmp_path: Path) -> None:
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    (root_a / "a.bin").write_bytes(b"a")
    (root_b / "b.bin").write_bytes(b"b")

    config_dir = tmp_path / "config"
    report_dir = tmp_path / "reports"
    quarantine_dir = tmp_path / ".quarantine"
    write_cleanup_config(
        config_dir,
        fixed_targets=[
            {"id": "a", "path": str(root_a), "scopeHint": TEST_SCOPE_NAME, "deleteMode": "directory"},
            {"id": "b", "path": str(root_b), "scopeHint": TEST_SCOPE_NAME, "deleteMode": "directory"},
        ],
        learning={"safetyPolicy": {"maxItemsPerRun": 1}},
    )

    result = runner.invoke(
        app,
        [
            "clean",
            "--config-dir",
            str(config_dir),
            "--report-dir",
            str(report_dir),
            "--quarantine-dir",
            str(quarantine_dir),
            "--mode",
            "quarantine",
            "--apply",
        ],
    )

    assert result.exit_code != 0
    assert "maxItemsPerRun" in result.stdout or "maxItemsPerRun" in str(result.exception)


def test_clean_delete_apply_removes_directory_contents(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "a.bin").write_bytes(b"a" * 32)
    (cache_root / "nested").mkdir()
    (cache_root / "nested" / "b.bin").write_bytes(b"b" * 16)

    config_dir = tmp_path / "config"
    report_dir = tmp_path / "reports"
    quarantine_dir = tmp_path / ".quarantine"
    write_cleanup_config(
        config_dir,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(cache_root),
                "scopeHint": TEST_SCOPE_NAME,
                "depth": 2,
                "deleteMode": "contents",
                "enabled": True,
                "source": "manual",
            }
        ],
        learning={
            "safetyPolicy": {
                "requireManualConfirmForLearnedTargets": False,
                "requireManualConfirmAboveBytes": 999999999,
            }
        },
    )

    result = runner.invoke(
        app,
        [
            "clean",
            "--config-dir",
            str(config_dir),
            "--report-dir",
            str(report_dir),
            "--quarantine-dir",
            str(quarantine_dir),
            "--mode",
            "delete",
            "--apply",
            "--interactive",
            "--confirm-delete",
            "DELETE",
        ],
        input="y\ny\n",
    )

    assert result.exit_code == 0
    assert "applied items = 1" in result.stdout
    assert cache_root.exists()
    assert list(cache_root.iterdir()) == []
    assert (report_dir / "cleanup-plan-delete.json").exists()
    assert (report_dir / "cleanup-execution-delete.json").exists()


def test_clean_delete_apply_removes_directory_target(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache-root"
    cache_root.mkdir()
    (cache_root / "a.bin").write_bytes(b"a" * 32)

    config_dir = tmp_path / "config"
    report_dir = tmp_path / "reports"
    quarantine_dir = tmp_path / ".quarantine"
    write_cleanup_config(
        config_dir,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(cache_root),
                "scopeHint": TEST_SCOPE_NAME,
                "depth": 1,
                "deleteMode": "directory",
                "enabled": True,
                "source": "manual",
            }
        ],
        learning={
            "safetyPolicy": {
                "requireManualConfirmForLearnedTargets": False,
                "requireManualConfirmAboveBytes": 999999999,
            }
        },
    )

    result = runner.invoke(
        app,
        [
            "clean",
            "--config-dir",
            str(config_dir),
            "--report-dir",
            str(report_dir),
            "--quarantine-dir",
            str(quarantine_dir),
            "--mode",
            "delete",
            "--apply",
            "--interactive",
            "--confirm-delete",
            "DELETE",
        ],
        input="y\ny\n",
    )

    assert result.exit_code == 0
    assert "applied items = 1" in result.stdout
    assert not cache_root.exists()


def test_clean_delete_apply_requires_confirmation_token(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "a.bin").write_bytes(b"a" * 32)

    config_dir = tmp_path / "config"
    report_dir = tmp_path / "reports"
    quarantine_dir = tmp_path / ".quarantine"
    write_cleanup_config(
        config_dir,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(cache_root),
                "scopeHint": TEST_SCOPE_NAME,
                "depth": 1,
                "deleteMode": "contents",
                "enabled": True,
                "source": "manual",
            }
        ],
        learning={
            "safetyPolicy": {
                "requireManualConfirmForLearnedTargets": False,
                "requireManualConfirmAboveBytes": 999999999,
            }
        },
    )

    result = runner.invoke(
        app,
        [
            "clean",
            "--config-dir",
            str(config_dir),
            "--report-dir",
            str(report_dir),
            "--quarantine-dir",
            str(quarantine_dir),
            "--mode",
            "delete",
            "--apply",
        ],
    )

    assert result.exit_code != 0
    assert cache_root.exists()


def test_clean_delete_apply_requires_interactive_confirmation(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "a.bin").write_bytes(b"a" * 32)

    config_dir = tmp_path / "config"
    report_dir = tmp_path / "reports"
    quarantine_dir = tmp_path / ".quarantine"
    write_cleanup_config(
        config_dir,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(cache_root),
                "scopeHint": TEST_SCOPE_NAME,
                "depth": 1,
                "deleteMode": "contents",
                "enabled": True,
                "source": "manual",
            }
        ],
        learning={
            "safetyPolicy": {
                "requireManualConfirmForLearnedTargets": False,
                "requireManualConfirmAboveBytes": 999999999,
            }
        },
    )

    result = runner.invoke(
        app,
        [
            "clean",
            "--config-dir",
            str(config_dir),
            "--report-dir",
            str(report_dir),
            "--quarantine-dir",
            str(quarantine_dir),
            "--mode",
            "delete",
            "--apply",
            "--confirm-delete",
            "DELETE",
        ],
    )

    assert result.exit_code != 0
    assert cache_root.exists()


def test_clean_delete_apply_interactive_decline_keeps_target(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "a.bin").write_bytes(b"a" * 32)

    config_dir = tmp_path / "config"
    report_dir = tmp_path / "reports"
    quarantine_dir = tmp_path / ".quarantine"
    write_cleanup_config(
        config_dir,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(cache_root),
                "scopeHint": TEST_SCOPE_NAME,
                "depth": 1,
                "deleteMode": "contents",
                "enabled": True,
                "source": "manual",
            }
        ],
        learning={
            "safetyPolicy": {
                "requireManualConfirmForLearnedTargets": False,
                "requireManualConfirmAboveBytes": 999999999,
            }
        },
    )

    result = runner.invoke(
        app,
        [
            "clean",
            "--config-dir",
            str(config_dir),
            "--report-dir",
            str(report_dir),
            "--quarantine-dir",
            str(quarantine_dir),
            "--mode",
            "delete",
            "--apply",
            "--interactive",
            "--confirm-delete",
            "DELETE",
        ],
        input="n\n",
    )

    assert result.exit_code == 0
    assert "Cleanup apply cancelled by user." in result.stdout
    assert cache_root.exists()


def test_restore_quarantine_command_restores_contents_and_updates_record(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "a.bin").write_bytes(b"a" * 32)
    (cache_root / "nested").mkdir()
    (cache_root / "nested" / "b.bin").write_bytes(b"b" * 16)

    config_dir = tmp_path / "config"
    report_dir = tmp_path / "reports"
    quarantine_dir = tmp_path / ".quarantine"
    write_cleanup_config(
        config_dir,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(cache_root),
                "scopeHint": TEST_SCOPE_NAME,
                "depth": 2,
                "deleteMode": "contents",
                "enabled": True,
            }
        ],
    )

    quarantine_result = runner.invoke(
        app,
        [
            "clean",
            "--config-dir",
            str(config_dir),
            "--report-dir",
            str(report_dir),
            "--quarantine-dir",
            str(quarantine_dir),
            "--mode",
            "quarantine",
            "--apply",
        ],
    )

    assert quarantine_result.exit_code == 0
    record_dir = next(path for path in (quarantine_dir / "records").iterdir() if path.is_dir())
    record_id = record_dir.name

    restore_result = runner.invoke(
        app,
        [
            "restore-quarantine",
            "--quarantine-dir",
            str(quarantine_dir),
            "--report-dir",
            str(report_dir),
            "--record-id",
            record_id,
        ],
    )

    assert restore_result.exit_code == 0
    assert "restored items = 1" in restore_result.stdout
    assert (cache_root / "a.bin").exists()
    assert (cache_root / "nested" / "b.bin").exists()
    manifest = (record_dir / "record.json").read_text(encoding="utf-8")
    assert '"status": "restored"' in manifest
    assert (report_dir / "restore-execution.json").exists()


def test_restore_quarantine_command_lists_active_records_without_apply(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "a.bin").write_bytes(b"a" * 32)

    config_dir = tmp_path / "config"
    report_dir = tmp_path / "reports"
    quarantine_dir = tmp_path / ".quarantine"
    write_cleanup_config(
        config_dir,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(cache_root),
                "scopeHint": TEST_SCOPE_NAME,
                "depth": 1,
                "deleteMode": "contents",
                "enabled": True,
            }
        ],
    )

    runner.invoke(
        app,
        [
            "clean",
            "--config-dir",
            str(config_dir),
            "--report-dir",
            str(report_dir),
            "--quarantine-dir",
            str(quarantine_dir),
            "--mode",
            "quarantine",
            "--apply",
        ],
    )

    result = runner.invoke(
        app,
        [
            "restore-quarantine",
            "--quarantine-dir",
            str(quarantine_dir),
            "--report-dir",
            str(report_dir),
        ],
    )

    assert result.exit_code == 0
    assert "No restore executed. Use --all or --record-id." in result.stdout


def test_restore_quarantine_command_skips_already_restored_record(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "a.bin").write_bytes(b"a" * 32)

    config_dir = tmp_path / "config"
    report_dir = tmp_path / "reports"
    quarantine_dir = tmp_path / ".quarantine"
    write_cleanup_config(
        config_dir,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(cache_root),
                "scopeHint": TEST_SCOPE_NAME,
                "depth": 1,
                "deleteMode": "contents",
                "enabled": True,
            }
        ],
    )

    runner.invoke(
        app,
        [
            "clean",
            "--config-dir",
            str(config_dir),
            "--report-dir",
            str(report_dir),
            "--quarantine-dir",
            str(quarantine_dir),
            "--mode",
            "quarantine",
            "--apply",
        ],
    )

    record_dir = next(path for path in (quarantine_dir / "records").iterdir() if path.is_dir())
    record_id = record_dir.name
    first_restore = runner.invoke(
        app,
        [
            "restore-quarantine",
            "--quarantine-dir",
            str(quarantine_dir),
            "--report-dir",
            str(report_dir),
            "--record-id",
            record_id,
        ],
    )
    assert first_restore.exit_code == 0

    second_restore = runner.invoke(
        app,
        [
            "restore-quarantine",
            "--quarantine-dir",
            str(quarantine_dir),
            "--report-dir",
            str(report_dir),
            "--record-id",
            record_id,
        ],
    )

    assert second_restore.exit_code == 0
    assert "skipped items = 1" in second_restore.stdout
