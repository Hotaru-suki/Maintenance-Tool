from __future__ import annotations

from pathlib import Path

from maintenancetool.core.config_loader import load_all_configs
from maintenancetool.core.learning_decisions import (
    load_learning_decision_state,
    update_learning_decision_state,
    write_learning_decision_state,
)
from maintenancetool.core.pending import load_pending_state, write_pending_state
from maintenancetool.core.rules import apply_pending_review, write_fixed_targets
from maintenancetool.models.schemas import PendingState
from maintenancetool.services.results import ReviewPendingServiceResult


def run_review_pending_service(
    *,
    config_path: Path,
    state_path: Path,
    accept_all: bool,
    accept_ids: set[str],
    reject_ids: set[str] | None = None,
) -> ReviewPendingServiceResult:
    pending_path = state_path / "pending.json"
    learning_decisions_path = state_path / "learningDecisions.json"
    fixed_targets_path = config_path / "fixedTargets.json"
    configs = load_all_configs(config_path)
    pending_state = load_pending_state(pending_path)
    if pending_state is None or not pending_state.suggestions:
        return ReviewPendingServiceResult(pending_state=None)

    accepted = {item.id for item in pending_state.suggestions} if accept_all else accept_ids
    updated_targets, remaining, accepted_items, rejected_items = apply_pending_review(
        fixed_targets=configs["fixedTargets"],
        suggestions=pending_state.suggestions,
        accept_ids=accepted,
        reject_ids=reject_ids or set(),
    )
    write_fixed_targets(fixed_targets_path, updated_targets)
    write_pending_state(
        pending_path,
        PendingState(createdAt=pending_state.createdAt, suggestions=remaining),
    )
    updated_learning_decisions = update_learning_decision_state(
        state=load_learning_decision_state(learning_decisions_path),
        accepted=accepted_items,
        rejected=rejected_items,
    )
    write_learning_decision_state(learning_decisions_path, updated_learning_decisions)
    return ReviewPendingServiceResult(
        pending_state=pending_state,
        accepted=accepted_items,
        rejected=rejected_items,
        remaining=remaining,
        fixed_targets_path=fixed_targets_path,
        pending_path=pending_path,
    )
