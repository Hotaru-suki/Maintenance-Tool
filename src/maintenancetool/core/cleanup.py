from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from maintenancetool.core.path_adapter import LocalPathResolver, resolve_local_path
from maintenancetool.core.scope import resolve_scope
from maintenancetool.core.safety import evaluate_fixed_target
from maintenancetool.models.schemas import (
    CleanupExecutionItem,
    CleanupExecutionResult,
    CleanupPlan,
    CleanupPlanItem,
    DenyRule,
    FixedTarget,
    QuarantineRecord,
    RestoreExecutionItem,
    RestoreExecutionResult,
    SafetyPolicy,
)


def build_cleanup_plan(
    *,
    fixed_targets: list[FixedTarget],
    deny_rules: list[DenyRule],
    safety_policy: SafetyPolicy,
    mode: str,
    local_path_resolver: LocalPathResolver = resolve_local_path,
) -> CleanupPlan:
    items: list[CleanupPlanItem] = []
    for target in fixed_targets:
        if not target.enabled or target.retired:
            continue
        scope = resolve_scope(target.path, target.scopeHint)
        for_delete = mode == "delete"
        decision = evaluate_fixed_target(
            target,
            deny_rules,
            local_path_resolver=local_path_resolver,
            safety_policy=safety_policy,
            for_delete=for_delete,
        )
        local_path = local_path_resolver(target.path, scope=scope)
        size_bytes = _measure_target(local_path, depth=target.depth)
        requires_manual_confirm = decision.requires_manual_confirm or (
            size_bytes >= safety_policy.requireManualConfirmAboveBytes
        )
        risk_level = (
            "medium"
            if requires_manual_confirm and decision.risk_level == "low"
            else decision.risk_level
        )
        reason = (
            "target exceeds manual confirmation size threshold"
            if size_bytes >= safety_policy.requireManualConfirmAboveBytes
            else decision.reason
        )
        allowed = (
            decision.allow_scan and mode in {"dry-run", "quarantine"}
        ) or (
            decision.allow_delete and mode == "delete"
        )
        if for_delete and allowed:
            requires_manual_confirm = True
            risk_level = "high"
            reason = "delete mode requires explicit confirmation"
        items.append(
            CleanupPlanItem(
                targetId=target.id or "",
                path=target.path,
                scope=scope,
                deleteMode=target.deleteMode,
                category=target.category,
                sizeBytes=size_bytes,
                allowed=allowed,
                reason=reason,
                riskLevel=risk_level,
                requiresManualConfirm=requires_manual_confirm,
                action="skip" if not allowed else mode,
            )
        )

    return CleanupPlan(mode=mode, createdAt=_utc_now(), items=items)


def apply_quarantine_plan(
    *,
    plan: CleanupPlan,
    fixed_targets: list[FixedTarget],
    deny_rules: list[DenyRule],
    safety_policy: SafetyPolicy,
    quarantine_dir: Path,
    confirmed_target_ids: set[str] | None = None,
    local_path_resolver: LocalPathResolver = resolve_local_path,
) -> CleanupExecutionResult:
    if plan.mode != "quarantine":
        raise ValueError("Only quarantine plans can be applied")

    quarantine_dir.mkdir(parents=True, exist_ok=True)
    target_map = {target.id: target for target in fixed_targets if target.id}
    results: list[CleanupExecutionItem] = []
    confirmed_ids = confirmed_target_ids or set()

    allowed_items = [item for item in plan.items if item.allowed]
    if len(allowed_items) > safety_policy.maxItemsPerRun:
        raise ValueError("cleanup plan exceeds maxItemsPerRun")
    if sum(item.sizeBytes for item in allowed_items) > safety_policy.maxBytesPerRun:
        raise ValueError("cleanup plan exceeds maxBytesPerRun")

    for item in plan.items:
        target = target_map.get(item.targetId)
        if target is None:
            results.append(
                CleanupExecutionItem(
                    targetId=item.targetId,
                    path=item.path,
                    outcome="failed",
                    detail="target definition not found",
                )
            )
            continue

        decision = evaluate_fixed_target(
            target,
            deny_rules,
            local_path_resolver=local_path_resolver,
            safety_policy=safety_policy,
        )
        if not decision.allow_scan:
            results.append(
                CleanupExecutionItem(
                    targetId=item.targetId,
                    path=item.path,
                    outcome="skipped",
                    detail=decision.reason,
                )
            )
            continue

        scope = resolve_scope(target.path, target.scopeHint)
        source_path = local_path_resolver(target.path, scope=scope)
        if not source_path.exists():
            results.append(
                CleanupExecutionItem(
                    targetId=item.targetId,
                    path=item.path,
                    outcome="skipped",
                    detail="source path does not exist",
                )
            )
            continue

        if item.requiresManualConfirm and item.targetId not in confirmed_ids:
            results.append(
                CleanupExecutionItem(
                    targetId=item.targetId,
                    path=item.path,
                    outcome="skipped",
                    detail="manual confirmation required by safety policy",
                )
            )
            continue

        record = _build_quarantine_record(
            quarantine_dir=quarantine_dir,
            item=item,
            source_name=source_path.name,
        )
        destination = _quarantine_payload_path(quarantine_dir, record.recordId)
        try:
            moved_path = _move_to_quarantine(
                source_path=source_path,
                destination=destination,
                delete_mode=target.deleteMode,
            )
            _write_quarantine_record(
                quarantine_dir=quarantine_dir,
                record=record.model_copy(update={"sourceName": source_path.name}),
            )
            results.append(
                CleanupExecutionItem(
                    targetId=item.targetId,
                    path=item.path,
                    outcome="applied",
                    detail="moved to quarantine",
                    quarantinePath=str(moved_path),
                    quarantineRecordId=record.recordId,
                )
            )
        except OSError as exc:
            results.append(
                CleanupExecutionItem(
                    targetId=item.targetId,
                    path=item.path,
                    outcome="failed",
                    detail=str(exc),
                )
            )

    return CleanupExecutionResult(mode="quarantine", createdAt=_utc_now(), items=results)


def list_quarantine_records(quarantine_dir: Path) -> list[QuarantineRecord]:
    records_dir = quarantine_dir / "records"
    if not records_dir.exists():
        return []
    records: list[QuarantineRecord] = []
    for record_dir in sorted(path for path in records_dir.iterdir() if path.is_dir()):
        manifest_path = record_dir / "record.json"
        if not manifest_path.exists():
            continue
        try:
            records.append(
                QuarantineRecord.model_validate_json(manifest_path.read_text(encoding="utf-8"))
            )
        except Exception:
            continue
    return records


def restore_quarantine_records(
    *,
    quarantine_dir: Path,
    record_ids: set[str],
    local_path_resolver: LocalPathResolver = resolve_local_path,
) -> RestoreExecutionResult:
    available = {record.recordId: record for record in list_quarantine_records(quarantine_dir)}
    results: list[RestoreExecutionItem] = []

    for record_id in sorted(record_ids):
        record = available.get(record_id)
        if record is None:
            results.append(
                RestoreExecutionItem(
                    recordId=record_id,
                    sourcePath="unknown",
                    outcome="failed",
                    detail="quarantine record not found",
                )
            )
            continue
        if record.status != "active":
            results.append(
                RestoreExecutionItem(
                    recordId=record.recordId,
                    sourcePath=record.sourcePath,
                    outcome="skipped",
                    detail="record is not active",
                    quarantinePath=str(_quarantine_payload_path(quarantine_dir, record.recordId)),
                )
            )
            continue

        payload_path = _quarantine_payload_path(quarantine_dir, record.recordId)
        source_path = local_path_resolver(record.sourcePath, scope=record.sourceScope)
        try:
            _restore_quarantine_payload(
                source_path=source_path,
                payload_path=payload_path,
                delete_mode=record.deleteMode,
            )
            _write_quarantine_record(
                quarantine_dir=quarantine_dir,
                record=record.model_copy(update={"status": "restored", "restoredAt": _utc_now()}),
            )
            results.append(
                RestoreExecutionItem(
                    recordId=record.recordId,
                    sourcePath=record.sourcePath,
                    outcome="applied",
                    detail="restored from quarantine",
                    quarantinePath=str(payload_path),
                )
            )
        except (OSError, ValueError) as exc:
            results.append(
                RestoreExecutionItem(
                    recordId=record.recordId,
                    sourcePath=record.sourcePath,
                    outcome="failed",
                    detail=str(exc),
                    quarantinePath=str(payload_path),
                )
            )

    return RestoreExecutionResult(createdAt=_utc_now(), items=results)


def apply_delete_plan(
    *,
    plan: CleanupPlan,
    fixed_targets: list[FixedTarget],
    deny_rules: list[DenyRule],
    safety_policy: SafetyPolicy,
    delete_confirmation: str,
    confirmed_target_ids: set[str] | None = None,
    local_path_resolver: LocalPathResolver = resolve_local_path,
) -> CleanupExecutionResult:
    if plan.mode != "delete":
        raise ValueError("Only delete plans can be applied")
    if delete_confirmation != "DELETE":
        raise ValueError("delete execution requires --confirm-delete DELETE")

    target_map = {target.id: target for target in fixed_targets if target.id}
    results: list[CleanupExecutionItem] = []
    confirmed_ids = confirmed_target_ids or set()

    allowed_items = [item for item in plan.items if item.allowed]
    if len(allowed_items) > safety_policy.maxItemsPerRun:
        raise ValueError("cleanup plan exceeds maxItemsPerRun")
    if sum(item.sizeBytes for item in allowed_items) > safety_policy.maxBytesPerRun:
        raise ValueError("cleanup plan exceeds maxBytesPerRun")

    for item in plan.items:
        target = target_map.get(item.targetId)
        if target is None:
            results.append(
                CleanupExecutionItem(
                    targetId=item.targetId,
                    path=item.path,
                    outcome="failed",
                    detail="target definition not found",
                )
            )
            continue

        decision = evaluate_fixed_target(
            target,
            deny_rules,
            local_path_resolver=local_path_resolver,
            safety_policy=safety_policy,
            for_delete=True,
        )
        if not decision.allow_delete:
            results.append(
                CleanupExecutionItem(
                    targetId=item.targetId,
                    path=item.path,
                    outcome="skipped",
                    detail=decision.reason,
                )
            )
            continue

        scope = resolve_scope(target.path, target.scopeHint)
        source_path = local_path_resolver(target.path, scope=scope)
        if not source_path.exists():
            results.append(
                CleanupExecutionItem(
                    targetId=item.targetId,
                    path=item.path,
                    outcome="skipped",
                    detail="source path does not exist",
                )
            )
            continue

        if item.requiresManualConfirm and item.targetId not in confirmed_ids:
            results.append(
                CleanupExecutionItem(
                    targetId=item.targetId,
                    path=item.path,
                    outcome="skipped",
                    detail="manual confirmation required by safety policy",
                )
            )
            continue

        try:
            _delete_target(source_path=source_path, delete_mode=target.deleteMode)
            results.append(
                CleanupExecutionItem(
                    targetId=item.targetId,
                    path=item.path,
                    outcome="applied",
                    detail="deleted",
                )
            )
        except OSError as exc:
            results.append(
                CleanupExecutionItem(
                    targetId=item.targetId,
                    path=item.path,
                    outcome="failed",
                    detail=str(exc),
                )
            )

    return CleanupExecutionResult(mode="delete", createdAt=_utc_now(), items=results)


def _move_to_quarantine(*, source_path: Path, destination: Path, delete_mode: str) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if delete_mode == "directory":
        return Path(shutil.move(str(source_path), str(destination)))

    if source_path.is_file():
        return Path(shutil.move(str(source_path), str(destination)))

    moved_root = destination
    moved_root.mkdir(parents=True, exist_ok=True)
    for child in list(source_path.iterdir()):
        moved_child = moved_root / child.name
        shutil.move(str(child), str(moved_child))
    return moved_root


def _restore_quarantine_payload(*, source_path: Path, payload_path: Path, delete_mode: str) -> None:
    if not payload_path.exists():
        raise ValueError("quarantine payload does not exist")

    source_path.parent.mkdir(parents=True, exist_ok=True)
    if delete_mode == "directory":
        if source_path.exists():
            raise ValueError("source path already exists")
        shutil.move(str(payload_path), str(source_path))
        return

    if payload_path.is_file():
        if source_path.exists():
            raise ValueError("source path already exists")
        shutil.move(str(payload_path), str(source_path))
        return

    source_path.mkdir(parents=True, exist_ok=True)
    if any(source_path.iterdir()):
        raise ValueError("source directory is not empty")
    for child in list(payload_path.iterdir()):
        shutil.move(str(child), str(source_path / child.name))
    payload_path.rmdir()


def _delete_target(*, source_path: Path, delete_mode: str) -> None:
    if delete_mode == "directory":
        if source_path.is_dir():
            shutil.rmtree(source_path)
        elif source_path.exists():
            source_path.unlink()
        return

    if source_path.is_file():
        source_path.unlink()
        return

    for child in list(source_path.iterdir()):
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _measure_target(path: Path, depth: int) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    queue: list[tuple[Path, int]] = [(path, 0)]
    while queue:
        current, current_depth = queue.pop(0)
        if current_depth > depth:
            continue
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in children:
            try:
                if child.is_symlink():
                    continue
                if child.is_file():
                    total += child.stat().st_size
                elif child.is_dir() and current_depth < depth:
                    queue.append((child, current_depth + 1))
            except OSError:
                continue
    return total


def _quarantine_name(target_id: str, source_name: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{target_id}-{source_name}"


def _build_quarantine_record(*, quarantine_dir: Path, item: CleanupPlanItem, source_name: str) -> QuarantineRecord:
    record_id = _quarantine_name(item.targetId or "target", source_name) + f"-{uuid.uuid4().hex[:8]}"
    return QuarantineRecord(
        recordId=record_id,
        targetId=item.targetId,
        sourcePath=item.path,
        sourceScope=item.scope,
        deleteMode=item.deleteMode,
        category=item.category,
        sizeBytes=item.sizeBytes,
        sourceName=source_name,
        quarantinedAt=_utc_now(),
    )


def _quarantine_record_dir(quarantine_dir: Path, record_id: str) -> Path:
    return quarantine_dir / "records" / record_id


def _quarantine_payload_path(quarantine_dir: Path, record_id: str) -> Path:
    return _quarantine_record_dir(quarantine_dir, record_id) / "payload"


def _write_quarantine_record(*, quarantine_dir: Path, record: QuarantineRecord) -> Path:
    record_dir = _quarantine_record_dir(quarantine_dir, record.recordId)
    record_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = record_dir / "record.json"
    manifest_path.write_text(
        json.dumps(record.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
