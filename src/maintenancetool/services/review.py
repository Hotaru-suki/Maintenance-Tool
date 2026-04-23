from __future__ import annotations

from pathlib import Path

from maintenancetool.core.config_loader import load_all_configs
from maintenancetool.core.learning_decisions import (
    load_learning_decision_state,
    update_learning_decision_state,
    write_learning_decision_state,
)
from maintenancetool.core.pending import load_pending_state, write_pending_state
from maintenancetool.core.rules import (
    apply_pending_review,
    promote_review_targets_to_fixed,
    write_deny_rules,
    write_fixed_targets,
    write_target_list,
)
from maintenancetool.models.schemas import PendingState
from maintenancetool.services.results import ReviewPendingServiceResult, ReviewPromotionServiceResult


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
    review_targets_path = config_path / "reviewTargets.json"
    deny_rules_path = config_path / "denyRules.json"
    configs = load_all_configs(config_path)
    pending_state = load_pending_state(pending_path)
    if pending_state is None or not pending_state.suggestions:
        return ReviewPendingServiceResult(pending_state=None)

    accepted = {item.id for item in pending_state.suggestions} if accept_all else accept_ids
    updated_targets, updated_review_targets, updated_deny_rules, remaining, accepted_items, rejected_items = apply_pending_review(
        fixed_targets=configs["fixedTargets"],
        review_targets=configs["reviewTargets"],
        deny_rules=configs["denyRules"],
        suggestions=pending_state.suggestions,
        accept_ids=accepted,
        reject_ids=reject_ids or set(),
    )
    write_fixed_targets(fixed_targets_path, updated_targets)
    write_target_list(review_targets_path, updated_review_targets)
    write_deny_rules(deny_rules_path, updated_deny_rules)
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
        review_targets_path=review_targets_path,
        deny_rules_path=deny_rules_path,
        pending_path=pending_path,
    )


def run_review_promotion_service(
    *,
    config_path: Path,
    promote_all: bool,
    target_ids: set[str],
) -> ReviewPromotionServiceResult:
    fixed_targets_path = config_path / "fixedTargets.json"
    review_targets_path = config_path / "reviewTargets.json"
    configs = load_all_configs(config_path)
    updated_targets, updated_review_targets, promoted = promote_review_targets_to_fixed(
        fixed_targets=configs["fixedTargets"],
        review_targets=configs["reviewTargets"],
        promote_ids=target_ids,
        promote_all=promote_all,
    )
    write_fixed_targets(fixed_targets_path, updated_targets)
    write_target_list(review_targets_path, updated_review_targets)
    return ReviewPromotionServiceResult(
        fixed_targets_path=fixed_targets_path,
        review_targets_path=review_targets_path,
        promoted=promoted,
        remaining_review_targets=updated_review_targets,
    )
