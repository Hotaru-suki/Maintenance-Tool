from __future__ import annotations

from pathlib import Path, PureWindowsPath

from maintenancetool.core.path_adapter import LocalPathResolver, resolve_local_path

SANDBOX_SENTINEL = ".maintenance_sandbox_root"


def validate_sandbox_root(path: Path) -> Path:
    root = path.expanduser().resolve()
    sentinel = root / SANDBOX_SENTINEL
    if not root.exists():
        raise ValueError(f"Sandbox root does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"Sandbox root is not a directory: {root}")
    if not sentinel.exists():
        raise ValueError(f"Sandbox sentinel not found: {sentinel}")
    return root


def build_sandbox_path_resolver(sandbox_root: Path) -> LocalPathResolver:
    validated_root = validate_sandbox_root(sandbox_root)

    def resolver(path: str, scope: str) -> Path:
        if scope == "wsl":
            return resolve_local_path(path, scope=scope)

        pure = PureWindowsPath(path)
        sandbox_name = validated_root.name.lower()
        lower_parts = [part.lower() for part in pure.parts]
        if sandbox_name in lower_parts:
            index = lower_parts.index(sandbox_name)
            suffix = pure.parts[index + 1 :]
            return validated_root.joinpath(*suffix)
        return resolve_local_path(path, scope=scope)

    return resolver


__all__ = ["SANDBOX_SENTINEL", "build_sandbox_path_resolver", "validate_sandbox_root"]
