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
