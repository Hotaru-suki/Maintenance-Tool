from pathlib import Path

import pytest

from maintenancetool.core import path_adapter
from maintenancetool.dev.sandbox import build_sandbox_path_resolver, validate_sandbox_root
from tests.helpers.sandbox_factory import SandboxFactory


def test_validate_sandbox_root_requires_sentinel(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="sentinel"):
        validate_sandbox_root(tmp_path)


def test_build_sandbox_path_resolver_maps_windows_sandbox_path(tmp_path: Path) -> None:
    sandbox = SandboxFactory(tmp_path).create()
    resolver = build_sandbox_path_resolver(sandbox.root)
    resolved = resolver(f"C:\\{sandbox.root.name}\\fixtures\\browser\\cache", "windows")
    assert resolved == sandbox.root / "fixtures" / "browser" / "cache"


def test_build_sandbox_path_resolver_falls_back_to_native_windows_path(monkeypatch, tmp_path: Path) -> None:
    sandbox = SandboxFactory(tmp_path).create()
    monkeypatch.setattr(path_adapter.os, "name", "nt")
    monkeypatch.setattr(path_adapter, "_is_wsl_environment", lambda: False)

    resolver = build_sandbox_path_resolver(sandbox.root)
    resolved = resolver("D:\\External\\Cache", "windows")

    assert resolved == Path("D:\\External\\Cache")
