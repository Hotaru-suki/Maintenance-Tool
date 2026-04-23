import json
from pathlib import Path

from maintenancetool.cli.dev import app
from tests.helpers.cli import runner
from tests.helpers.configuration import write_json, write_standard_config


def test_review_pending_accept_all_promotes_learned_target(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    write_standard_config(
        config_dir,
        fixed_targets=[
            {
                "id": "existing",
                "path": "/sandbox/existing",
                "scopeHint": "wsl",
            }
        ],
    )
    write_json(
        state_dir / "pending.json",
        {
            "version": 1,
            "createdAt": "2026-04-21T00:00:00+00:00",
            "suggestions": [
                {
                    "id": "abc123",
                    "path": "/sandbox/new-target",
                    "scope": "wsl",
                    "suggestedAction": "addFixedTarget",
                    "reason": "new candidate discovered",
                    "hitRule": "name-browser-cache",
                    "hitRuleReason": "matched cache directory name",
                    "createdAt": "2026-04-21T00:00:00+00:00",
                }
            ],
        },
    )

    result = runner.invoke(
        app,
        ["review-pending", "--config-dir", str(config_dir), "--state-dir", str(state_dir), "--accept-all"],
    )

    assert result.exit_code == 0
    fixed_targets = json.loads((config_dir / "fixedTargets.json").read_text(encoding="utf-8"))
    pending = json.loads((state_dir / "pending.json").read_text(encoding="utf-8"))
    learning_decisions = json.loads((state_dir / "learningDecisions.json").read_text(encoding="utf-8"))
    assert any(item["path"] == "/sandbox/new-target" for item in fixed_targets)
    assert pending["suggestions"] == []
    assert learning_decisions["decisions"][0]["decision"] == "accepted"
    assert learning_decisions["decisions"][0]["hitRule"] == "name-browser-cache"
    assert learning_decisions["decisions"][0]["hitRuleReason"] == "matched cache directory name"


def test_review_pending_reject_records_learning_decision(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    write_standard_config(config_dir, fixed_targets=[])
    write_json(
        state_dir / "pending.json",
        {
            "version": 1,
            "createdAt": "2026-04-21T00:00:00+00:00",
            "suggestions": [
                {
                    "id": "reject001",
                    "path": "/sandbox/reject-target",
                    "scope": "wsl",
                    "suggestedAction": "addFixedTarget",
                    "reason": "new candidate discovered",
                    "hitRule": "name-temp-temp",
                    "hitRuleReason": "matched temp directory name",
                    "createdAt": "2026-04-21T00:00:00+00:00",
                }
            ],
        },
    )

    result = runner.invoke(
        app,
        [
            "review-pending",
            "--config-dir",
            str(config_dir),
            "--state-dir",
            str(state_dir),
            "--reject",
            "reject001",
        ],
    )

    assert result.exit_code == 0
    pending = json.loads((state_dir / "pending.json").read_text(encoding="utf-8"))
    learning_decisions = json.loads((state_dir / "learningDecisions.json").read_text(encoding="utf-8"))
    assert pending["suggestions"] == []
    assert learning_decisions["decisions"][0]["decision"] == "rejected"
    assert learning_decisions["decisions"][0]["hitRule"] == "name-temp-temp"
    assert learning_decisions["decisions"][0]["hitRuleReason"] == "matched temp directory name"


def test_review_pending_accepts_three_way_suggestions_into_separate_lists(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    write_standard_config(config_dir, fixed_targets=[])
    write_json(
        state_dir / "pending.json",
        {
            "version": 1,
            "createdAt": "2026-04-21T00:00:00+00:00",
            "suggestions": [
                {
                    "id": "safe001",
                    "path": "/sandbox/safe-temp",
                    "scope": "wsl",
                    "suggestedAction": "addFixedTarget",
                    "reason": "safe residue",
                    "category": "temp",
                    "createdAt": "2026-04-21T00:00:00+00:00",
                },
                {
                    "id": "review001",
                    "path": "/sandbox/browser-state",
                    "scope": "wsl",
                    "suggestedAction": "addReviewTarget",
                    "reason": "stateful cache",
                    "category": "browser-cache",
                    "createdAt": "2026-04-21T00:00:00+00:00",
                },
                {
                    "id": "deny001",
                    "path": "/sandbox/protected-link",
                    "scope": "wsl",
                    "suggestedAction": "addDenyRule",
                    "reason": "symlink/junction/reparse targets are rejected",
                    "category": "cache",
                    "createdAt": "2026-04-21T00:00:00+00:00",
                },
            ],
        },
    )

    result = runner.invoke(
        app,
        ["review-pending", "--config-dir", str(config_dir), "--state-dir", str(state_dir), "--accept-all"],
    )

    assert result.exit_code == 0
    fixed_targets = json.loads((config_dir / "fixedTargets.json").read_text(encoding="utf-8"))
    review_targets = json.loads((config_dir / "reviewTargets.json").read_text(encoding="utf-8"))
    deny_rules = json.loads((config_dir / "denyRules.json").read_text(encoding="utf-8"))

    assert any(item["path"] == "/sandbox/safe-temp" for item in fixed_targets)
    assert any(item["path"] == "/sandbox/browser-state" for item in review_targets)
    assert any(item["path"] == "/sandbox/protected-link" for item in deny_rules)


def test_review_promote_moves_selected_review_targets_to_fixed_targets(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    write_standard_config(
        config_dir,
        fixed_targets=[],
        review_targets=[
            {
                "id": "browser-state",
                "path": "/sandbox/browser-state",
                "scopeHint": "wsl",
                "category": "browser-cache",
                "source": "learned",
            },
            {
                "id": "large-growth",
                "path": "/sandbox/large-growth",
                "scopeHint": "wsl",
                "category": "logs",
                "source": "learned",
            },
        ],
    )

    result = runner.invoke(
        app,
        [
            "review-promote",
            "--config-dir",
            str(config_dir),
            "--target-id",
            "browser-state",
            "--target-id",
            "large-growth",
        ],
    )

    assert result.exit_code == 0
    assert "promoted review targets = 2" in result.stdout
    fixed_targets = json.loads((config_dir / "fixedTargets.json").read_text(encoding="utf-8"))
    review_targets = json.loads((config_dir / "reviewTargets.json").read_text(encoding="utf-8"))
    assert {item["id"] for item in fixed_targets} == {"browser-state", "large-growth"}
    assert review_targets == []


def test_list_targets_shows_fixed_review_and_deny_lists(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    write_standard_config(
        config_dir,
        fixed_targets=[{"id": "safe", "path": "/sandbox/safe", "scopeHint": "wsl"}],
        review_targets=[{"id": "review", "path": "/sandbox/review", "scopeHint": "wsl"}],
        deny_rules=[{"id": "deny", "path": "/sandbox/deny", "scopeHint": "wsl", "reason": "protected"}],
    )

    result = runner.invoke(
        app,
        ["list-targets", "--config-dir", str(config_dir), "--list", "all"],
    )

    assert result.exit_code == 0
    assert "fixedTargets count = 1" in result.stdout
    assert "reviewTargets count = 1" in result.stdout
    assert "denyRules count = 1" in result.stdout
    assert "safe | enabled" in result.stdout
    assert "review | enabled" in result.stdout
    assert "deny | enabled" in result.stdout
