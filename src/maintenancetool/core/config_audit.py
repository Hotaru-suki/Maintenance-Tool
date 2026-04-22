from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ConfigFileAudit:
    name: str
    path: Path
    expected_kind: str
    exists: bool
    valid_json: bool
    actual_kind: str | None = None
    item_count: int | None = None
    notes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ConfigAuditSummary:
    profile: str
    fixed_targets_count: int | None
    deny_rules_count: int | None
    enabled_fixed_targets: int | None
    enabled_deny_rules: int | None
    scope_hints: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ConfigAuditResult:
    files: list[ConfigFileAudit]
    summary: ConfigAuditSummary | None
    raw_values: dict[str, Any] = field(default_factory=dict)


def audit_config_directory(config_dir: Path) -> ConfigAuditResult:
    specs = [
        ("fixedTargets.json", "array"),
        ("denyRules.json", "array"),
        ("discover.config.json", "object"),
        ("learning.config.json", "object"),
    ]
    audits: list[ConfigFileAudit] = []
    raw_values: dict[str, Any] = {}

    for name, expected_kind in specs:
        audit = _audit_json_file(config_dir / name, expected_kind=expected_kind)
        audits.append(audit)
        if audit.valid_json and not audit.errors:
            raw_values[name] = _read_json(config_dir / name)

    return ConfigAuditResult(
        files=audits,
        summary=_build_summary(raw_values),
        raw_values=raw_values,
    )


def _audit_json_file(path: Path, *, expected_kind: str) -> ConfigFileAudit:
    audit = ConfigFileAudit(
        name=path.name,
        path=path,
        expected_kind=expected_kind,
        exists=path.exists(),
        valid_json=False,
    )
    if not path.exists():
        audit.errors.append("missing file")
        return audit

    try:
        raw = path.read_text(encoding="utf-8-sig").strip()
    except OSError as exc:
        audit.errors.append(str(exc))
        return audit

    if not raw:
        audit.errors.append("empty file")
        return audit

    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        audit.errors.append(f"invalid JSON: {exc.msg}")
        return audit

    audit.valid_json = True
    actual_kind = _json_kind(value)
    audit.actual_kind = actual_kind
    if actual_kind != expected_kind:
        audit.errors.append(f"expected {expected_kind}, got {actual_kind}")
        return audit

    if isinstance(value, list):
        audit.item_count = len(value)
        if not value:
            audit.notes.append("empty list")
    elif isinstance(value, dict):
        audit.item_count = len(value)
        if not value:
            audit.notes.append("empty object")

    return audit


def _build_summary(raw_values: dict[str, Any]) -> ConfigAuditSummary | None:
    fixed_targets = raw_values.get("fixedTargets.json")
    deny_rules = raw_values.get("denyRules.json")
    discover_config = raw_values.get("discover.config.json")
    learning_config = raw_values.get("learning.config.json")
    if (
        not isinstance(fixed_targets, list)
        or not isinstance(deny_rules, list)
        or not isinstance(discover_config, dict)
        or not isinstance(learning_config, dict)
    ):
        return None

    enabled_fixed_targets = sum(1 for item in fixed_targets if item.get("enabled", True))
    enabled_deny_rules = sum(1 for item in deny_rules if item.get("enabled", True))
    scope_hints = sorted(
        {
            str(item.get("scopeHint", "auto"))
            for item in [*fixed_targets, *deny_rules]
            if isinstance(item, dict)
        }
    )
    has_learning_defaults = bool(discover_config) and bool(learning_config)
    if not fixed_targets and not deny_rules and has_learning_defaults:
        profile = "learning-driven-initial"
    elif not fixed_targets and not deny_rules:
        profile = "empty-template"
    elif any(_looks_like_sandbox_path(item.get("path")) for item in fixed_targets if isinstance(item, dict)):
        profile = "sandbox-sample"
    else:
        profile = "configured"

    return ConfigAuditSummary(
        profile=profile,
        fixed_targets_count=len(fixed_targets),
        deny_rules_count=len(deny_rules),
        enabled_fixed_targets=enabled_fixed_targets,
        enabled_deny_rules=enabled_deny_rules,
        scope_hints=scope_hints,
    )


def _json_kind(value: Any) -> str:
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _looks_like_sandbox_path(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.replace("/", "\\").lower()
    return "maintenancetoolsandbox" in normalized


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))
