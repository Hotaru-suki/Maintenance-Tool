from maintenancetool.cli.dev import app
from maintenancetool.ui.launcher import build_launcher_commands, filter_launcher_commands, resolve_exact_command
from tests.helpers.cli import runner
from tests.helpers.configuration import write_standard_config
from tests.helpers.runtime_workspace import invoke_runtime_command


def test_filter_launcher_commands_narrows_results() -> None:
    commands = build_launcher_commands()

    matches = filter_launcher_commands(commands, "/d", advanced_enabled=False)

    names = [command.name for command in matches]
    assert "/dryrun" in names
    assert "/delete-safe" in names
    assert "/advanced-dryrun" not in names


def test_filter_launcher_commands_includes_update_command() -> None:
    commands = build_launcher_commands()

    matches = filter_launcher_commands(commands, "/c", advanced_enabled=False)

    names = [command.name for command in matches]
    assert "/check-update" in names


def test_resolve_exact_command_supports_alias() -> None:
    command = resolve_exact_command(build_launcher_commands(), "/stat", advanced_enabled=False)

    assert command is not None
    assert command.name == "/status"


def test_launcher_shows_welcome_and_exit(runtime_workspace) -> None:
    write_standard_config(runtime_workspace.config_dir, fixed_targets=[])

    result = invoke_runtime_command(
        runner,
        app,
        runtime_workspace,
        "launcher",
        input_text="/exit\n",
    )

    assert result.exit_code == 0
    assert "MaintenanceTool" in result.stdout
    assert "mode: standard" in result.stdout
    assert "recent:" in result.stdout
    assert "commands matching `/`" in result.stdout
    assert "selected: /help" in result.stdout
    assert "exiting MaintenanceTool" in result.stdout


def test_launcher_status_command_prints_summary(runtime_workspace) -> None:
    write_standard_config(runtime_workspace.config_dir, fixed_targets=[])

    result = invoke_runtime_command(
        runner,
        app,
        runtime_workspace,
        "launcher",
        input_text="/status\n/exit\n",
    )

    assert result.exit_code == 0
    assert "status" in result.stdout
    assert "config" in result.stdout
    assert "- profile: learning-driven-initial" in result.stdout
    assert "learning-driven-initial" in result.stdout
    assert "pending" in result.stdout
    assert "- total: 0" in result.stdout
    assert "next" in result.stdout
    assert "- primary: /analyze" in result.stdout


def test_launcher_analyze_shows_followup_guidance(runtime_workspace) -> None:
    write_standard_config(runtime_workspace.config_dir, fixed_targets=[])

    result = invoke_runtime_command(
        runner,
        app,
        runtime_workspace,
        "launcher",
        input_text="/analyze\nn\n/exit\n",
    )

    assert result.exit_code == 0
    assert "analyze" in result.stdout
    assert "next" in result.stdout
    assert "/review" in result.stdout or "/dryrun" in result.stdout


def test_launcher_analyze_review_dryrun_delete_chain(runtime_workspace) -> None:
    sandbox = runtime_workspace.root / "sandbox"
    cache_root = sandbox / "cache"
    extra_root = sandbox / "orphan-cache"
    cache_root.mkdir(parents=True)
    extra_root.mkdir(parents=True)
    (cache_root / "a.bin").write_bytes(b"a" * 16)
    (extra_root / "b.bin").write_bytes(b"b" * 64)

    write_standard_config(
        runtime_workspace.config_dir,
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
        learning={
            "safetyPolicy": {
                "requireManualConfirmForLearnedTargets": False,
                "requireManualConfirmAboveBytes": 999999999,
            }
        },
    )

    result = invoke_runtime_command(
        runner,
        app,
        runtime_workspace,
        "launcher",
        input_text="/analyze\ny\na\nn\n/dryrun\n/delete-safe\ny\n/exit\n",
    )

    assert result.exit_code == 0
    assert "pending_suggestions: 1" in result.stdout
    assert "Accepted" in result.stdout
    assert "dry-run preview" in result.stdout
    assert "delete safe execution" in result.stdout
    assert "applied_items: 2" in result.stdout
    assert not (cache_root / "a.bin").exists()
    assert not (extra_root / "b.bin").exists()
    assert (runtime_workspace.report_dir / "cleanup-execution-delete.json").exists()
