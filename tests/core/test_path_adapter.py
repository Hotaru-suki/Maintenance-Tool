from pathlib import Path
from pathlib import PureWindowsPath

from maintenancetool.core import path_adapter


def test_resolve_local_path_maps_windows_path_to_mnt_in_wsl(monkeypatch) -> None:
    monkeypatch.setattr(path_adapter, "_should_translate_windows_path", lambda: True)

    resolved = path_adapter.resolve_local_path("C:\\Users\\Alice\\Cache", scope="windows")

    assert str(resolved).replace("\\", "/") == "/mnt/c/Users/Alice/Cache"


def test_resolve_local_path_keeps_windows_path_on_native_windows(monkeypatch) -> None:
    monkeypatch.setattr(path_adapter.os, "name", "nt")
    monkeypatch.setattr(path_adapter, "_is_wsl_environment", lambda: False)

    resolved = path_adapter.resolve_local_path("C:\\Users\\Alice\\Cache", scope="windows")

    assert str(resolved) == str(PureWindowsPath("C:\\Users\\Alice\\Cache"))


def test_resolve_local_path_keeps_windows_path_on_non_wsl_posix(monkeypatch) -> None:
    monkeypatch.setattr(path_adapter.os, "name", "posix")
    monkeypatch.setattr(path_adapter, "_is_wsl_environment", lambda: False)

    resolved = path_adapter.resolve_local_path("C:\\Users\\Alice\\Cache", scope="windows")

    assert str(resolved) == "C:\\Users\\Alice\\Cache"
