from __future__ import annotations

import os
import re
from pathlib import PurePosixPath, PureWindowsPath

from maintenancetool.models.schemas import ScopeHint, ScopeName


WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
WINDOWS_ROOT_RE = re.compile(r"^[A-Za-z]:[\\/]?$")


def resolve_scope(path: str, scope_hint: ScopeHint = "auto") -> ScopeName:
    if scope_hint != "auto":
        return scope_hint
    if WINDOWS_DRIVE_RE.match(path):
        return "windows"
    return "wsl"


def normalize_path(path: str, scope: ScopeName) -> str:
    if scope == "windows":
        normalized = str(PureWindowsPath(path)).replace("/", "\\")
        if WINDOWS_DRIVE_RE.match(normalized):
            normalized = normalized[0].upper() + normalized[1:]
        return normalized.rstrip("\\") or normalized
    normalized = os.path.normpath(str(PurePosixPath(path)))
    return normalized if normalized != "." else path


def path_parent(path: str, scope: ScopeName) -> str | None:
    normalized = normalize_path(path, scope)
    pure = PureWindowsPath(normalized) if scope == "windows" else PurePosixPath(normalized)
    parent = str(pure.parent)
    if parent == normalized:
        return None
    return normalize_path(parent, scope)


def is_root_path(path: str, scope: ScopeName) -> bool:
    normalized = normalize_path(path, scope)
    if scope == "windows":
        return bool(WINDOWS_ROOT_RE.match(normalized))
    return normalized == "/"


def is_subpath_or_same(path: str, root: str, scope: ScopeName) -> bool:
    left = normalize_path(path, scope)
    right = normalize_path(root, scope)
    left_parts = _parts(left, scope)
    right_parts = _parts(right, scope)
    return len(left_parts) >= len(right_parts) and left_parts[: len(right_parts)] == right_parts


def _parts(path: str, scope: ScopeName) -> tuple[str, ...]:
    pure = PureWindowsPath(path) if scope == "windows" else PurePosixPath(path)
    parts = pure.parts
    if scope == "windows":
        return tuple(part.lower() for part in parts)
    return parts

