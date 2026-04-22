from __future__ import annotations

import json
from pathlib import Path

from maintenancetool.services.update import UpdateStatus, get_update_status, open_update_download


def test_get_update_status_writes_live_cache(monkeypatch, tmp_path: Path) -> None:
    expected = UpdateStatus(
        current_version="0.1.0",
        latest_version="0.2.0",
        checked_at="2026-04-22T12:00:00Z",
        release_url="https://example.invalid/releases/latest",
        installer_url="https://example.invalid/MaintenanceTool-v0.2.0-win-x64-setup.exe",
        update_available=True,
        source="live",
        error=None,
    )
    monkeypatch.setattr(
        "maintenancetool.services.update._fetch_latest_release",
        lambda **_: expected,
    )

    result = get_update_status(tmp_path, force_refresh=True)

    assert result == expected
    cache_payload = json.loads((tmp_path / "update-state.json").read_text(encoding="utf-8"))
    assert cache_payload["latest_version"] == "0.2.0"
    assert cache_payload["update_available"] is True


def test_get_update_status_falls_back_to_cache(monkeypatch, tmp_path: Path) -> None:
    cache_path = tmp_path / "update-state.json"
    cache_path.write_text(
        json.dumps(
            {
                "current_version": "0.1.0",
                "latest_version": "0.1.1",
                "checked_at": "2026-04-22T12:00:00Z",
                "release_url": "https://example.invalid/releases/latest",
                "installer_url": None,
                "update_available": True,
                "source": "live",
                "error": None,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "maintenancetool.services.update._fetch_latest_release",
        lambda **_: None,
    )

    result = get_update_status(tmp_path, force_refresh=True)

    assert result.source == "cache"
    assert result.latest_version == "0.1.1"
    assert result.update_available is True


def test_open_update_download_prefers_installer(monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(
        "maintenancetool.services.update.webbrowser.open",
        lambda url: opened.append(url) or True,
    )
    status = UpdateStatus(
        current_version="0.1.0",
        latest_version="0.1.1",
        checked_at="2026-04-22T12:00:00Z",
        release_url="https://example.invalid/releases/latest",
        installer_url="https://example.invalid/MaintenanceTool-v0.1.1-win-x64-setup.exe",
        update_available=True,
        source="live",
        error=None,
    )

    assert open_update_download(status) is True
    assert opened == ["https://example.invalid/MaintenanceTool-v0.1.1-win-x64-setup.exe"]
