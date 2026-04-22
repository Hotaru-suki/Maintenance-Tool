from maintenancetool.core.safety import evaluate_target, iter_effective_deny_rules
from maintenancetool.models.schemas import DenyRule, SafetyPolicy


def test_evaluate_target_rejects_windows_system_directory_without_user_deny_rules() -> None:
    decision = evaluate_target(
        "C:\\Windows\\Temp",
        deny_rules=[],
        scope_hint="windows",
    )

    assert decision.allow_scan is False
    assert decision.allow_delete is False
    assert decision.reason == "matched deny rule: system-root"


def test_iter_effective_deny_rules_merges_user_and_builtin_rules() -> None:
    effective = iter_effective_deny_rules(
        [
            DenyRule(
                id="user-protect",
                path="C:\\Users\\Alice\\Work",
                scopeHint="windows",
                reason="user protected",
            )
        ],
        scope="windows",
    )

    ids = {rule.id for rule in effective}
    assert "user-protect" in ids
    assert "system-root" in ids
    assert "program-files" in ids


def test_evaluate_target_rejects_path_outside_allowed_roots() -> None:
    decision = evaluate_target(
        "C:\\Users\\Alice\\Downloads\\cache",
        deny_rules=[],
        scope_hint="windows",
        safety_policy=SafetyPolicy(
            allowedRoots=[
                {
                    "path": "C:\\Users\\Alice\\AppData\\Local",
                    "scopeHint": "windows",
                    "enabled": True,
                }
            ]
        ),
    )

    assert decision.allow_scan is False
    assert decision.allow_delete is False
    assert decision.reason == "outside configured allowed roots"


def test_evaluate_target_allows_path_within_allowed_roots() -> None:
    decision = evaluate_target(
        "C:\\Users\\Alice\\AppData\\Local\\Temp\\cache",
        deny_rules=[],
        scope_hint="windows",
        safety_policy=SafetyPolicy(
            allowedRoots=[
                {
                    "path": "C:\\Users\\Alice\\AppData\\Local",
                    "scopeHint": "windows",
                    "enabled": True,
                }
            ]
        ),
    )

    assert decision.allow_scan is True
    assert decision.reason == "allowed"
