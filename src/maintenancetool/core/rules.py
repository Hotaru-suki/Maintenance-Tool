from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from maintenancetool.core.scope import normalize_path, resolve_scope
from maintenancetool.models.schemas import DenyRule, FixedTarget, PendingSuggestion


def write_fixed_targets(path: Path, targets: list[FixedTarget]) -> None:
    write_target_list(path, targets)


def write_target_list(path: Path, targets: list[FixedTarget]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [target.model_dump(mode="json", exclude_none=True) for target in targets]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_deny_rules(path: Path, deny_rules: list[DenyRule]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [rule.model_dump(mode="json", exclude_none=True) for rule in deny_rules]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def apply_pending_review(
    *,
    fixed_targets: list[FixedTarget],
    review_targets: list[FixedTarget],
    deny_rules: list[DenyRule],
    suggestions: list[PendingSuggestion],
    accept_ids: set[str],
    reject_ids: set[str] | None = None,
) -> tuple[list[FixedTarget], list[FixedTarget], list[DenyRule], list[PendingSuggestion], list[PendingSuggestion], list[PendingSuggestion]]:
    targets = list(fixed_targets)
    review_list = list(review_targets)
    deny_list = list(deny_rules)
    accepted: list[PendingSuggestion] = []
    rejected: list[PendingSuggestion] = []
    explicit_rejects = reject_ids or set()

    target_index = {target.id: idx for idx, target in enumerate(targets) if target.id}
    target_paths = {
        (
            resolve_scope(target.path, target.scopeHint),
            normalize_path(target.path, resolve_scope(target.path, target.scopeHint)),
        )
        for target in targets
    }
    review_target_paths = {
        (
            resolve_scope(target.path, target.scopeHint),
            normalize_path(target.path, resolve_scope(target.path, target.scopeHint)),
        )
        for target in review_list
    }
    deny_paths = {
        (
            resolve_scope(rule.path, rule.scopeHint),
            normalize_path(rule.path, resolve_scope(rule.path, rule.scopeHint)),
        )
        for rule in deny_list
    }

    for suggestion in suggestions:
        if suggestion.id in explicit_rejects:
            rejected.append(suggestion)
            continue
        if suggestion.id not in accept_ids:
            continue

        if suggestion.suggestedAction == "addFixedTarget":
            key = (suggestion.scope, normalize_path(suggestion.path, suggestion.scope))
            if key not in target_paths:
                new_target = FixedTarget(
                    id=_target_id(suggestion.path, suggestion.scope),
                    path=suggestion.path,
                    scopeHint=suggestion.scope,
                    enabled=True,
                    depth=2,
                    deleteMode="contents",
                    source="learned",
                    category=suggestion.category,
                    note=f"promoted from pending suggestion {suggestion.id}",
                    createdAt=_utc_now(),
                    updatedAt=_utc_now(),
                )
                targets.append(new_target)
                target_paths.add(key)
            accepted.append(suggestion)
            continue

        if suggestion.suggestedAction == "addReviewTarget":
            key = (suggestion.scope, normalize_path(suggestion.path, suggestion.scope))
            if key not in review_target_paths:
                review_list.append(
                    FixedTarget(
                        id=_target_id(suggestion.path, suggestion.scope),
                        path=suggestion.path,
                        scopeHint=suggestion.scope,
                        enabled=True,
                        depth=2,
                        deleteMode="contents",
                        source="learned",
                        category=suggestion.category,
                        note=f"promoted to review list from pending suggestion {suggestion.id}",
                        createdAt=_utc_now(),
                        updatedAt=_utc_now(),
                    )
                )
                review_target_paths.add(key)
            accepted.append(suggestion)
            continue

        if suggestion.suggestedAction == "addDenyRule":
            _append_deny_rule(
                deny_list=deny_list,
                deny_paths=deny_paths,
                suggestion=suggestion,
                reason=suggestion.reason,
            )
            accepted.append(suggestion)
            continue

        if suggestion.suggestedAction == "retireFixedTarget" and suggestion.derivedFrom in target_index:
            idx = target_index[suggestion.derivedFrom]
            targets[idx] = targets[idx].model_copy(
                update={"retired": True, "updatedAt": _utc_now()}
            )
            accepted.append(suggestion)
            continue

        rejected.append(suggestion)

    remaining = [suggestion for suggestion in suggestions if suggestion not in accepted and suggestion not in rejected]
    return targets, review_list, deny_list, remaining, accepted, rejected


def promote_review_targets_to_fixed(
    *,
    fixed_targets: list[FixedTarget],
    review_targets: list[FixedTarget],
    promote_ids: set[str],
    promote_all: bool = False,
) -> tuple[list[FixedTarget], list[FixedTarget], list[FixedTarget]]:
    targets = list(fixed_targets)
    review_list: list[FixedTarget] = []
    promoted: list[FixedTarget] = []
    target_paths = {
        (
            resolve_scope(target.path, target.scopeHint),
            normalize_path(target.path, resolve_scope(target.path, target.scopeHint)),
        )
        for target in targets
    }

    for target in review_targets:
        should_promote = promote_all or bool(target.id and target.id in promote_ids)
        if not should_promote:
            review_list.append(target)
            continue

        key = (
            resolve_scope(target.path, target.scopeHint),
            normalize_path(target.path, resolve_scope(target.path, target.scopeHint)),
        )
        promoted_target = target.model_copy(
            update={
                "source": "learned",
                "note": _promotion_note(target.note),
                "updatedAt": _utc_now(),
            }
        )
        if key not in target_paths:
            targets.append(promoted_target)
            target_paths.add(key)
        promoted.append(promoted_target)

    return targets, review_list, promoted


def _append_deny_rule(
    *,
    deny_list: list[DenyRule],
    deny_paths: set[tuple[str, str]],
    suggestion: PendingSuggestion,
    reason: str,
) -> None:
    key = (suggestion.scope, normalize_path(suggestion.path, suggestion.scope))
    if key in deny_paths:
        return
    deny_list.append(
        DenyRule(
            id=_deny_id(suggestion.path, suggestion.scope),
            path=suggestion.path,
            scopeHint=suggestion.scope,
            enabled=True,
            reason=reason,
            source="user",
            createdAt=_utc_now(),
            updatedAt=_utc_now(),
        )
    )
    deny_paths.add(key)


def _promotion_note(existing_note: str | None) -> str:
    suffix = "promoted from review list after user approval"
    if not existing_note:
        return suffix
    if suffix in existing_note:
        return existing_note
    return f"{existing_note}; {suffix}"


def _target_id(path: str, scope: str) -> str:
    digest = hashlib.sha1(f"{scope}:{path}".encode("utf-8")).hexdigest()
    return f"learned-{digest[:12]}"


def _deny_id(path: str, scope: str) -> str:
    digest = hashlib.sha1(f"deny:{scope}:{path}".encode("utf-8")).hexdigest()
    return f"deny-{digest[:12]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
