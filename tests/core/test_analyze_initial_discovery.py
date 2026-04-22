import json
from pathlib import Path

from maintenancetool.core.config_expansion import expand_config_path
from maintenancetool.services.analyze import run_analyze_service
from tests.helpers.configuration import write_json


def test_analyze_initial_discovery_finds_candidates_without_fixed_targets(
    monkeypatch,
    tmp_path: Path,
) -> None:
    local_appdata = tmp_path / "LocalAppData"
    appdata = tmp_path / "AppData"
    temp_root = local_appdata / "Temp"
    code_logs_root = appdata / "Code" / "logs"
    cache_dir = temp_root / "VendorCache" / "Cache"
    logs_dir = code_logs_root / "2026-04-22"
    cache_dir.mkdir(parents=True)
    logs_dir.mkdir(parents=True)
    (cache_dir / "a.bin").write_bytes(b"a" * 64)
    (logs_dir / "main.log").write_bytes(b"b" * 32)

    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))
    monkeypatch.setenv("APPDATA", str(appdata))

    config_dir = tmp_path / "config"
    state_dir = tmp_path / "state"
    config_dir.mkdir()
    state_dir.mkdir()
    write_json(config_dir / "fixedTargets.json", [])
    write_json(config_dir / "denyRules.json", [])
    write_json(
        config_dir / "discover.config.json",
        {
            "defaultDepth": 1,
            "maxDepth": 3,
            "topN": 20,
            "minBytes": 1,
            "scopePolicies": {},
            "pathOverrides": [],
        },
    )
    write_json(
        config_dir / "learning.config.json",
        {
            "newItemPolicy": {"minBytes": 1, "promoteNewPaths": True},
            "changePolicy": {"sizeDeltaBytes": 10, "sizeDeltaRatio": 0.1},
            "stalePolicy": {"missingCountThreshold": 2, "suggestOnly": True},
            "groupingPolicy": {"groupBy": []},
            "safetyPolicy": {},
        },
    )

    def local_path_resolver(path: str, *, scope: str) -> Path:
        if scope != "windows":
            return Path(path)
        expanded = expand_config_path(path)
        normalized = expanded.replace("\\", "/")
        return Path(normalized)

    result = run_analyze_service(
        config_path=config_dir,
        state_path=state_dir,
        local_path_resolver=local_path_resolver,
    )

    assert result.entries
    assert result.suggestions
    pending = json.loads((state_dir / "pending.json").read_text(encoding="utf-8"))
    pending_paths = {item["path"] for item in pending["suggestions"]}
    assert any(path.endswith("\\Cache") for path in pending_paths)
    assert any("\\Code\\logs\\" in path for path in pending_paths)
