from __future__ import annotations

from maintenancetool.core.path_adapter import (
    LocalPathResolver,
    is_linklike_path,
    resolve_local_path,
)
from maintenancetool.core.scope import is_root_path, is_subpath_or_same, normalize_path, resolve_scope
from maintenancetool.models.schemas import DenyRule, FixedTarget, SafetyDecision, SafetyPolicy, SafetyRoot


WINDOWS_SYSTEM_PROTECTED_PATHS = (
    ("system-root", "C:\\Windows", "Windows system directory"),
    ("program-files", "C:\\Program Files", "Program Files directory"),
    ("program-files-x86", "C:\\Program Files (x86)", "Program Files x86 directory"),
    ("program-data", "C:\\ProgramData", "ProgramData directory"),
)


def evaluate_target(
    path: str,
    *,
    deny_rules: list[DenyRule],
    scope_hint: str = "auto",
    for_delete: bool = False,
    local_path_resolver: LocalPathResolver = resolve_local_path,
    safety_policy: SafetyPolicy | None = None,
) -> SafetyDecision:
    policy = safety_policy or SafetyPolicy()
    scope = resolve_scope(path, scope_hint)
    normalized = normalize_path(path, scope)

    if is_root_path(normalized, scope):
        return SafetyDecision(
            allow_scan=False,
            allow_promote=False,
            allow_delete=False,
            reason="root boundary is protected",
            risk_level="high",
            requires_manual_confirm=True,
        )

    for rule in iter_effective_deny_rules(deny_rules, scope=scope):
        if not rule.enabled:
            continue
        if is_subpath_or_same(normalized, rule.path, scope):
            return SafetyDecision(
                allow_scan=False,
                allow_promote=False,
                allow_delete=False,
                reason=f"matched deny rule: {rule.id}",
                risk_level="high",
                requires_manual_confirm=True,
            )

    if policy.allowedRoots and not _is_within_allowed_roots(
        normalized,
        scope=scope,
        allowed_roots=policy.allowedRoots,
    ):
        return SafetyDecision(
            allow_scan=False,
            allow_promote=False,
            allow_delete=False,
            reason="outside configured allowed roots",
            risk_level="high",
            requires_manual_confirm=True,
        )

    local_path = local_path_resolver(normalized, scope=scope)
    if policy.refuseSymlinks and local_path.exists() and is_linklike_path(local_path, scope=scope):
        return SafetyDecision(
            allow_scan=False,
            allow_promote=False,
            allow_delete=False,
            reason="symlink/junction/reparse targets are rejected",
            risk_level="high",
            requires_manual_confirm=True,
        )

    return SafetyDecision(
        allow_scan=True,
        allow_promote=True,
        allow_delete=for_delete,
        reason="allowed",
        risk_level="low" if not for_delete else "high",
        requires_manual_confirm=for_delete,
    )


def evaluate_fixed_target(
    target: FixedTarget,
    deny_rules: list[DenyRule],
    local_path_resolver: LocalPathResolver = resolve_local_path,
    safety_policy: SafetyPolicy | None = None,
    for_delete: bool = False,
) -> SafetyDecision:
    decision = evaluate_target(
        target.path,
        deny_rules=deny_rules,
        scope_hint=target.scopeHint,
        for_delete=for_delete,
        local_path_resolver=local_path_resolver,
        safety_policy=safety_policy,
    )
    policy = safety_policy or SafetyPolicy()
    local_path = local_path_resolver(target.path, scope=resolve_scope(target.path, target.scopeHint))
    size_bytes = 0
    try:
        if local_path.exists() and local_path.is_file():
            size_bytes = local_path.stat().st_size
    except OSError:
        size_bytes = 0

    manual_confirm = decision.requires_manual_confirm
    risk_level = decision.risk_level
    reason = decision.reason

    if policy.requireManualConfirmForLearnedTargets and target.source == "learned":
        manual_confirm = True
        risk_level = "high" if for_delete and decision.allow_scan else ("medium" if decision.allow_scan else decision.risk_level)
        reason = "learned target requires manual confirmation"
    if size_bytes >= policy.requireManualConfirmAboveBytes:
        manual_confirm = True
        risk_level = "high" if for_delete and decision.allow_scan else ("medium" if decision.allow_scan else decision.risk_level)
        reason = "target exceeds manual confirmation size threshold"

    return decision.model_copy(
        update={
            "requires_manual_confirm": manual_confirm,
            "risk_level": risk_level,
            "reason": reason,
        }
    )


def iter_effective_deny_rules(deny_rules: list[DenyRule], *, scope: str) -> list[DenyRule]:
    effective: list[DenyRule] = []
    for rule in deny_rules:
        rule_scope = resolve_scope(rule.path, rule.scopeHint)
        if rule_scope == scope:
            effective.append(rule)
    effective.extend(_builtin_system_deny_rules(scope=scope))
    return effective


def _builtin_system_deny_rules(*, scope: str) -> list[DenyRule]:
    if scope != "windows":
        return []
    return [
        DenyRule(
            id=rule_id,
            path=path,
            enabled=True,
            reason=reason,
            scopeHint="windows",
            source="system",
        )
        for rule_id, path, reason in WINDOWS_SYSTEM_PROTECTED_PATHS
    ]


def _is_within_allowed_roots(path: str, *, scope: str, allowed_roots: list[SafetyRoot]) -> bool:
    for root in allowed_roots:
        if not root.enabled:
            continue
        root_scope = resolve_scope(root.path, root.scopeHint)
        if root_scope != scope:
            continue
        if is_subpath_or_same(path, root.path, scope):
            return True
    return False
