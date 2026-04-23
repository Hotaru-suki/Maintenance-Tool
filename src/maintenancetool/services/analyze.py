from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from maintenancetool.core.config_loader import load_all_configs
from maintenancetool.core.discovery_roots import (
    default_discovery_excluded_names,
    has_default_discover_environment,
    resolve_discover_roots,
)
from maintenancetool.core.diff import build_pending_suggestions, compute_last_seen_at, compute_missing_counts
from maintenancetool.core.learning_decisions import build_decision_index, load_learning_decision_state
from maintenancetool.core.path_adapter import LocalPathResolver, resolve_local_path
from maintenancetool.core.pending import write_pending_state
from maintenancetool.core.snapshot import (
    collect_snapshot_entries,
    load_snapshot_state,
    write_snapshot_state,
)
from maintenancetool.models.schemas import PendingState, SnapshotState
from maintenancetool.services.results import AnalyzeServiceResult


def run_analyze_service(
    *,
    config_path: Path,
    state_path: Path,
    discover_mode: Literal["full", "fixed-only"] = "full",
    local_path_resolver: LocalPathResolver = resolve_local_path,
) -> AnalyzeServiceResult:
    configs = load_all_configs(config_path)
    managed_targets = [*configs["fixedTargets"], *configs["reviewTargets"]]
    snapshot_path = state_path / "lastSnapshot.json"
    pending_path = state_path / "pending.json"
    learning_decisions_path = state_path / "learningDecisions.json"
    previous_state = load_snapshot_state(snapshot_path)
    learning_decisions = load_learning_decision_state(learning_decisions_path)
    discover_roots = (
        resolve_discover_roots(managed_targets, configs["discover"])
        if discover_mode == "full"
        else []
    )
    current_entries, progress = collect_snapshot_entries(
        fixed_targets=managed_targets,
        deny_rules=configs["denyRules"],
        discover_config=configs["discover"],
        include_discovery=discover_mode == "full",
        safety_policy=configs["learning"].safetyPolicy,
        local_path_resolver=local_path_resolver,
    )
    missing_counts = compute_missing_counts(
        managed_targets,
        current_entries,
        previous_state,
    )
    collected_at = (
        current_entries[0].collectedAt
        if current_entries
        else datetime.now(timezone.utc).isoformat()
    )
    last_seen_at = compute_last_seen_at(
        managed_targets,
        current_entries,
        previous_state,
        collected_at=collected_at,
    )
    suggestions = build_pending_suggestions(
        fixed_targets=configs["fixedTargets"],
        review_targets=configs["reviewTargets"],
        deny_rules=configs["denyRules"],
        current_entries=current_entries,
        previous_state=previous_state,
        decision_index=build_decision_index(learning_decisions),
        learning_config=configs["learning"],
        missing_counts=missing_counts,
    )
    write_snapshot_state(
        snapshot_path,
        SnapshotState(
            collectedAt=collected_at,
            entries=current_entries,
            missingCounts=missing_counts,
            lastSeenAt=last_seen_at,
        ),
    )
    write_pending_state(
        pending_path,
        PendingState(createdAt=collected_at, suggestions=suggestions),
    )
    initial_discovery_ready = bool(current_entries or suggestions) or has_default_discover_environment()
    return AnalyzeServiceResult(
        configs=configs,
        snapshot_path=snapshot_path,
        pending_path=pending_path,
        entries=current_entries,
        suggestions=suggestions,
        discover_roots=discover_roots,
        discover_mode=discover_mode,
        excluded_names=sorted(
            {
                name
                for scope, _root in discover_roots
                for name in default_discovery_excluded_names(scope)
            }
        ),
        progress=progress,
        initial_discovery_ready=initial_discovery_ready,
    )
