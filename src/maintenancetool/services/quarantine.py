from __future__ import annotations

from pathlib import Path

from maintenancetool.core.cleanup import list_quarantine_records, restore_quarantine_records
from maintenancetool.core.path_adapter import LocalPathResolver, resolve_local_path
from maintenancetool.core.reporting import write_restore_execution_report
from maintenancetool.services.results import RestoreQuarantineServiceResult


def run_restore_quarantine_service(
    *,
    quarantine_dir: Path,
    report_dir: Path,
    record_ids: set[str],
    apply: bool,
    local_path_resolver: LocalPathResolver = resolve_local_path,
) -> RestoreQuarantineServiceResult:
    records = [record for record in list_quarantine_records(quarantine_dir) if record.status == "active"]
    result = RestoreQuarantineServiceResult(records=records)
    if not apply:
        return result

    execution = restore_quarantine_records(
        quarantine_dir=quarantine_dir,
        record_ids=record_ids,
        local_path_resolver=local_path_resolver,
    )
    report_path = write_restore_execution_report(report_dir, execution)
    result.execution = execution
    result.report_path = report_path
    return result
