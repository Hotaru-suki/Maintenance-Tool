from __future__ import annotations

import json
import urllib.error
import urllib.request
import webbrowser
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from maintenancetool.branding import PRODUCT_NAME
from maintenancetool.release import (
    APP_RELEASES_API_LATEST_URL,
    APP_RELEASES_LATEST_URL,
    current_version,
    installer_name,
)

UPDATE_CACHE_FILENAME = "update-state.json"
UPDATE_CHECK_TTL = timedelta(hours=24)
UTC = timezone.utc


@dataclass(frozen=True, slots=True)
class UpdateStatus:
    current_version: str
    latest_version: str | None
    checked_at: str | None
    release_url: str
    installer_url: str | None
    update_available: bool
    source: str
    error: str | None = None


def get_update_status(
    state_dir: Path,
    *,
    force_refresh: bool = False,
    refresh_if_stale: bool = False,
    timeout_seconds: float = 2.0,
) -> UpdateStatus:
    cache_path = state_dir / UPDATE_CACHE_FILENAME
    cached = _load_cached_status(cache_path)
    if not force_refresh:
        if cached is not None and not refresh_if_stale:
            return cached
        if cached is not None and refresh_if_stale and not _is_stale(cached):
            return cached

    fetched = _fetch_latest_release(timeout_seconds=timeout_seconds)
    if fetched is not None:
        state_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(asdict(fetched), indent=2), encoding="utf-8")
        return fetched

    if cached is not None:
        return UpdateStatus(
            current_version=cached.current_version,
            latest_version=cached.latest_version,
            checked_at=cached.checked_at,
            release_url=cached.release_url,
            installer_url=cached.installer_url,
            update_available=cached.update_available,
            source="cache",
            error=cached.error,
        )

    return UpdateStatus(
        current_version=current_version(),
        latest_version=None,
        checked_at=None,
        release_url=APP_RELEASES_LATEST_URL,
        installer_url=None,
        update_available=False,
        source="unavailable",
        error="Unable to contact the release service.",
    )


def open_update_download(status: UpdateStatus) -> bool:
    target = status.installer_url or status.release_url
    try:
        return bool(webbrowser.open(target))
    except Exception:
        return False


def _load_cached_status(cache_path: Path) -> UpdateStatus | None:
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    try:
        return UpdateStatus(
            current_version=str(payload["current_version"]),
            latest_version=str(payload["latest_version"]) if payload.get("latest_version") else None,
            checked_at=str(payload["checked_at"]) if payload.get("checked_at") else None,
            release_url=str(payload["release_url"]),
            installer_url=str(payload["installer_url"]) if payload.get("installer_url") else None,
            update_available=bool(payload["update_available"]),
            source=str(payload.get("source", "cache")),
            error=str(payload["error"]) if payload.get("error") else None,
        )
    except KeyError:
        return None


def _is_stale(status: UpdateStatus) -> bool:
    if status.checked_at is None:
        return True
    try:
        checked_at = datetime.fromisoformat(status.checked_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    return datetime.now(UTC) - checked_at > UPDATE_CHECK_TTL


def _fetch_latest_release(*, timeout_seconds: float) -> UpdateStatus | None:
    request = urllib.request.Request(
        APP_RELEASES_API_LATEST_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": PRODUCT_NAME,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return None

    latest_version = str(payload.get("tag_name", "")).lstrip("v") or None
    release_url = str(payload.get("html_url") or APP_RELEASES_LATEST_URL)
    assets = payload.get("assets") or []
    expected_installer_name = installer_name(version=latest_version) if latest_version else None
    installer_url = None
    for asset in assets:
        asset_name = str(asset.get("name") or "")
        if expected_installer_name is not None and asset_name == expected_installer_name:
            installer_url = str(asset.get("browser_download_url") or "") or None
            break
        if asset_name.endswith("-setup.exe"):
            installer_url = str(asset.get("browser_download_url") or "") or None
            break

    current = current_version()
    checked_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return UpdateStatus(
        current_version=current,
        latest_version=latest_version,
        checked_at=checked_at,
        release_url=release_url,
        installer_url=installer_url,
        update_available=_is_newer_version(latest_version, current),
        source="live",
        error=None,
    )


def _is_newer_version(candidate: str | None, current: str) -> bool:
    if not candidate:
        return False
    return _normalize_version(candidate) > _normalize_version(current)


def _normalize_version(version: str) -> tuple[int, ...]:
    base = version.strip().split("-", 1)[0]
    parts = [part for part in base.split(".") if part != ""]
    normalized: list[int] = []
    for part in parts:
        try:
            normalized.append(int(part))
        except ValueError:
            digits = "".join(ch for ch in part if ch.isdigit())
            normalized.append(int(digits or "0"))
    return tuple(normalized)
