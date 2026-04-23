from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from maintenancetool.core.config_expansion import (
    expand_allowed_roots,
    expand_path_field,
)
from maintenancetool.core.scope import normalize_path, resolve_scope
from maintenancetool.models.schemas import (
    DenyRule,
    DiscoverConfig,
    FixedTarget,
    LearningConfig,
)


FIXED_TARGETS_ADAPTER = TypeAdapter(list[FixedTarget])
DENY_RULES_ADAPTER = TypeAdapter(list[DenyRule])


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")
    raw = path.read_text(encoding="utf-8-sig").strip()
    if not raw:
        raise ValueError(f"{path.name} is empty")
    return json.loads(raw)


def _read_json_optional_array(path: Path) -> Any:
    if not path.exists():
        return []
    return _read_json(path)


def load_fixed_targets(path: Path) -> list[FixedTarget]:
    raw = _read_json(path)
    if not isinstance(raw, list):
        raise ValueError(f"{path.name} must be a JSON array")
    targets = FIXED_TARGETS_ADAPTER.validate_python(_normalize_fixed_targets(raw))
    _validate_unique_ids_and_paths(targets, path.name)
    return targets


def load_optional_fixed_targets(path: Path) -> list[FixedTarget]:
    raw = _read_json_optional_array(path)
    if not isinstance(raw, list):
        raise ValueError(f"{path.name} must be a JSON array")
    targets = FIXED_TARGETS_ADAPTER.validate_python(_normalize_fixed_targets(raw))
    _validate_unique_ids_and_paths(targets, path.name)
    return targets


def load_deny_rules(path: Path) -> list[DenyRule]:
    raw = _read_json(path)
    if not isinstance(raw, list):
        raise ValueError(f"{path.name} must be a JSON array")
    rules = DENY_RULES_ADAPTER.validate_python(_normalize_deny_rules(raw))
    _validate_unique_ids_and_paths(rules, path.name)
    return rules


def load_discover_config(path: Path) -> DiscoverConfig:
    raw = _read_json(path)
    if not isinstance(raw, dict):
        raise ValueError(f"{path.name} must be a JSON object")
    return DiscoverConfig.model_validate(_normalize_discover_config(raw))


def load_learning_config(path: Path) -> LearningConfig:
    raw = _read_json(path)
    if not isinstance(raw, dict):
        raise ValueError(f"{path.name} must be a JSON object")
    return LearningConfig.model_validate(_normalize_learning_config(raw))


def load_all_configs(config_dir: Path) -> dict[str, Any]:
    fixed_targets = load_fixed_targets(config_dir / "fixedTargets.json")
    review_targets = load_optional_fixed_targets(config_dir / "reviewTargets.json")
    deny_rules = load_deny_rules(config_dir / "denyRules.json")
    discover = load_discover_config(config_dir / "discover.config.json")
    learning = load_learning_config(config_dir / "learning.config.json")

    return {
        "fixedTargets": fixed_targets,
        "reviewTargets": review_targets,
        "denyRules": deny_rules,
        "discover": discover,
        "learning": learning,
    }


def _validate_unique_ids_and_paths(items: list[Any], source_name: str) -> None:
    seen_ids: set[str] = set()
    seen_paths: set[tuple[str, str]] = set()

    for item in items:
        if not item.id:
            raise ValueError(f"Missing id in {source_name}")
        if item.id in seen_ids:
            raise ValueError(f"Duplicate id '{item.id}' in {source_name}")
        seen_ids.add(item.id)

        scope = resolve_scope(item.path, item.scopeHint)
        key = (scope, normalize_path(item.path, scope).lower() if scope == "windows" else normalize_path(item.path, scope))
        if key in seen_paths:
            raise ValueError(f"Duplicate path '{item.path}' in {source_name}")
        seen_paths.add(key)


def _normalize_fixed_targets(raw_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in raw_items:
        current = expand_path_field(item)
        current.setdefault("id", _stable_id("target", current.get("path", "")))
        normalized.append(current)
    return normalized


def _normalize_deny_rules(raw_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in raw_items:
        current = expand_path_field(item)
        current.setdefault("id", _stable_id("deny", current.get("path", "")))
        normalized.append(current)
    return normalized


def _normalize_discover_config(raw: dict[str, Any]) -> dict[str, Any]:
    current = dict(raw)
    current.setdefault("topN", current.pop("maxEntriesPerRoot", 20))
    current.setdefault("minBytes", 1)
    current.setdefault("pathOverrides", [])
    current.setdefault("scopePolicies", {})
    current["pathOverrides"] = [
        expand_path_field(item)
        if isinstance(item, dict)
        else item
        for item in current["pathOverrides"]
    ]
    return current


def _normalize_learning_config(raw: dict[str, Any]) -> dict[str, Any]:
    if "newItemPolicy" in raw:
        current = expand_allowed_roots(raw)
        current.setdefault("safetyPolicy", {})
        return current
    return expand_allowed_roots(
        {
        "newItemPolicy": {
            "minBytes": raw.get("minBytesForPromotion", 1),
            "promoteNewPaths": raw.get("promoteNewPath", True),
        },
        "changePolicy": {
            "sizeDeltaBytes": raw.get("sizeDeltaBytes", 1024 * 1024),
            "sizeDeltaRatio": raw.get("sizeDeltaRatio", 0.25),
        },
        "stalePolicy": {
            "missingCountThreshold": raw.get("retireMissingAfterRuns", 2),
            "suggestOnly": True,
        },
        "groupingPolicy": {
            "groupBy": ["scope"],
        },
        "safetyPolicy": {
            "maxItemsPerRun": raw.get("maxItemsPerRun", 100),
            "maxBytesPerRun": raw.get("maxBytesPerRun", 10 * 1024 * 1024 * 1024),
        },
        }
    )


def _stable_id(prefix: str, path: str) -> str:
    return f"{prefix}-{hashlib.sha1(path.encode('utf-8')).hexdigest()[:12]}"
