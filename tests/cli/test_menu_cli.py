from pathlib import Path

import maintenancetool.ui.menu as menu_ui
from maintenancetool.cli.dev import app
from maintenancetool.ui.selection import parse_selection
from tests.helpers.cli import runner
from tests.helpers.configuration import write_json, write_standard_config
from tests.helpers.runtime_workspace import invoke_runtime_command


def test_parse_selection_supports_mixed_ranges() -> None:
    selected = parse_selection("1,3-4,6", 6)
    assert selected == {1, 3, 4, 6}


def test_menu_exit_immediately(runtime_workspace) -> None:
    write_standard_config(runtime_workspace.config_dir, fixed_targets=[])

    result = invoke_runtime_command(
        runner,
        app,
        runtime_workspace,
        "menu",
        input_text="0\n",
    )

    assert result.exit_code == 0
    assert "MaintenanceTool" in result.stdout


def test_menu_hides_advanced_for_non_admin(monkeypatch, runtime_workspace) -> None:
    monkeypatch.setattr(menu_ui, "is_admin_session", lambda: False)
    write_standard_config(runtime_workspace.config_dir, fixed_targets=[])

    result = invoke_runtime_command(
        runner,
        app,
        runtime_workspace,
        "menu",
        input_text="0\n",
    )

    assert result.exit_code == 0
    assert "9. Advanced" not in result.stdout
    assert "7. Check Updates" in result.stdout


def test_menu_shows_advanced_for_admin(monkeypatch, runtime_workspace) -> None:
    monkeypatch.setattr(menu_ui, "is_admin_session", lambda: True)
    write_standard_config(runtime_workspace.config_dir, fixed_targets=[])

    result = invoke_runtime_command(
        runner,
        app,
        runtime_workspace,
        "menu",
        input_text="0\n",
    )

    assert result.exit_code == 0
    assert "9. Advanced" in result.stdout
    assert "7. Check Updates" in result.stdout


def test_menu_ordinary_flow_does_not_show_quarantine_entry(runtime_workspace) -> None:
    write_standard_config(runtime_workspace.config_dir, fixed_targets=[])

    result = invoke_runtime_command(
        runner,
        app,
        runtime_workspace,
        "menu",
        input_text="0\n",
    )

    assert result.exit_code == 0
    assert "4. Quarantine" not in result.stdout
    assert "4. Delete Safe" in result.stdout


def test_config_check_reports_learning_driven_initial_warning_only(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    write_standard_config(config_dir, fixed_targets=[])

    result = runner.invoke(app, ["config-check", "--config-dir", str(config_dir)])

    assert result.exit_code == 0
    assert "profile=learning-driven-initial" in result.stdout
    assert "fixedTargets.json: exists=True valid_json=True kind=array count=0" in result.stdout
    assert "warning: config profile is learning-driven-initial" in result.stdout
    assert "discover_root_source=" in result.stdout
    assert "hit_rules_total=" in result.stdout
    assert "Configuration check passed." in result.stdout


def test_menu_review_pending_shows_reason_size_category_and_source(runtime_workspace) -> None:
    write_standard_config(
        runtime_workspace.config_dir,
        fixed_targets=[
            {
                "id": "existing",
                "path": "/sandbox/existing",
                "scopeHint": "wsl",
            }
        ],
    )
    write_json(
        runtime_workspace.state_dir / "pending.json",
        {
            "version": 1,
            "createdAt": "2026-04-21T00:00:00+00:00",
            "suggestions": [
                {
                    "id": "abc123",
                    "path": "/sandbox/new-target",
                    "scope": "wsl",
                    "suggestedAction": "addFixedTarget",
                    "reason": "new candidate discovered under /sandbox (2048 bytes)",
                    "category": "cache",
                    "hitRule": "name-browser-cache",
                    "hitRuleReason": "matched cache directory name",
                    "sizeBytes": 2048,
                    "derivedFrom": "/sandbox",
                    "createdAt": "2026-04-21T00:00:00+00:00",
                }
            ],
        },
    )

    result = runner.invoke(
        app,
        ["menu", *runtime_workspace.runtime_args()],
        input="2\nq\n1\n0\n",
    )

    assert result.exit_code == 0
    assert "pending review items=1" in result.stdout
    assert "fields=Action" in result.stdout
    assert "Rule Reason" in result.stdout
    assert "first item: path=/sandbox/new-target" in result.stdout
    assert "category=cache" in result.stdout
    assert "bytes=2048" in result.stdout
    assert "source=/sandbox" in result.stdout
    assert "hit_rule=name-browser-cache" in result.stdout


def test_menu_delete_safe_apply_renders_execution_summary(runtime_workspace) -> None:
    cache_root = runtime_workspace.root / "cache"
    cache_root.mkdir()
    (cache_root / "a.bin").write_bytes(b"a" * 32)

    write_standard_config(
        runtime_workspace.config_dir,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(cache_root),
                "scopeHint": "wsl",
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

    result = invoke_runtime_command(runner, app, runtime_workspace, "menu", input_text="4\n1\ny\n1\n0\n")

    assert result.exit_code == 0
    assert "applied items = 1" in result.stdout
    assert "execution_report_path=" in result.stdout


def test_menu_dry_run_selection_generates_preview_only(runtime_workspace) -> None:
    cache_root = runtime_workspace.root / "cache"
    cache_root.mkdir()
    (cache_root / "a.bin").write_bytes(b"a" * 32)

    write_standard_config(
        runtime_workspace.config_dir,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(cache_root),
                "scopeHint": "wsl",
                "depth": 1,
                "deleteMode": "contents",
                "enabled": True,
                "source": "manual",
            }
        ],
    )

    result = invoke_runtime_command(runner, app, runtime_workspace, "menu", input_text="3\n1\ny\n1\n0\n")

    assert result.exit_code == 0
    assert "selected items = 1" in result.stdout
    assert "Dry-run preview generated only" in result.stdout
    assert "execution_report_path=" not in result.stdout
