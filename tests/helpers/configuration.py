from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_DISCOVER_CONFIG = {
    "defaultDepth": 1,
    "maxDepth": 2,
    "topN": 5,
    "minBytes": 1,
    "scopePolicies": {},
    "pathOverrides": [],
}

DEFAULT_LEARNING_CONFIG = {
    "newItemPolicy": {"minBytes": 1, "promoteNewPaths": True},
    "changePolicy": {"sizeDeltaBytes": 10, "sizeDeltaRatio": 0.1},
    "stalePolicy": {"missingCountThreshold": 2, "suggestOnly": True},
    "groupingPolicy": {"groupBy": ["scope"]},
}


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_standard_config(
    config_dir: Path,
    *,
    fixed_targets: list[dict[str, Any]],
    deny_rules: list[dict[str, Any]] | None = None,
    discover: dict[str, Any] | None = None,
    learning: dict[str, Any] | None = None,
) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    write_json(config_dir / "fixedTargets.json", fixed_targets)
    write_json(config_dir / "denyRules.json", deny_rules or [])
    write_json(config_dir / "discover.config.json", _merge_dict(DEFAULT_DISCOVER_CONFIG, discover or {}))
    write_json(config_dir / "learning.config.json", _merge_dict(DEFAULT_LEARNING_CONFIG, learning or {}))


def write_legacy_sandbox_config(
    config_dir: Path,
    *,
    fixed_targets: list[dict[str, Any]],
    deny_rules: list[dict[str, Any]] | None = None,
    discover: dict[str, Any] | None = None,
    learning: dict[str, Any] | None = None,
) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    write_json(config_dir / "fixedTargets.json", fixed_targets)
    write_json(config_dir / "denyRules.json", deny_rules or [])
    write_json(
        config_dir / "discover.config.json",
        {
            "defaultDepth": 1,
            "maxEntriesPerRoot": 10,
            "scopePolicies": {"windows": {"defaultDepth": 1}},
            **(discover or {}),
        },
    )
    write_json(
        config_dir / "learning.config.json",
        {
            "promoteNewPath": True,
            "minBytesForPromotion": 1,
            "retireMissingAfterRuns": 3,
            **(learning or {}),
        },
    )


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged
