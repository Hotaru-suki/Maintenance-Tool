from __future__ import annotations

from pathlib import Path

from maintenancetool.core.cleanup import (
    apply_delete_plan,
    apply_quarantine_plan,
    build_cleanup_plan,
)
from maintenancetool.core.config_loader import load_all_configs
from maintenancetool.core.path_adapter import LocalPathResolver, resolve_local_path
from maintenancetool.core.reporting import (
    write_cleanup_execution_report,
    write_cleanup_plan_report,
)
from maintenancetool.services.results import CleanupServiceResult


def run_cleanup_service(
    *,
    config_path: Path,
    report_dir: Path,
    quarantine_dir: Path,
    mode: str,
    apply: bool,
    include_review_targets: bool = False,
    delete_confirmation: str | None = None,
    confirmed_target_ids: set[str] | None = None,
    local_path_resolver: LocalPathResolver = resolve_local_path,
) -> CleanupServiceResult:
    configs = load_all_configs(config_path)
    safety_policy = configs["learning"].safetyPolicy
    plan = build_cleanup_plan(
        fixed_targets=configs["fixedTargets"],
        review_targets=configs["reviewTargets"],
        deny_rules=configs["denyRules"],
        safety_policy=safety_policy,
        mode=mode,
        include_review_targets=include_review_targets,
        local_path_resolver=local_path_resolver,
    )
    report_path = write_cleanup_plan_report(report_dir, plan)
    result = CleanupServiceResult(
        plan=plan,
        report_path=report_path,
    )
    if not apply:
        return result

    if mode == "quarantine":
        execution = apply_quarantine_plan(
            plan=plan,
            fixed_targets=configs["fixedTargets"],
            review_targets=configs["reviewTargets"],
            deny_rules=configs["denyRules"],
            safety_policy=safety_policy,
            quarantine_dir=quarantine_dir,
            confirmed_target_ids=confirmed_target_ids,
            local_path_resolver=local_path_resolver,
        )
    else:
        execution = apply_delete_plan(
            plan=plan,
            fixed_targets=configs["fixedTargets"],
            review_targets=configs["reviewTargets"],
            deny_rules=configs["denyRules"],
            safety_policy=safety_policy,
            delete_confirmation=delete_confirmation or "",
            confirmed_target_ids=confirmed_target_ids,
            local_path_resolver=local_path_resolver,
        )
    execution_report_path = write_cleanup_execution_report(report_dir, execution)
    result.execution = execution
    result.execution_report_path = execution_report_path
    return result
