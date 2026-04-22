from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from maintenancetool.core.discovery_roots import resolve_discover_roots
from maintenancetool.core.hit_rules import match_discovery_candidate
from maintenancetool.core.path_adapter import (
    LocalPathResolver,
    logical_path_from_local,
    resolve_local_path,
)
from maintenancetool.core.scope import normalize_path, resolve_scope
from maintenancetool.core.safety import evaluate_fixed_target, evaluate_target
from maintenancetool.models.schemas import (
    DenyRule,
    DiscoverConfig,
    SafetyPolicy,
    SnapshotEntry,
    SnapshotState,
)


def load_snapshot_state(path: Path) -> SnapshotState | None:
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return None
    if raw == "[]":
        return None
    return SnapshotState.model_validate_json(raw)


def write_snapshot_state(path: Path, state: SnapshotState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def collect_snapshot_entries(
    *,
    fixed_targets: list[FixedTarget],
    deny_rules: list[DenyRule],
    discover_config: DiscoverConfig,
    safety_policy: SafetyPolicy | None = None,
    local_path_resolver: LocalPathResolver = resolve_local_path,
    collected_at: str | None = None,
) -> list[SnapshotEntry]:
    timestamp = collected_at or _utc_now()
    entries: list[SnapshotEntry] = []
    covered: set[tuple[str, str]] = set()

    for target in fixed_targets:
        if not target.enabled or target.retired:
            continue
        decision = evaluate_fixed_target(
            target,
            deny_rules,
            local_path_resolver=local_path_resolver,
            safety_policy=safety_policy,
        )
        if not decision.allow_scan:
            continue
        scope = resolve_scope(target.path, target.scopeHint)
        normalized_path = normalize_path(target.path, scope)
        local_path = local_path_resolver(normalized_path, scope=scope)
        if not local_path.exists():
            continue

        entry_type = "file" if local_path.is_file() else "directory"
        size_bytes = _measure_path(local_path, max_depth=target.depth)
        entries.append(
            SnapshotEntry(
                path=normalized_path,
                scope=scope,
                sizeBytes=size_bytes,
                entryType=entry_type,
                collectedAt=timestamp,
                category=target.category,
                depth=target.depth,
                sourceRootId=target.id,
            )
        )
        covered.add((scope, normalized_path))

    discover_roots = resolve_discover_roots(fixed_targets, discover_config)
    discover_entries = _collect_discover_entries(
        roots=discover_roots,
        deny_rules=deny_rules,
        discover_config=discover_config,
        covered=covered,
        safety_policy=safety_policy,
        local_path_resolver=local_path_resolver,
        collected_at=timestamp,
    )
    entries.extend(discover_entries)
    return sorted(entries, key=lambda item: (item.scope, -item.sizeBytes, item.path))


def _collect_discover_entries(
    *,
    roots: list[tuple[str, str]],
    deny_rules: list[DenyRule],
    discover_config: DiscoverConfig,
    covered: set[tuple[str, str]],
    safety_policy: SafetyPolicy | None,
    local_path_resolver: LocalPathResolver,
    collected_at: str,
) -> list[SnapshotEntry]:
    results: list[SnapshotEntry] = []

    for scope, root in roots:
        root_path = local_path_resolver(root, scope=scope)
        if not root_path.exists() or not root_path.is_dir():
            continue
        top_n = _resolve_top_n(discover_config, scope, root)
        max_depth = _resolve_max_depth(discover_config, scope, root)
        min_bytes = _resolve_min_bytes(discover_config, scope, root)

        candidates: list[SnapshotEntry] = []
        for candidate in _iter_candidate_directories(root_path, max_depth=max_depth):
            candidate_path = logical_path_from_local(
                root_logical=root,
                root_local=root_path,
                candidate_local=candidate,
                scope=scope,
            )
            key = (scope, candidate_path)
            if key in covered:
                continue
            decision = evaluate_target(
                candidate_path,
                deny_rules=deny_rules,
                scope_hint=scope,
                local_path_resolver=local_path_resolver,
                safety_policy=safety_policy,
            )
            if not decision.allow_promote:
                continue
            hit = match_discovery_candidate(
                logical_path=candidate_path,
                root_category=_override_category(discover_config, scope, root),
            )
            if not hit.matched:
                continue
            size_bytes = _measure_path(candidate, max_depth=max_depth)
            if size_bytes < min_bytes:
                continue
            candidates.append(
                SnapshotEntry(
                    path=candidate_path,
                    scope=scope,
                    sizeBytes=size_bytes,
                    entryType="directory",
                    collectedAt=collected_at,
                    category=hit.category,
                    hitRule=hit.rule_id,
                    hitRuleReason=hit.reason,
                    depth=_depth_from_root(root_path, candidate),
                    sourceRootId=root,
                )
            )

        candidates.sort(key=lambda item: (-item.sizeBytes, item.path))
        results.extend(candidates[:top_n])

    return results
def _iter_candidate_directories(root: Path, max_depth: int) -> list[Path]:
    results: list[Path] = []
    queue: list[tuple[Path, int]] = [(root, 0)]
    while queue:
        current, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        try:
            children = sorted(current.iterdir(), key=lambda item: item.name)
        except OSError:
            continue
        for child in children:
            try:
                if child.is_symlink() or not child.is_dir():
                    continue
            except OSError:
                continue
            results.append(child)
            queue.append((child, depth + 1))
    return results


def _measure_path(path: Path, max_depth: int) -> int:
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0

    total = 0
    queue: list[tuple[Path, int]] = [(path, 0)]
    while queue:
        current, depth = queue.pop(0)
        if depth > max_depth:
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
                elif child.is_dir() and depth < max_depth:
                    queue.append((child, depth + 1))
            except OSError:
                continue
    return total


def _depth_from_root(root: Path, candidate: Path) -> int:
    try:
        return len(candidate.relative_to(root).parts)
    except ValueError:
        return 0


def _resolve_scope_policy(discover_config: DiscoverConfig, scope: str):
    return discover_config.scopePolicies.get(scope, discover_config.scopePolicies.get(scope.upper()))


def _resolve_top_n(discover_config: DiscoverConfig, scope: str, root: str) -> int:
    override = _matching_override(discover_config, scope, root)
    if override and override.topN is not None:
        return override.topN
    policy = _resolve_scope_policy(discover_config, scope)
    if policy and policy.topN is not None:
        return policy.topN
    return discover_config.topN


def _resolve_max_depth(discover_config: DiscoverConfig, scope: str, root: str) -> int:
    override = _matching_override(discover_config, scope, root)
    if override and override.maxDepth is not None:
        return override.maxDepth
    policy = _resolve_scope_policy(discover_config, scope)
    if policy and policy.maxDepth is not None:
        return policy.maxDepth
    return discover_config.maxDepth


def _resolve_min_bytes(discover_config: DiscoverConfig, scope: str, root: str) -> int:
    override = _matching_override(discover_config, scope, root)
    if override and override.minBytes is not None:
        return override.minBytes
    policy = _resolve_scope_policy(discover_config, scope)
    if policy and policy.minBytes is not None:
        return policy.minBytes
    return discover_config.minBytes


def _override_category(discover_config: DiscoverConfig, scope: str, root: str) -> str | None:
    override = _matching_override(discover_config, scope, root)
    return override.category if override else None


def _matching_override(discover_config: DiscoverConfig, scope: str, root: str):
    normalized_root = normalize_path(root, scope)
    for override in discover_config.pathOverrides:
        override_scope = resolve_scope(override.path, override.scopeHint)
        if override_scope != scope:
            continue
        if normalize_path(override.path, scope) == normalized_root:
            return override
    return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
