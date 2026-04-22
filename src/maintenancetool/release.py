from __future__ import annotations

from maintenancetool import __version__
from maintenancetool.branding import PRODUCT_NAME

APP_NAME = PRODUCT_NAME
APP_PUBLISHER = "Hotaru-suki"
APP_REPOSITORY = "Hotaru-suki/Maintenance-Tool"
APP_REPOSITORY_URL = f"https://github.com/{APP_REPOSITORY}"
APP_RELEASES_URL = f"{APP_REPOSITORY_URL}/releases"
APP_RELEASES_LATEST_URL = f"{APP_RELEASES_URL}/latest"
APP_RELEASES_API_LATEST_URL = f"https://api.github.com/repos/{APP_REPOSITORY}/releases/latest"
APP_ISSUES_URL = f"{APP_REPOSITORY_URL}/issues"
APP_ISSUE_NEW_URL = f"{APP_REPOSITORY_URL}/issues/new"
APP_SUPPORT_EMAIL = "siestakawaiis@gmail.com"
APP_WINGET_ID = "HotaruSuki.MyTool"
APP_LICENSE = "Other"


def current_version() -> str:
    return __version__


def version_tag(*, version: str | None = None) -> str:
    resolved_version = version or current_version()
    return f"v{resolved_version}"


def release_archive_name(*, version: str | None = None, platform_tag: str = "win-x64") -> str:
    resolved_version = version or current_version()
    return f"{APP_NAME}-{version_tag(version=resolved_version)}-{platform_tag}.zip"


def installer_name(*, version: str | None = None, platform_tag: str = "win-x64") -> str:
    resolved_version = version or current_version()
    return f"{APP_NAME}-{version_tag(version=resolved_version)}-{platform_tag}-setup.exe"


def winget_manifest_name(*, version: str | None = None, platform_tag: str = "win-x64") -> str:
    resolved_version = version or current_version()
    return f"{APP_NAME}-{version_tag(version=resolved_version)}-{platform_tag}-winget.yaml"


def release_download_url(filename: str, *, version: str | None = None) -> str:
    return f"{APP_RELEASES_URL}/download/{version_tag(version=version)}/{filename}"
