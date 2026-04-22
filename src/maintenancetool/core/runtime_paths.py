from __future__ import annotations

import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from maintenancetool.branding import PRODUCT_NAME

APP_NAME = PRODUCT_NAME
WINDOWS_DATA_DIRNAME = APP_NAME
WORKSPACE_ROOT_CONFIG_FILENAME = "workspace-root.txt"
WINDOWS_PROTECTED_INSTALL_ROOTS = (
    Path("C:/Program Files"),
    Path("C:/Program Files (x86)"),
    Path("C:/Windows"),
)


@dataclass(frozen=True, slots=True)
class RuntimeWorkspace:
    root: Path
    config_dir: Path
    state_dir: Path
    report_dir: Path
    quarantine_dir: Path


def get_runtime_workspace() -> RuntimeWorkspace:
    root = _resolve_workspace_root()
    return RuntimeWorkspace(
        root=root,
        config_dir=root / "config",
        state_dir=root / "state",
        report_dir=root / "reports",
        quarantine_dir=root / ".quarantine",
    )


def bootstrap_runtime_workspace() -> RuntimeWorkspace:
    workspace = _ensure_workspace(get_runtime_workspace())
    _bootstrap_config_templates(workspace.config_dir)
    return workspace


def _ensure_workspace(preferred: RuntimeWorkspace) -> RuntimeWorkspace:
    candidates = [
        preferred.root,
        Path(tempfile.gettempdir()) / APP_NAME,
    ]
    tried: list[Path] = []
    for candidate_root in candidates:
        if candidate_root in tried:
            continue
        tried.append(candidate_root)
        workspace = RuntimeWorkspace(
            root=candidate_root,
            config_dir=candidate_root / "config",
            state_dir=candidate_root / "state",
            report_dir=candidate_root / "reports",
            quarantine_dir=candidate_root / ".quarantine",
        )
        try:
            _create_workspace_dirs(workspace)
            return workspace
        except OSError:
            continue
    raise OSError(f"Unable to create runtime workspace in any candidate root: {tried}")


def _create_workspace_dirs(workspace: RuntimeWorkspace) -> None:
    workspace.root.mkdir(parents=True, exist_ok=True)
    workspace.state_dir.mkdir(parents=True, exist_ok=True)
    workspace.report_dir.mkdir(parents=True, exist_ok=True)
    workspace.quarantine_dir.mkdir(parents=True, exist_ok=True)
    workspace.config_dir.mkdir(parents=True, exist_ok=True)


def get_packaged_template_dir() -> Path | None:
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "config_templates")
    candidates.extend(
        [
            Path(sys.executable).resolve().parent / "config_templates",
            Path(__file__).resolve().parents[3] / "packaging" / "config_templates",
        ]
    )
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def _resolve_workspace_root() -> Path:
    override = os.getenv("MAINTENANCETOOL_WORKSPACE_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        configured_root = _resolve_windows_configured_workspace_root()
        if configured_root is not None:
            return configured_root
        portable_root = _resolve_windows_portable_workspace_root()
        if portable_root is not None:
            return portable_root
        return _resolve_windows_workspace_root()
    xdg_state_home = os.getenv("XDG_STATE_HOME")
    if xdg_state_home:
        return Path(xdg_state_home) / APP_NAME.lower()
    return Path.home() / ".local" / "state" / APP_NAME.lower()


def _resolve_windows_workspace_root() -> Path:
    documents_root = _resolve_windows_documents_root()
    return documents_root / WINDOWS_DATA_DIRNAME


def _resolve_windows_portable_workspace_root() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    executable_dir = _resolve_executable_dir()
    if _is_windows_protected_install_root(executable_dir):
        return None
    return executable_dir / "workspace"


def _resolve_windows_configured_workspace_root() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    executable_dir = _resolve_executable_dir()
    config_path = executable_dir / WORKSPACE_ROOT_CONFIG_FILENAME
    if not config_path.exists():
        return None
    raw = config_path.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return None
    configured = Path(raw).expanduser()
    if not configured.is_absolute():
        configured = executable_dir / configured
    return configured.resolve()


def _resolve_windows_documents_root() -> Path:
    for env_name in ("MAINTENANCETOOL_DOCUMENTS_ROOT", "USERPROFILE"):
        env_value = os.getenv(env_name)
        if env_value:
            candidate = Path(env_value).expanduser()
            if env_name == "USERPROFILE":
                return candidate / "Documents"
            return candidate
    return Path.home() / "Documents"


def _is_windows_protected_install_root(path: Path) -> bool:
    normalized = path.resolve()
    for root in WINDOWS_PROTECTED_INSTALL_ROOTS:
        try:
            normalized.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _resolve_executable_dir() -> Path:
    return Path(sys.executable).resolve().parent


def _bootstrap_config_templates(config_dir: Path) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    template_dir = get_packaged_template_dir()
    if template_dir is None:
        return
    for template_path in template_dir.glob("*.json"):
        destination = config_dir / template_path.name
        if destination.exists():
            continue
        shutil.copy2(template_path, destination)
