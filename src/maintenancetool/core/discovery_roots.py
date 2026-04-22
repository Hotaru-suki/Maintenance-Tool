from __future__ import annotations

import ctypes
import os

from maintenancetool.core.config_expansion import expand_config_path
from maintenancetool.core.scope import normalize_path, path_parent, resolve_scope
from maintenancetool.models.schemas import DiscoverConfig, FixedTarget


_WINDOWS_DEFAULT_ROOTS: tuple[tuple[str, str | None], ...] = (
    ("%LOCALAPPDATA%\\Temp", "temp"),
    ("%LOCALAPPDATA%\\Microsoft\\Windows\\INetCache", "browser-cache"),
    ("%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Cache", "browser-cache"),
    ("%LOCALAPPDATA%\\Microsoft\\Edge\\User Data\\Default\\Cache", "browser-cache"),
    ("%APPDATA%\\Code\\logs", "logs"),
)

_WINDOWS_DEFAULT_EXCLUDED_NAMES: tuple[str, ...] = (
    "$Recycle.Bin",
    "Program Files",
    "Program Files (x86)",
    "ProgramData",
    "System Volume Information",
    "Windows",
)


def resolve_discover_roots(
    fixed_targets: list[FixedTarget],
    discover_config: DiscoverConfig,
) -> list[tuple[str, str]]:
    roots: set[tuple[str, str]] = set()
    for target in fixed_targets:
        if not target.enabled or target.retired:
            continue
        scope = resolve_scope(target.path, target.scopeHint)
        parent = path_parent(target.path, scope)
        if parent:
            roots.add((scope, parent))

    for override in discover_config.pathOverrides:
        scope = resolve_scope(override.path, override.scopeHint)
        roots.add((scope, normalize_path(override.path, scope)))

    if roots:
        return sorted(roots)
    return default_discover_roots()


def default_discover_roots() -> list[tuple[str, str]]:
    drive_roots = _list_windows_fixed_drive_roots()
    if drive_roots:
        return [("windows", normalize_path(root, "windows")) for root in drive_roots]

    roots: list[tuple[str, str]] = []
    for path_template, _category in _WINDOWS_DEFAULT_ROOTS:
        expanded = expand_config_path(path_template)
        if "%" in expanded:
            continue
        scope = resolve_scope(expanded, "windows")
        roots.append((scope, normalize_path(expanded, scope)))
    return roots


def default_discovery_excluded_names(scope: str) -> list[str]:
    if scope == "windows":
        return list(_WINDOWS_DEFAULT_EXCLUDED_NAMES)
    return []


def has_default_discover_environment() -> bool:
    return bool(os.getenv("LOCALAPPDATA") or os.getenv("APPDATA"))


def discover_root_summary(
    fixed_targets: list[FixedTarget],
    discover_config: DiscoverConfig,
) -> dict[str, object]:
    explicit_override_count = len(discover_config.pathOverrides)
    fallback_roots = default_discover_roots() if explicit_override_count == 0 and not fixed_targets else []
    resolved_roots = resolve_discover_roots(fixed_targets, discover_config)
    source = "explicit"
    if explicit_override_count == 0 and not fixed_targets:
        source = "system-drive-fallback"
    elif explicit_override_count == 0 and fixed_targets:
        source = "target-parent"
    return {
        "discover_root_source": source,
        "discover_root_count": len(resolved_roots),
        "explicit_override_count": explicit_override_count,
        "default_fallback_root_count": len(fallback_roots),
        "default_environment_ready": has_default_discover_environment(),
    }


def _list_windows_fixed_drive_roots() -> list[str]:
    if os.name != "nt":
        return []
    try:
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    except Exception:
        return []

    drive_roots: list[str] = []
    for index in range(26):
        if not (bitmask & (1 << index)):
            continue
        drive = f"{chr(ord('A') + index)}:\\"
        try:
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
        except Exception:
            continue
        if drive_type == 3:
            drive_roots.append(drive)
    return drive_roots
