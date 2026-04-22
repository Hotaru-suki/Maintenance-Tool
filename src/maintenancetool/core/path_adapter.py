from __future__ import annotations

import os
import platform
import stat
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable

from maintenancetool.core.scope import normalize_path


LocalPathResolver = Callable[[str, str], Path]


def resolve_local_path(
    path: str,
    *,
    scope: str,
) -> Path:
    if scope == "wsl":
        return Path(normalize_path(path, scope))

    pure = PureWindowsPath(path)
    if not _should_translate_windows_path():
        return Path(str(pure))

    translated = _translate_windows_path_to_wsl(path)
    if translated is None:
        return Path(str(pure))
    return Path(translated)


def logical_path_from_local(
    *,
    root_logical: str,
    root_local: Path,
    candidate_local: Path,
    scope: str,
) -> str:
    if scope == "wsl":
        return normalize_path(str(candidate_local), scope)

    relative = candidate_local.relative_to(root_local)
    logical_root = PureWindowsPath(root_logical)
    return normalize_path(str(logical_root.joinpath(*relative.parts)), scope)


def is_linklike_path(path: Path, *, scope: str) -> bool:
    try:
        if path.is_symlink():
            return True
    except OSError:
        return False

    if scope != "windows":
        return False

    try:
        stat_result = os.lstat(path)
    except OSError:
        return False

    file_attributes = getattr(stat_result, "st_file_attributes", 0)
    file_attribute_reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(file_attributes & file_attribute_reparse_point)


def _should_translate_windows_path() -> bool:
    return os.name != "nt" and _is_wsl_environment()


def _translate_windows_path_to_wsl(path: str) -> str | None:
    pure = PureWindowsPath(path)
    drive = pure.drive.rstrip(":").lower()
    tail_parts = [part for part in pure.parts[1:] if part not in ("\\", "/")]
    if not drive:
        return None
    return str(PurePosixPath("/mnt", drive, *tail_parts))


def _is_wsl_environment() -> bool:
    if os.getenv("WSL_DISTRO_NAME"):
        return True
    try:
        release = platform.release().lower()
    except OSError:
        return False
    return "microsoft" in release or "wsl" in release
