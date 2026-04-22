import maintenancetool.cli.runtime_support as runtime_support
from maintenancetool.cli.runtime import app
from tests.helpers.cli import runner
from tests.helpers.configuration import write_standard_config
from tests.helpers.runtime_workspace import invoke_runtime_command


def test_runtime_cli_blocks_direct_advanced_command_for_non_admin_windows(monkeypatch, runtime_workspace) -> None:
    monkeypatch.setattr(runtime_support, "is_windows_runtime", lambda: True)
    monkeypatch.setattr(runtime_support, "is_admin_session", lambda: False)
    write_standard_config(runtime_workspace.config_dir, fixed_targets=[])

    result = invoke_runtime_command(
        runner,
        app,
        runtime_workspace,
        "config-check",
        include_state=False,
        include_report=False,
        include_quarantine=False,
    )

    assert result.exit_code == 1
    assert "available only in advanced mode" in result.stdout


def test_runtime_cli_allows_direct_advanced_command_for_admin_windows(monkeypatch, runtime_workspace) -> None:
    monkeypatch.setattr(runtime_support, "is_windows_runtime", lambda: True)
    monkeypatch.setattr(runtime_support, "is_admin_session", lambda: True)
    write_standard_config(runtime_workspace.config_dir, fixed_targets=[])

    result = invoke_runtime_command(
        runner,
        app,
        runtime_workspace,
        "config-check",
        include_state=False,
        include_report=False,
        include_quarantine=False,
    )

    assert result.exit_code == 0
    assert "Configuration check passed." in result.stdout


def test_runtime_cli_analyze_fixed_only_reports_mode(monkeypatch, runtime_workspace) -> None:
    monkeypatch.setattr(runtime_support, "is_windows_runtime", lambda: True)
    monkeypatch.setattr(runtime_support, "is_admin_session", lambda: True)
    write_standard_config(runtime_workspace.config_dir, fixed_targets=[])

    result = invoke_runtime_command(
        runner,
        app,
        runtime_workspace,
        "analyze",
        "--fixed-only",
        include_report=False,
        include_quarantine=False,
    )

    assert result.exit_code == 0
    assert "mode = fixed-only" in result.stdout
