from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from maintenancetool.core.scope import normalize_path, resolve_scope
from maintenancetool.models.schemas import (
    FixedTarget,
    LearningConfig,
    LearningDecisionEntry,
    PendingSuggestion,
    SnapshotEntry,
    SnapshotState,
)


def build_pending_suggestions(
    *,
    fixed_targets: list[FixedTarget],
    current_entries: list[SnapshotEntry],
    previous_state: SnapshotState | None,
    decision_index: dict[tuple[str, str, str], LearningDecisionEntry] | None = None,
    learning_config: LearningConfig,
    missing_counts: dict[str, int],
) -> list[PendingSuggestion]:
    suggestions: list[PendingSuggestion] = []
    created_at = _utc_now()
    candidate_suggestions: list[PendingSuggestion] = []
    known_target_paths = {
        (
            resolve_scope(target.path, target.scopeHint),
            normalize_path(target.path, resolve_scope(target.path, target.scopeHint)),
        )
        for target in fixed_targets
    }
    previous_entries = {
        (entry.scope, normalize_path(entry.path, entry.scope)): entry
        for entry in (previous_state.entries if previous_state else [])
    }

    for entry in current_entries:
        key = (entry.scope, normalize_path(entry.path, entry.scope))
        if key in known_target_paths:
            continue
        if entry.sizeBytes < learning_config.newItemPolicy.minBytes:
            continue
        previous = previous_entries.get(key)
        is_new = previous is None
        changed = False
        if previous is not None:
            delta_bytes = abs(entry.sizeBytes - previous.sizeBytes)
            delta_ratio = (
                delta_bytes / previous.sizeBytes if previous.sizeBytes else float(delta_bytes > 0)
            )
            changed = (
                delta_bytes >= learning_config.changePolicy.sizeDeltaBytes
                and delta_ratio >= learning_config.changePolicy.sizeDeltaRatio
            )
        if not is_new and not changed:
            continue
        if not learning_config.newItemPolicy.promoteNewPaths:
            continue

        reason = (
            f"new candidate discovered under {entry.sourceRootId or 'unknown root'} "
            f"({entry.sizeBytes} bytes)"
            if is_new
            else (
                "candidate size changed significantly "
                f"from {previous.sizeBytes} to {entry.sizeBytes} bytes"
            )
        )
        candidate_suggestions.append(
            PendingSuggestion(
                id=_suggestion_id("addFixedTarget", entry.path, entry.scope),
                path=entry.path,
                scope=entry.scope,
                suggestedAction="addFixedTarget",
                reason=reason,
                category=entry.category,
                hitRule=entry.hitRule,
                hitRuleReason=entry.hitRuleReason,
                sizeBytes=entry.sizeBytes,
                derivedFrom=entry.sourceRootId,
                createdAt=created_at,
            )
        )

    threshold = learning_config.stalePolicy.missingCountThreshold
    for target in fixed_targets:
        misses = missing_counts.get(target.id, 0)
        if misses < threshold or target.retired:
            continue
        scope = resolve_scope(target.path, target.scopeHint)
        if not _stale_age_satisfied(
            target=target,
            previous_state=previous_state,
            learning_config=learning_config,
            created_at=created_at,
        ):
            continue
        stale_reason = f"target missing for {misses} analyze runs"
        required_days = learning_config.stalePolicy.lastSeenAgeDays
        if required_days is not None and previous_state is not None:
            last_seen_at = previous_state.lastSeenAt.get(target.id)
            if last_seen_at:
                age_days = _days_between(last_seen_at, created_at)
                stale_reason += f"; last seen {age_days} day(s) ago"
        suggestions.append(
            PendingSuggestion(
                id=_suggestion_id("retireFixedTarget", target.path, scope),
                path=normalize_path(target.path, scope),
                scope=scope,
                suggestedAction="retireFixedTarget",
                reason=stale_reason,
                category=target.category,
                hitRule=None,
                hitRuleReason=None,
                sizeBytes=None,
                derivedFrom=target.id,
                createdAt=created_at,
            )
        )

    suggestions.extend(_group_candidate_suggestions(candidate_suggestions, learning_config))
    deduped = dedupe_suggestions(suggestions)
    return _filter_suppressed_suggestions(deduped, decision_index or {})


def dedupe_suggestions(
    suggestions: list[PendingSuggestion],
) -> list[PendingSuggestion]:
    deduped: dict[tuple[str, str, str], PendingSuggestion] = {}
    for suggestion in suggestions:
        key = (suggestion.suggestedAction, suggestion.scope, suggestion.path)
        deduped[key] = suggestion
    return list(deduped.values())


def _filter_suppressed_suggestions(
    suggestions: list[PendingSuggestion],
    decision_index: dict[tuple[str, str, str], LearningDecisionEntry],
) -> list[PendingSuggestion]:
    filtered: list[PendingSuggestion] = []
    for suggestion in suggestions:
        key = (suggestion.suggestedAction, suggestion.scope, suggestion.path)
        decision = decision_index.get(key)
        if decision is None:
            filtered.append(suggestion)
            continue
        if decision.decision in {"accepted", "rejected"}:
            continue
        filtered.append(suggestion)
    return filtered


def compute_missing_counts(
    fixed_targets: list[FixedTarget],
    current_entries: list[SnapshotEntry],
    previous_state: SnapshotState | None,
) -> dict[str, int]:
    previous_counts = dict(previous_state.missingCounts) if previous_state else {}
    entry_keys = {
        (entry.scope, normalize_path(entry.path, entry.scope))
        for entry in current_entries
        if entry.sourceRootId is not None
    }
    result: dict[str, int] = {}
    for target in fixed_targets:
        scope = resolve_scope(target.path, target.scopeHint)
        key = (scope, normalize_path(target.path, scope))
        if key in entry_keys:
            result[target.id] = 0
        else:
            result[target.id] = previous_counts.get(target.id, 0) + 1
    return result


def compute_last_seen_at(
    fixed_targets: list[FixedTarget],
    current_entries: list[SnapshotEntry],
    previous_state: SnapshotState | None,
    *,
    collected_at: str,
) -> dict[str, str]:
    previous_last_seen = dict(previous_state.lastSeenAt) if previous_state else {}
    current_seen = {
        (entry.scope, normalize_path(entry.path, entry.scope)): entry.collectedAt
        for entry in current_entries
        if entry.sourceRootId is not None
    }
    result: dict[str, str] = {}
    for target in fixed_targets:
        scope = resolve_scope(target.path, target.scopeHint)
        key = (scope, normalize_path(target.path, scope))
        if key in current_seen:
            result[target.id] = current_seen[key]
        elif target.id in previous_last_seen:
            result[target.id] = previous_last_seen[target.id]
        else:
            result[target.id] = collected_at
    return result


def _group_candidate_suggestions(
    suggestions: list[PendingSuggestion],
    learning_config: LearningConfig,
) -> list[PendingSuggestion]:
    if not suggestions:
        return []
    group_by = learning_config.groupingPolicy.groupBy
    if not group_by:
        return suggestions

    grouped: dict[tuple[str, ...], PendingSuggestion] = {}
    for suggestion in suggestions:
        key = _grouping_key(suggestion, group_by)
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = suggestion
            continue
        existing_size = existing.sizeBytes or 0
        current_size = suggestion.sizeBytes or 0
        if current_size > existing_size or (current_size == existing_size and suggestion.path < existing.path):
            grouped[key] = suggestion
    if len(grouped) == len(suggestions):
        return list(grouped.values())

    grouped_counts: dict[tuple[str, ...], int] = {}
    for suggestion in suggestions:
        key = _grouping_key(suggestion, group_by)
        grouped_counts[key] = grouped_counts.get(key, 0) + 1

    result: list[PendingSuggestion] = []
    for key, suggestion in grouped.items():
        count = grouped_counts.get(key, 1)
        if count > 1:
            result.append(
                suggestion.model_copy(
                    update={
                        "reason": f"{suggestion.reason}; grouped {count} similar candidate(s) by {','.join(group_by)}"
                    }
                )
            )
        else:
            result.append(suggestion)
    return result


def _grouping_key(suggestion: PendingSuggestion, group_by: list[str]) -> tuple[str, ...]:
    values: list[str] = []
    for field in group_by:
        if field == "scope":
            values.append(suggestion.scope)
        elif field == "category":
            values.append(suggestion.category or "")
        elif field == "root":
            values.append(suggestion.derivedFrom or "")
    return tuple(values)


def _stale_age_satisfied(
    *,
    target: FixedTarget,
    previous_state: SnapshotState | None,
    learning_config: LearningConfig,
    created_at: str,
) -> bool:
    required_days = learning_config.stalePolicy.lastSeenAgeDays
    if required_days is None:
        return True
    if previous_state is None:
        return False
    last_seen_at = previous_state.lastSeenAt.get(target.id)
    if not last_seen_at:
        return False
    return _days_between(last_seen_at, created_at) >= required_days


def _days_between(start: str, end: str) -> int:
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    return max(0, (end_dt - start_dt).days)


def _suggestion_id(action: str, path: str, scope: str) -> str:
    digest = hashlib.sha1(f"{action}:{scope}:{path}".encode("utf-8")).hexdigest()
    return digest[:12]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
