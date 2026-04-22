from __future__ import annotations

import platform
import sys
import urllib.parse
import webbrowser
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from maintenancetool import __version__
from maintenancetool.release import APP_ISSUE_NEW_URL, APP_SUPPORT_EMAIL
from maintenancetool.services.config import run_config_check_service
from maintenancetool.services.results import FeedbackServiceResult


def run_feedback_service(
    *,
    feedback_dir: Path,
    config_dir: Path | None,
    state_dir: Path | None,
    report_dir: Path | None,
    category: str,
    title: str,
    details: str,
    include_config: bool,
) -> FeedbackServiceResult:
    del feedback_dir, report_dir
    diagnostics = _build_diagnostics_payload(
        category=category,
        title=title,
        config_dir=config_dir,
        include_config=include_config,
        state_dir=state_dir,
    )
    subject = f"MaintenanceTool [{category.strip() or 'feedback'}] {title.strip()}"
    body = _build_feedback_body(details=details, diagnostics=diagnostics)
    issue_url = _build_issue_url(
        category=category,
        title=title,
        body=body,
    )
    email_query = urllib.parse.urlencode(
        {
            "subject": subject,
            "body": body,
        }
    )
    return FeedbackServiceResult(
        issue_url=issue_url,
        email_url=f"mailto:{APP_SUPPORT_EMAIL}?{email_query}",
        subject=subject,
        diagnostics=diagnostics,
    )


def dispatch_feedback(result: FeedbackServiceResult) -> tuple[str, bool]:
    if _open_url(result.issue_url):
        return ("issue", True)
    if _open_url(result.email_url):
        return ("email", True)
    return ("manual", False)


def _open_url(url: str) -> bool:
    try:
        return bool(webbrowser.open(url))
    except Exception:
        return False


def _build_diagnostics_payload(
    *,
    category: str,
    title: str,
    config_dir: Path | None,
    include_config: bool,
    state_dir: Path | None,
) -> dict[str, object]:
    config_check = None
    if config_dir is not None and config_dir.exists():
        config_result = run_config_check_service(config_dir)
        config_check = {
            "ok": config_result.ok,
            "errors": config_result.errors,
        }

    return {
        "tool": {
            "name": "MaintenanceTool",
            "version": __version__,
        },
        "feedback": {
            "category": category,
            "title": title,
            "includeConfig": include_config,
        },
        "runtime": {
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "pythonVersion": sys.version,
            "frozen": bool(getattr(sys, "frozen", False)),
            "executable": sys.executable,
        },
        "configCheck": config_check,
        "analyzeSummary": _build_analyze_summary(state_dir),
    }


def _build_analyze_summary(state_dir: Path | None) -> dict[str, object] | None:
    if state_dir is None or not state_dir.exists():
        return None

    pending_path = state_dir / "pending.json"
    snapshot_path = state_dir / "lastSnapshot.json"
    pending_data = _read_json_if_exists(pending_path)
    snapshot_data = _read_json_if_exists(snapshot_path)
    if pending_data is None and snapshot_data is None:
        return None

    suggestions = pending_data.get("suggestions", []) if isinstance(pending_data, dict) else []
    entries = snapshot_data.get("entries", []) if isinstance(snapshot_data, dict) else []
    by_hit_rule = Counter(
        item.get("hitRule") or "unknown"
        for item in suggestions
        if isinstance(item, dict)
    )
    by_category = Counter(
        item.get("category") or "uncategorized"
        for item in suggestions
        if isinstance(item, dict)
    )
    return {
        "snapshotEntries": len(entries) if isinstance(entries, list) else 0,
        "pendingSuggestions": len(suggestions) if isinstance(suggestions, list) else 0,
        "pendingByHitRule": dict(sorted(by_hit_rule.items())),
        "pendingByCategory": dict(sorted(by_category.items())),
        "snapshotPath": str(snapshot_path) if snapshot_path.exists() else None,
        "pendingPath": str(pending_path) if pending_path.exists() else None,
    }


def _read_json_if_exists(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        import json

        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _build_feedback_body(*, details: str, diagnostics: dict[str, object]) -> str:
    return "\n".join(
        [
            details.strip() or "(no details provided)",
            "",
            f"Version: {diagnostics['tool']['version']}",
            f"Platform: {diagnostics['runtime']['platform']}",
            f"System: {diagnostics['runtime']['system']} {diagnostics['runtime']['release']}",
            f"Python: {diagnostics['runtime']['pythonVersion']}",
            "",
            "Analyze summary:",
            str(diagnostics.get("analyzeSummary")),
        ]
    )


def _build_issue_url(*, category: str, title: str, body: str) -> str:
    issue_title = f"[{category.strip() or 'feedback'}] {title.strip()}".strip()
    query = urllib.parse.urlencode(
        {
            "title": issue_title,
            "body": body,
        }
    )
    return f"{APP_ISSUE_NEW_URL}?{query}"
