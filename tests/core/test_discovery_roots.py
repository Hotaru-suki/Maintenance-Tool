from pathlib import Path

from maintenancetool.core.discovery_roots import default_discover_roots, resolve_discover_roots
from maintenancetool.core.config_loader import load_all_configs
from tests.helpers.configuration import write_json


def test_default_discover_roots_uses_windows_environment(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))

    roots = default_discover_roots()

    assert roots
    assert any("LocalAppData" in root for _scope, root in roots)


def test_resolve_discover_roots_falls_back_when_config_has_no_roots(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
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
