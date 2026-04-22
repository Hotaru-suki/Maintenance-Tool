from pathlib import Path

from maintenancetool.core import runtime_paths


def test_resolve_workspace_root_prefers_explicit_override(monkeypatch, tmp_path: Path) -> None:
    override_root = tmp_path / "CustomWorkspace"
    monkeypatch.setenv("MAINTENANCETOOL_WORKSPACE_ROOT", str(override_root))

    resolved = runtime_paths._resolve_workspace_root()

    assert resolved == override_root.resolve()


def test_resolve_workspace_root_uses_documents_on_windows(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("MAINTENANCETOOL_WORKSPACE_ROOT", raising=False)
    monkeypatch.setattr(runtime_paths.os, "name", "nt")
    monkeypatch.setattr(
        runtime_paths,
        "_resolve_windows_workspace_root",
        lambda: tmp_path / "UserProfile" / "Documents" / runtime_paths.APP_NAME,
    )

    resolved = runtime_paths._resolve_workspace_root()

    assert resolved == tmp_path / "UserProfile" / "Documents" / runtime_paths.APP_NAME


def test_resolve_workspace_root_prefers_frozen_workspace_root_file(monkeypatch, tmp_path: Path) -> None:
    install_dir = tmp_path / "MaintenanceTool"
    install_dir.mkdir()
    configured_root = tmp_path / "ToolData"
    (install_dir / runtime_paths.WORKSPACE_ROOT_CONFIG_FILENAME).write_text(
        str(configured_root),
        encoding="utf-8",
    )

    monkeypatch.delenv("MAINTENANCETOOL_WORKSPACE_ROOT", raising=False)
    monkeypatch.setattr(runtime_paths.os, "name", "nt")
    monkeypatch.setattr(runtime_paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(runtime_paths, "_resolve_executable_dir", lambda: install_dir)

    resolved = runtime_paths._resolve_workspace_root()

    assert resolved == configured_root.resolve()


def test_resolve_workspace_root_prefers_frozen_portable_workspace_for_custom_install(monkeypatch, tmp_path: Path) -> None:
    install_dir = tmp_path / "PortableMaintenanceTool"
    install_dir.mkdir()

    monkeypatch.delenv("MAINTENANCETOOL_WORKSPACE_ROOT", raising=False)
    monkeypatch.setattr(runtime_paths.os, "name", "nt")
    monkeypatch.setattr(runtime_paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(runtime_paths, "_resolve_executable_dir", lambda: install_dir)

    resolved = runtime_paths._resolve_workspace_root()

    assert resolved == (install_dir / "workspace").resolve()


def test_resolve_windows_workspace_root_prefers_explicit_documents_root(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MAINTENANCETOOL_DOCUMENTS_ROOT", str(tmp_path / "DocsRoot"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "UserProfile"))

    resolved = runtime_paths._resolve_windows_workspace_root()

    assert resolved == tmp_path / "DocsRoot" / runtime_paths.APP_NAME


def test_resolve_windows_documents_root_falls_back_to_home_documents(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("MAINTENANCETOOL_DOCUMENTS_ROOT", raising=False)
    monkeypatch.delenv("USERPROFILE", raising=False)
    monkeypatch.setattr(runtime_paths.Path, "home", lambda: tmp_path / "Home")

    resolved = runtime_paths._resolve_windows_documents_root()

    assert resolved == tmp_path / "Home" / "Documents"


def test_ensure_workspace_falls_back_to_temp_directory(monkeypatch, tmp_path: Path) -> None:
    preferred = runtime_paths.RuntimeWorkspace(
        root=tmp_path / "blocked",
        config_dir=tmp_path / "blocked" / "config",
        state_dir=tmp_path / "blocked" / "state",
        report_dir=tmp_path / "blocked" / "reports",
        quarantine_dir=tmp_path / "blocked" / ".quarantine",
    )
    temp_root = tmp_path / "temp-root"

    monkeypatch.setattr(runtime_paths.tempfile, "gettempdir", lambda: str(temp_root))

    attempted: list[Path] = []

    def fake_create(workspace: runtime_paths.RuntimeWorkspace) -> None:
        attempted.append(workspace.root)
        if workspace.root == preferred.root:
            raise OSError("blocked")
        workspace.root.mkdir(parents=True, exist_ok=True)
        workspace.config_dir.mkdir(parents=True, exist_ok=True)
        workspace.state_dir.mkdir(parents=True, exist_ok=True)
        workspace.report_dir.mkdir(parents=True, exist_ok=True)
        workspace.quarantine_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(runtime_paths, "_create_workspace_dirs", fake_create)

    resolved = runtime_paths._ensure_workspace(preferred)

    assert attempted == [preferred.root, temp_root / runtime_paths.APP_NAME]
    assert resolved.root == temp_root / runtime_paths.APP_NAME


def test_get_packaged_template_dir_ignores_empty_meipass(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(runtime_paths.sys, "_MEIPASS", "", raising=False)
    (tmp_path / "bin").mkdir()
    fallback_template = tmp_path / "bin" / "config_templates"
    fallback_template.mkdir()
    monkeypatch.setattr(runtime_paths.sys, "executable", str(tmp_path / "bin" / "tool.exe"))

    selected = runtime_paths.get_packaged_template_dir()

    assert selected == fallback_template


def test_get_packaged_template_dir_prefers_meipass_templates(monkeypatch, tmp_path: Path) -> None:
    meipass_template = tmp_path / "bundle" / "config_templates"
    meipass_template.mkdir(parents=True)
    executable_template = tmp_path / "bin" / "config_templates"
    executable_template.mkdir(parents=True)
    monkeypatch.setattr(runtime_paths.sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False)
    monkeypatch.setattr(runtime_paths.sys, "executable", str(tmp_path / "bin" / "tool.exe"))

    selected = runtime_paths.get_packaged_template_dir()

    assert selected == meipass_template


def test_bootstrap_config_templates_copies_all_default_files(monkeypatch, tmp_path: Path) -> None:
    template_dir = tmp_path / "bundle" / "config_templates"
    template_dir.mkdir(parents=True)
    for name in (
        "fixedTargets.json",
        "denyRules.json",
        "discover.config.json",
        "learning.config.json",
    ):
        (template_dir / name).write_text(f"template:{name}\n", encoding="utf-8")

    config_dir = tmp_path / "workspace" / "config"
    monkeypatch.setattr(runtime_paths, "get_packaged_template_dir", lambda: template_dir)

    runtime_paths._bootstrap_config_templates(config_dir)

    for name in (
        "fixedTargets.json",
        "denyRules.json",
        "discover.config.json",
        "learning.config.json",
    ):
        assert (config_dir / name).read_text(encoding="utf-8") == f"template:{name}\n"
