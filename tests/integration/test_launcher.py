from pathlib import Path

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
    assert "Quick Start" in result.stdout
    assert "Primary Flow" in result.stdout
    assert "/status" in result.stdout
    assert "Command Details" in result.stdout
    assert "Exiting MaintenanceTool." in result.stdout


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
    assert "MaintenanceTool Status" in result.stdout
    assert "Configuration" in result.stdout
    assert "profile" in result.stdout
    assert "learning-driven-initial" in result.stdout
    assert "Pending" in result.stdout
    assert "pending_total" in result.stdout
    assert "Recommended Next" in result.stdout
    assert "Next Step" in result.stdout
    assert "/analyze" in result.stdout


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
    assert "Analyze Result" in result.stdout
    assert "Next Step" in result.stdout
    assert "/review" in result.stdout or "/dryrun" in result.stdout
