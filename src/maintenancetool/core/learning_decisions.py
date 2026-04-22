from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from maintenancetool.models.schemas import (
    LearningDecisionEntry,
    LearningDecisionSummary,
    LearningDecisionState,
    PendingSuggestion,
)


def load_learning_decision_state(path: Path) -> LearningDecisionState | None:
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return None
    if raw == "[]":
        return None
    return LearningDecisionState.model_validate_json(raw)


def write_learning_decision_state(path: Path, state: LearningDecisionState) -> None:
    state_with_summary = state.model_copy(update={"summary": build_learning_decision_summary(state)})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state_with_summary.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def update_learning_decision_state(
    *,
    state: LearningDecisionState | None,
    accepted: list[PendingSuggestion],
    rejected: list[PendingSuggestion],
) -> LearningDecisionState:
    now = _utc_now()
    entries = {
        (entry.suggestedAction, entry.scope, entry.path): entry
        for entry in (state.decisions if state is not None else [])
    }
    for suggestion in accepted:
        key = (suggestion.suggestedAction, suggestion.scope, suggestion.path)
        existing = entries.get(key)
        entries[key] = LearningDecisionEntry(
            id=suggestion.id,
            path=suggestion.path,
            scope=suggestion.scope,
            suggestedAction=suggestion.suggestedAction,
            decision="accepted",
            category=suggestion.category,
            hitRule=suggestion.hitRule,
            hitRuleReason=suggestion.hitRuleReason,
            derivedFrom=suggestion.derivedFrom,
            lastReason=suggestion.reason,
            createdAt=existing.createdAt if existing is not None else now,
            updatedAt=now,
        )
    for suggestion in rejected:
        key = (suggestion.suggestedAction, suggestion.scope, suggestion.path)
        existing = entries.get(key)
        entries[key] = LearningDecisionEntry(
            id=suggestion.id,
            path=suggestion.path,
            scope=suggestion.scope,
            suggestedAction=suggestion.suggestedAction,
            decision="rejected",
            category=suggestion.category,
            hitRule=suggestion.hitRule,
            hitRuleReason=suggestion.hitRuleReason,
            derivedFrom=suggestion.derivedFrom,
            lastReason=suggestion.reason,
            createdAt=existing.createdAt if existing is not None else now,
            updatedAt=now,
        )
    return LearningDecisionState(
        updatedAt=now,
        summary=LearningDecisionSummary(),
        decisions=sorted(entries.values(), key=lambda item: (item.suggestedAction, item.scope, item.path)),
    )


def build_decision_index(
    state: LearningDecisionState | None,
) -> dict[tuple[str, str, str], LearningDecisionEntry]:
    if state is None:
        return {}
    return {
        (entry.suggestedAction, entry.scope, entry.path): entry
        for entry in state.decisions
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_learning_decision_summary(state: LearningDecisionState) -> LearningDecisionSummary:
    by_category = Counter(item.category or "uncategorized" for item in state.decisions)
    by_hit_rule = Counter(item.hitRule or "unknown" for item in state.decisions)
    accepted_count = sum(1 for item in state.decisions if item.decision == "accepted")
    rejected_count = sum(1 for item in state.decisions if item.decision == "rejected")
    return LearningDecisionSummary(
        totalDecisions=len(state.decisions),
        acceptedCount=accepted_count,
        rejectedCount=rejected_count,
        byCategory=dict(sorted(by_category.items())),
        byHitRule=dict(sorted(by_hit_rule.items())),
    )
