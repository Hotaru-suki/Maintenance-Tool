import maintenancetool.runtime_main as runtime_main
from typer.testing import CliRunner

from maintenancetool.cli.runtime import app as runtime_app


def test_runtime_app_hides_verify_sandbox_command() -> None:
    runner = CliRunner()

    result = runner.invoke(runtime_app, ["--help"])

    assert result.exit_code == 0
    assert "verify-sandbox" not in result.stdout


def test_runtime_main_defaults_to_menu_when_no_args(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(runtime_main, "bootstrap_runtime_workspace", lambda: calls.append("bootstrap"))
    monkeypatch.setitem(
        __import__("sys").modules,
        "maintenancetool.cli.runtime",
        type(
            "RuntimeModule",
            (),
            {
                "launch_default_launcher": staticmethod(lambda: calls.append("launcher")),
                "app": staticmethod(lambda: calls.append("app")),
            },
        )(),
    )
    monkeypatch.setattr(runtime_main.sys, "argv", ["MyTool.exe"])

    runtime_main.run()

    assert calls == ["bootstrap", "launcher"]


def test_runtime_main_uses_cli_when_args_present(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(runtime_main, "bootstrap_runtime_workspace", lambda: calls.append("bootstrap"))
    monkeypatch.setitem(
        __import__("sys").modules,
        "maintenancetool.cli.runtime",
        type(
            "RuntimeModule",
            (),
            {
                "launch_default_launcher": staticmethod(lambda: calls.append("launcher")),
                "app": staticmethod(lambda: calls.append("app")),
            },
        )(),
    )
    monkeypatch.setattr(runtime_main.sys, "argv", ["MyTool.exe", "config-check"])

    runtime_main.run()

    assert calls == ["bootstrap", "app"]


def test_runtime_main_main_returns_zero_on_success(monkeypatch) -> None:
    monkeypatch.setattr(runtime_main, "run", lambda: None)

    result = runtime_main.main()

    assert result == 0


def test_runtime_main_main_pauses_and_returns_one_on_failure(monkeypatch) -> None:
    calls: list[str] = []

    def raise_error() -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(runtime_main, "run", raise_error)
    monkeypatch.setattr(runtime_main, "_pause_on_error", lambda: calls.append("pause"))

    result = runtime_main.main()

    assert result == 1
    assert calls == ["pause"]
