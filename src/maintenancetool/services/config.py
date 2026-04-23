from __future__ import annotations

from pathlib import Path

from maintenancetool.core.config_audit import audit_config_directory
from maintenancetool.core.config_loader import load_all_configs
from maintenancetool.core.discovery_roots import discover_root_summary
from maintenancetool.core.hit_rules import hit_rule_summary
from maintenancetool.services.results import ConfigCheckServiceResult


def run_config_check_service(config_path: Path) -> ConfigCheckServiceResult:
    audit = audit_config_directory(config_path)
    file_summaries = [
        {
            "name": item.name,
            "path": item.path,
            "expected_kind": item.expected_kind,
            "exists": item.exists,
            "valid_json": item.valid_json,
            "actual_kind": item.actual_kind,
            "item_count": item.item_count,
            "notes": item.notes,
            "errors": item.errors,
        }
        for item in audit.files
    ]
    warnings: list[str] = []
    if audit.summary is not None:
        if audit.summary.profile == "learning-driven-initial":
            warnings.append("config profile is learning-driven-initial; analyze can learn candidates before any target is enabled")
        if audit.summary.profile == "empty-template":
            warnings.append("config profile is empty-template; no real targets are configured")
        if audit.summary.profile == "sandbox-sample":
            warnings.append("config profile looks like sandbox-sample; verify before using on a real machine")

    structural_errors = [
        f"{item.name}: {error}"
        for item in audit.files
        for error in item.errors
    ]
    if structural_errors:
        return ConfigCheckServiceResult(
            ok=False,
            errors=structural_errors,
            warnings=warnings,
            files=file_summaries,
            summary=_summary_to_dict(audit.summary),
        )

    try:
        configs = load_all_configs(config_path)
    except Exception as exc:
        return ConfigCheckServiceResult(
            ok=False,
            errors=[str(exc)],
            warnings=warnings,
            files=file_summaries,
            summary=_summary_to_dict(audit.summary),
        )

    summary = _summary_to_dict(audit.summary)
    if summary is not None:
        summary.update(
            discover_root_summary(
                [*configs["fixedTargets"], *configs["reviewTargets"]],
                configs["discover"],
            )
        )
        summary.update(hit_rule_summary())

    return ConfigCheckServiceResult(
        ok=True,
        errors=[],
        warnings=warnings,
        files=file_summaries,
        summary=summary,
    )


def _summary_to_dict(summary) -> dict[str, object] | None:
    if summary is None:
        return None
    return {
        "profile": summary.profile,
        "fixed_targets_count": summary.fixed_targets_count,
        "review_targets_count": summary.review_targets_count,
        "deny_rules_count": summary.deny_rules_count,
        "enabled_fixed_targets": summary.enabled_fixed_targets,
        "enabled_review_targets": summary.enabled_review_targets,
        "enabled_deny_rules": summary.enabled_deny_rules,
        "scope_hints": summary.scope_hints,
    }
