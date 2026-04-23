from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from maintenancetool.models.schemas import (
    CleanupExecutionResult,
    CleanupPlan,
    DiscoverProgress,
    PendingState,
    PendingSuggestion,
    QuarantineRecord,
    RestoreExecutionResult,
    SnapshotEntry,
    FixedTarget,
)


@dataclass(slots=True)
class AnalyzeServiceResult:
    configs: dict[str, Any]
    snapshot_path: Path
    pending_path: Path
    entries: list[SnapshotEntry]
    suggestions: list[PendingSuggestion]
    discover_mode: str = "full"
    discover_roots: list[tuple[str, str]] = field(default_factory=list)
    excluded_names: list[str] = field(default_factory=list)
    progress: list[DiscoverProgress] = field(default_factory=list)
    initial_discovery_ready: bool = False


@dataclass(slots=True)
class ReviewPendingServiceResult:
    pending_state: PendingState | None
    accepted: list[PendingSuggestion] = field(default_factory=list)
    rejected: list[PendingSuggestion] = field(default_factory=list)
    remaining: list[PendingSuggestion] = field(default_factory=list)
    fixed_targets_path: Path | None = None
    review_targets_path: Path | None = None
    deny_rules_path: Path | None = None
    pending_path: Path | None = None


@dataclass(slots=True)
class ReviewPromotionServiceResult:
    fixed_targets_path: Path
    review_targets_path: Path
    promoted: list[FixedTarget] = field(default_factory=list)
    remaining_review_targets: list[FixedTarget] = field(default_factory=list)


@dataclass(slots=True)
class ConfigCheckServiceResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    files: list[dict[str, object]] = field(default_factory=list)
    summary: dict[str, object] | None = None


@dataclass(slots=True)
class CleanupServiceResult:
    plan: CleanupPlan
    report_path: Path
    execution: CleanupExecutionResult | None = None
    execution_report_path: Path | None = None


@dataclass(slots=True)
class FeedbackServiceResult:
    issue_url: str
    email_url: str
    subject: str
    diagnostics: dict[str, object]


@dataclass(slots=True)
class RestoreQuarantineServiceResult:
    records: list[QuarantineRecord] = field(default_factory=list)
    execution: RestoreExecutionResult | None = None
    report_path: Path | None = None
