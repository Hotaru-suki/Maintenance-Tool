from __future__ import annotations

from dataclasses import dataclass
from pathlib import PureWindowsPath


@dataclass(frozen=True, slots=True)
class DiscoveryHit:
    matched: bool
    category: str | None = None
    rule_id: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class NameRule:
    rule_id: str
    category: str
    token: str
    reason: str


@dataclass(frozen=True, slots=True)
class PathFragmentRule:
    rule_id: str
    category: str
    fragment: str
    reason: str


NAME_RULES: tuple[NameRule, ...] = (
    NameRule("name-browser-code-cache", "browser-cache", "code cache", "matched browser cache directory name"),
    NameRule("name-browser-gpucache", "browser-cache", "gpucache", "matched browser cache directory name"),
    NameRule("name-browser-cache", "browser-cache", "cache", "matched cache directory name"),
    NameRule("name-generic-dot-cache", "cache", ".cache", "matched cache directory name"),
    NameRule("name-logs-logs", "logs", "logs", "matched logs directory name"),
    NameRule("name-logs-log", "logs", "log", "matched logs directory name"),
    NameRule("name-logs-crashpad", "logs", "crashpad", "matched crash/report directory name"),
    NameRule("name-temp-temp", "temp", "temp", "matched temp directory name"),
    NameRule("name-temp-tmp", "temp", "tmp", "matched temp directory name"),
)

PATH_FRAGMENT_RULES: tuple[PathFragmentRule, ...] = (
    PathFragmentRule("path-browser-inetcache", "browser-cache", "\\microsoft\\windows\\inetcache\\", "matched browser cache path"),
    PathFragmentRule("path-browser-chrome-user-data", "browser-cache", "\\google\\chrome\\user data\\", "matched browser cache path"),
    PathFragmentRule("path-browser-edge-user-data", "browser-cache", "\\microsoft\\edge\\user data\\", "matched browser cache path"),
    PathFragmentRule("path-logs-code-logs", "logs", "\\code\\logs\\", "matched IDE logs path"),
    PathFragmentRule("path-temp-local-temp", "temp", "\\appdata\\local\\temp\\", "matched temp root path"),
)


def match_discovery_candidate(
    *,
    logical_path: str,
    root_category: str | None,
) -> DiscoveryHit:
    normalized_path = str(PureWindowsPath(logical_path)).lower().replace("/", "\\")
    leaf_name = PureWindowsPath(logical_path).name.lower()

    for rule in NAME_RULES:
        if leaf_name == rule.token or rule.token in leaf_name:
            return DiscoveryHit(
                matched=True,
                category=rule.category,
                rule_id=rule.rule_id,
                reason=rule.reason,
            )

    for rule in PATH_FRAGMENT_RULES:
        if rule.fragment in normalized_path:
            return DiscoveryHit(
                matched=True,
                category=rule.category,
                rule_id=rule.rule_id,
                reason=rule.reason,
            )

    if root_category:
        return DiscoveryHit(
            matched=True,
            category=root_category,
            rule_id="root-category-fallback",
            reason=f"matched discover root category: {root_category}",
        )

    return DiscoveryHit(matched=False)


def hit_rule_summary() -> dict[str, int]:
    return {
        "hit_rules_name": len(NAME_RULES),
        "hit_rules_path_fragment": len(PATH_FRAGMENT_RULES),
        "hit_rules_total": len(NAME_RULES) + len(PATH_FRAGMENT_RULES),
    }
