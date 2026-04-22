from pathlib import Path

import pytest

from maintenancetool.core.config_loader import load_all_configs, load_fixed_targets
from tests.helpers.configuration import write_json, write_standard_config


def test_load_all_configs_valid(tmp_path: Path) -> None:
    write_standard_config(
        tmp_path,
        fixed_targets=[
            {
                "id": "cache-root",
                "path": str(tmp_path / "sandbox" / "cache"),
                "enabled": True,
                "depth": 2,
                "deleteMode": "contents",
                "source": "manual",
            }
        ],
        deny_rules=[
            {
                "id": "protect-root",
                "path": str(tmp_path / "sandbox" / "protected"),
                "enabled": True,
                "reason": "protected",
            }
        ],
    )

    configs = load_all_configs(tmp_path)

    assert len(configs["fixedTargets"]) == 1
    assert configs["discover"].maxDepth == 2
    assert configs["learning"].stalePolicy.missingCountThreshold == 2
    assert configs["learning"].safetyPolicy.maxItemsPerRun == 100


def test_load_fixed_targets_rejects_duplicate_ids(tmp_path: Path) -> None:
    payload = [
        {"id": "dup", "path": "/tmp/a"},
        {"id": "dup", "path": "/tmp/b"},
    ]
    write_json(tmp_path / "fixedTargets.json", payload)

    with pytest.raises(ValueError, match="Duplicate id"):
        load_fixed_targets(tmp_path / "fixedTargets.json")


def test_load_all_configs_rejects_empty_file(tmp_path: Path) -> None:
    for name in [
        "fixedTargets.json",
        "denyRules.json",
        "discover.config.json",
        "learning.config.json",
    ]:
        (tmp_path / name).write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="is empty"):
        load_all_configs(tmp_path)


def test_load_all_configs_supports_legacy_config_shape(tmp_path: Path) -> None:
    write_json(
        tmp_path / "fixedTargets.json",
        [
            {
                "path": "C:\\MaintenanceToolSandbox\\fixtures\\browser\\cache",
                "scopeHint": "windows",
            }
        ],
    )
    write_json(
        tmp_path / "denyRules.json",
        [
            {
                "path": "C:\\MaintenanceToolSandbox\\fixtures\\protected",
                "scopeHint": "windows",
                "reason": "protected",
            }
        ],
    )
    write_json(
        tmp_path / "discover.config.json",
        {
            "defaultDepth": 2,
            "maxEntriesPerRoot": 500,
            "scopePolicies": {"windows": {"defaultDepth": 2}},
        },
    )
    write_json(
        tmp_path / "learning.config.json",
        {
            "promoteNewPath": True,
            "minBytesForPromotion": 1024,
            "retireMissingAfterRuns": 3,
        },
    )

    configs = load_all_configs(tmp_path)

    assert configs["fixedTargets"][0].id is not None
    assert configs["denyRules"][0].id is not None
    assert configs["discover"].topN == 500
    assert configs["learning"].newItemPolicy.minBytes == 1024
    assert configs["learning"].stalePolicy.missingCountThreshold == 3
    assert configs["learning"].safetyPolicy.maxItemsPerRun == 100


def test_load_all_configs_expands_environment_paths(monkeypatch, tmp_path: Path) -> None:
    local_appdata = tmp_path / "LocalAppData"
    appdata = tmp_path / "AppData"
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))
    monkeypatch.setenv("APPDATA", str(appdata))

    write_json(tmp_path / "fixedTargets.json", [])
    write_json(tmp_path / "denyRules.json", [])
    write_json(
        tmp_path / "discover.config.json",
        {
            "defaultDepth": 1,
            "maxDepth": 2,
            "pathOverrides": [
                {
                    "path": "%LOCALAPPDATA%\\Temp",
                    "scopeHint": "windows",
                },
                {
                    "path": "%APPDATA%\\Code\\logs",
                    "scopeHint": "windows",
                },
            ],
        },
    )
    write_json(
        tmp_path / "learning.config.json",
        {
            "newItemPolicy": {"minBytes": 1, "promoteNewPaths": True},
            "safetyPolicy": {
                "allowedRoots": [
                    {"path": "%LOCALAPPDATA%\\Temp", "scopeHint": "windows"},
                ]
            },
        },
    )

    configs = load_all_configs(tmp_path)

    assert configs["discover"].pathOverrides[0].path == f"{local_appdata}\\Temp"
    assert configs["discover"].pathOverrides[1].path == f"{appdata}\\Code\\logs"
    assert configs["learning"].safetyPolicy.allowedRoots[0].path == f"{local_appdata}\\Temp"
