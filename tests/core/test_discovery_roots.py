from pathlib import Path

from maintenancetool.core.discovery_roots import default_discover_roots, resolve_discover_roots
from maintenancetool.core.config_loader import load_all_configs
from tests.helpers.configuration import write_json


def test_default_discover_roots_uses_windows_environment(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    monkeypatch.setattr(
        "maintenancetool.core.discovery_roots._list_windows_fixed_drive_roots",
        lambda: [],
    )

    roots = default_discover_roots()

    assert roots
    assert any("LocalAppData" in root for _scope, root in roots)


def test_default_discover_roots_prefers_fixed_windows_drives(monkeypatch) -> None:
    monkeypatch.setattr(
        "maintenancetool.core.discovery_roots._list_windows_fixed_drive_roots",
        lambda: ["C:\\", "D:\\"],
    )

    roots = default_discover_roots()

    assert roots == [("windows", "C:"), ("windows", "D:")]


def test_resolve_discover_roots_falls_back_when_config_has_no_roots(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    monkeypatch.setattr(
        "maintenancetool.core.discovery_roots._list_windows_fixed_drive_roots",
        lambda: [],
    )
    write_json(tmp_path / "fixedTargets.json", [])
    write_json(tmp_path / "denyRules.json", [])
    write_json(
        tmp_path / "discover.config.json",
        {
            "defaultDepth": 1,
            "maxDepth": 2,
            "topN": 10,
            "minBytes": 1,
            "scopePolicies": {},
            "pathOverrides": [],
        },
    )
    write_json(
        tmp_path / "learning.config.json",
        {
            "newItemPolicy": {"minBytes": 1, "promoteNewPaths": True},
        },
    )

    configs = load_all_configs(tmp_path)
    roots = resolve_discover_roots(configs["fixedTargets"], configs["discover"])

    assert roots
    assert any("AppData" in root for _scope, root in roots)


def test_resolve_discover_roots_includes_fixed_drives_and_target_parents(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "maintenancetool.core.discovery_roots._list_windows_fixed_drive_roots",
        lambda: ["C:\\", "D:\\", "E:\\"],
    )
    write_json(
        tmp_path / "fixedTargets.json",
        [
            {
                "id": "known",
                "path": "F:\\Vendor\\Cache",
                "scopeHint": "windows",
            }
        ],
    )
    write_json(tmp_path / "reviewTargets.json", [])
    write_json(tmp_path / "denyRules.json", [])
    write_json(tmp_path / "discover.config.json", {"pathOverrides": []})
    write_json(tmp_path / "learning.config.json", {"newItemPolicy": {"minBytes": 1, "promoteNewPaths": True}})

    configs = load_all_configs(tmp_path)
    roots = resolve_discover_roots(configs["fixedTargets"], configs["discover"])

    assert ("windows", "C:") in roots
    assert ("windows", "D:") in roots
    assert ("windows", "E:") in roots
    assert ("windows", "F:\\Vendor") in roots
