from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from maintenancetool.core.scope import normalize_path, resolve_scope
from maintenancetool.models.schemas import FixedTarget, PendingSuggestion


def write_fixed_targets(path: Path, targets: list[FixedTarget]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [target.model_dump(mode="json", exclude_none=True) for target in targets]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def apply_pending_review(
    *,
    fixed_targets: list[FixedTarget],
    suggestions: list[PendingSuggestion],
    accept_ids: set[str],
    reject_ids: set[str] | None = None,
) -> tuple[list[FixedTarget], list[PendingSuggestion], list[PendingSuggestion], list[PendingSuggestion]]:
    targets = list(fixed_targets)
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

        if suggestion.suggestedAction == "retireFixedTarget" and suggestion.derivedFrom in target_index:
            idx = target_index[suggestion.derivedFrom]
            targets[idx] = targets[idx].model_copy(
                update={"retired": True, "updatedAt": _utc_now()}
            )
            accepted.append(suggestion)
            continue

        rejected.append(suggestion)

    remaining = [suggestion for suggestion in suggestions if suggestion not in accepted and suggestion not in rejected]
    return targets, remaining, accepted, rejected


def _target_id(path: str, scope: str) -> str:
    digest = hashlib.sha1(f"{scope}:{path}".encode("utf-8")).hexdigest()
    return f"learned-{digest[:12]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
