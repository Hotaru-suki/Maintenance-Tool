import json
from pathlib import Path

import pytest

from maintenancetool.cli.dev import app
from tests.helpers.cli import TEST_SCOPE_NAME, runner
from tests.helpers.configuration import write_standard_config


@pytest.fixture(autouse=True)
def isolate_system_drive_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "maintenancetool.core.discovery_roots._list_windows_fixed_drive_roots",
        lambda: [],
    )
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)


def test_analyze_generates_snapshot_and_pending(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    cache_root = sandbox / "cache"
    extra_root = sandbox / "orphan-cache"
    protected = sandbox / "protected"
    cache_root.mkdir(parents=True)
    extra_root.mkdir(parents=True)
    protected.mkdir(parents=True)
    (cache_root / "a.bin").write_bytes(b"a" * 16)
    (extra_root / "b.bin").write_bytes(b"b" * 64)

    config_dir = tmp_path / "config"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    write_standard_config(
        config_dir,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(cache_root),
                "enabled": True,
                "depth": 2,
                "deleteMode": "contents",
                "source": "manual",
                "category": "cache",
            }
        ],
        deny_rules=[{"id": "protected", "path": str(protected), "enabled": True, "reason": "protected"}],
        discover={"maxDepth": 1, "topN": 10},
    )

    result = runner.invoke(
        app,
        [
            "analyze",
            "--config-dir",
            str(config_dir),
            "--state-dir",
            str(state_dir),
        ],
    )

    assert result.exit_code == 0
    snapshot = json.loads((state_dir / "lastSnapshot.json").read_text(encoding="utf-8"))
    pending = json.loads((state_dir / "pending.json").read_text(encoding="utf-8"))

    snapshot_paths = {entry["path"] for entry in snapshot["entries"]}
    pending_paths = {item["path"] for item in pending["suggestions"]}

    assert str(cache_root) in snapshot_paths
    assert str(extra_root) in pending_paths


def test_analyze_suppresses_previously_accepted_learning_decision(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    cache_root = sandbox / "cache"
    extra_root = sandbox / "orphan-cache"
    cache_root.mkdir(parents=True)
    extra_root.mkdir(parents=True)
    (cache_root / "a.bin").write_bytes(b"a" * 16)
    (extra_root / "b.bin").write_bytes(b"b" * 64)

    config_dir = tmp_path / "config"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    write_standard_config(
        config_dir,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(cache_root),
                "enabled": True,
                "depth": 2,
                "deleteMode": "contents",
                "source": "manual",
                "category": "cache",
            }
        ],
        discover={"maxDepth": 1, "topN": 10},
    )
    (state_dir / "learningDecisions.json").write_text(
        json.dumps(
            {
                "version": 1,
                "updatedAt": "2026-04-21T00:00:00+00:00",
                "decisions": [
                        {
                            "id": "known001",
                            "path": str(extra_root),
                            "scope": TEST_SCOPE_NAME,
                            "suggestedAction": "addFixedTarget",
                            "decision": "accepted",
                            "createdAt": "2026-04-21T00:00:00+00:00",
                            "updatedAt": "2026-04-21T00:00:00+00:00",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "analyze",
            "--config-dir",
            str(config_dir),
            "--state-dir",
            str(state_dir),
        ],
    )

    assert result.exit_code == 0
    pending = json.loads((state_dir / "pending.json").read_text(encoding="utf-8"))
    pending_paths = {item["path"] for item in pending["suggestions"]}
    assert str(extra_root) not in pending_paths


def test_analyze_suppresses_previously_rejected_learning_decision(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    cache_root = sandbox / "cache"
    extra_root = sandbox / "orphan-cache"
    cache_root.mkdir(parents=True)
    extra_root.mkdir(parents=True)
    (cache_root / "a.bin").write_bytes(b"a" * 16)
    (extra_root / "b.bin").write_bytes(b"b" * 64)

    config_dir = tmp_path / "config"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    write_standard_config(
        config_dir,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(cache_root),
                "enabled": True,
                "depth": 2,
                "deleteMode": "contents",
                "source": "manual",
                "category": "cache",
            }
        ],
        discover={"maxDepth": 1, "topN": 10},
    )
    (state_dir / "learningDecisions.json").write_text(
        json.dumps(
            {
                "version": 1,
                "updatedAt": "2026-04-21T00:00:00+00:00",
                "decisions": [
                        {
                            "id": "known002",
                            "path": str(extra_root),
                            "scope": TEST_SCOPE_NAME,
                            "suggestedAction": "addFixedTarget",
                            "decision": "rejected",
                            "createdAt": "2026-04-21T00:00:00+00:00",
                            "updatedAt": "2026-04-21T00:00:00+00:00",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "analyze",
            "--config-dir",
            str(config_dir),
            "--state-dir",
            str(state_dir),
        ],
    )

    assert result.exit_code == 0
    pending = json.loads((state_dir / "pending.json").read_text(encoding="utf-8"))
    pending_paths = {item["path"] for item in pending["suggestions"]}
    assert str(extra_root) not in pending_paths


def test_analyze_fixed_only_scans_review_targets(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    safe_root = sandbox / "safe-cache"
    review_root = sandbox / "browser-cache"
    safe_root.mkdir(parents=True)
    review_root.mkdir(parents=True)
    (safe_root / "safe.bin").write_bytes(b"a" * 16)
    (review_root / "state.bin").write_bytes(b"b" * 32)

    config_dir = tmp_path / "config"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    write_standard_config(
        config_dir,
        fixed_targets=[
            {
                "id": "safe-root",
                "path": str(safe_root),
                "enabled": True,
                "depth": 2,
                "deleteMode": "contents",
                "source": "manual",
                "category": "temp",
            }
        ],
        review_targets=[
            {
                "id": "review-root",
                "path": str(review_root),
                "enabled": True,
                "depth": 2,
                "deleteMode": "contents",
                "source": "manual",
                "category": "browser-cache",
            }
        ],
    )

    result = runner.invoke(
        app,
        [
            "analyze",
            "--config-dir",
            str(config_dir),
            "--state-dir",
            str(state_dir),
            "--fixed-only",
        ],
    )

    assert result.exit_code == 0
    snapshot = json.loads((state_dir / "lastSnapshot.json").read_text(encoding="utf-8"))
    snapshot_paths = {entry["path"] for entry in snapshot["entries"]}
    assert str(safe_root) in snapshot_paths
    assert str(review_root) in snapshot_paths
