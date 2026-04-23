from __future__ import annotations

import json
from pathlib import Path

from maintenancetool.models.schemas import CleanupExecutionResult, CleanupPlan, RestoreExecutionResult


def write_cleanup_plan_report(report_dir: Path, plan: CleanupPlan) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    output_path = report_dir / _cleanup_plan_report_name(plan.mode)
    output_path.write_text(
        json.dumps(plan.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def write_cleanup_execution_report(
    report_dir: Path,
    result: CleanupExecutionResult,
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    output_path = report_dir / _cleanup_execution_report_name(result.mode)
    output_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def _cleanup_plan_report_name(mode: str) -> str:
    if mode == "quarantine":
        return "stage-plan.json"
    return f"cleanup-plan-{mode}.json"


def _cleanup_execution_report_name(mode: str) -> str:
    if mode == "quarantine":
        return "stage-execution.json"
    return f"cleanup-execution-{mode}.json"


def write_restore_execution_report(
    report_dir: Path,
    result: RestoreExecutionResult,
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    output_path = report_dir / "restore-execution.json"
    output_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path
