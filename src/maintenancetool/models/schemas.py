from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


ScopeName = Literal["windows", "wsl"]
ScopeHint = Literal["windows", "wsl", "auto"]
DeleteMode = Literal["contents", "directory"]
TargetSource = Literal["manual", "learned"]
PendingAction = Literal["addFixedTarget", "retireFixedTarget"]
RiskLevel = Literal["low", "medium", "high"]


class FixedTarget(BaseModel):
    id: str | None = Field(default=None, min_length=1)
    path: str = Field(min_length=1)
    scopeHint: ScopeHint = "auto"
    enabled: bool = True
    depth: int = Field(default=2, ge=0)
    deleteMode: DeleteMode = "contents"
    source: TargetSource = "manual"
    category: str | None = None
    note: str | None = None
    createdAt: str | None = None
    updatedAt: str | None = None
    retired: bool = False
    priority: int | None = None


class DenyRule(BaseModel):
    id: str | None = Field(default=None, min_length=1)
    path: str = Field(min_length=1)
    enabled: bool = True
    reason: str = Field(default="protected path", min_length=1)
    scopeHint: ScopeHint = "auto"
    source: Literal["system", "user"] = "user"
    createdAt: str | None = None
    updatedAt: str | None = None


class ScopePolicy(BaseModel):
    defaultDepth: int | None = Field(default=None, ge=0)
    maxDepth: int | None = Field(default=None, ge=0)
    minBytes: int | None = Field(default=None, ge=0)
    topN: int | None = Field(default=None, ge=1)


class PathOverride(BaseModel):
    path: str = Field(min_length=1)
    scopeHint: ScopeHint = "auto"
    depth: int | None = Field(default=None, ge=0)
    maxDepth: int | None = Field(default=None, ge=0)
    minBytes: int | None = Field(default=None, ge=0)
    topN: int | None = Field(default=None, ge=1)
    category: str | None = None


class DiscoverConfig(BaseModel):
    defaultDepth: int = Field(default=2, ge=0)
    maxDepth: int = Field(default=3, ge=0)
    topN: int = Field(default=20, ge=1)
    minBytes: int = Field(default=1, ge=0)
    scopePolicies: dict[str, ScopePolicy] = Field(default_factory=dict)
    pathOverrides: list[PathOverride] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_depths(self) -> "DiscoverConfig":
        if self.maxDepth < self.defaultDepth:
            raise ValueError("discover.maxDepth must be >= discover.defaultDepth")
        return self


class NewItemPolicy(BaseModel):
    minBytes: int = Field(default=1, ge=0)
    promoteNewPaths: bool = True


class ChangePolicy(BaseModel):
    sizeDeltaBytes: int = Field(default=1024 * 1024, ge=0)
    sizeDeltaRatio: float = Field(default=0.25, ge=0)


class StalePolicy(BaseModel):
    missingCountThreshold: int = Field(default=2, ge=1)
    lastSeenAgeDays: int | None = Field(default=None, ge=1)
    suggestOnly: bool = True


class GroupingPolicy(BaseModel):
    groupBy: list[Literal["root", "category", "scope"]] = Field(
        default_factory=lambda: ["scope"]
    )


class SafetyRoot(BaseModel):
    path: str = Field(min_length=1)
    scopeHint: ScopeHint = "auto"
    enabled: bool = True


class SafetyPolicy(BaseModel):
    refuseSymlinks: bool = True
    requireManualConfirmForLearnedTargets: bool = True
    requireManualConfirmAboveBytes: int = Field(default=512 * 1024 * 1024, ge=0)
    maxItemsPerRun: int = Field(default=100, ge=1)
    maxBytesPerRun: int = Field(default=10 * 1024 * 1024 * 1024, ge=1)
    allowedRoots: list[SafetyRoot] = Field(default_factory=list)


class LearningConfig(BaseModel):
    newItemPolicy: NewItemPolicy = Field(default_factory=NewItemPolicy)
    changePolicy: ChangePolicy = Field(default_factory=ChangePolicy)
    stalePolicy: StalePolicy = Field(default_factory=StalePolicy)
    groupingPolicy: GroupingPolicy = Field(default_factory=GroupingPolicy)
    safetyPolicy: SafetyPolicy = Field(default_factory=SafetyPolicy)


class SnapshotEntry(BaseModel):
    path: str
    scope: ScopeName
    sizeBytes: int = Field(ge=0)
    entryType: Literal["directory", "file"] = "directory"
    collectedAt: str
    category: str | None = None
    hitRule: str | None = None
    hitRuleReason: str | None = None
    depth: int = Field(default=0, ge=0)
    sourceRootId: str | None = None


class PendingSuggestion(BaseModel):
    id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    scope: ScopeName
    suggestedAction: PendingAction
    reason: str = Field(min_length=1)
    category: str | None = None
    hitRule: str | None = None
    hitRuleReason: str | None = None
    sizeBytes: int | None = Field(default=None, ge=0)
    derivedFrom: str | None = None
    createdAt: str


class SafetyDecision(BaseModel):
    allow_scan: bool
    allow_promote: bool
    allow_delete: bool
    reason: str
    risk_level: RiskLevel
    requires_manual_confirm: bool


class SnapshotState(BaseModel):
    version: int = 1
    collectedAt: str
    entries: list[SnapshotEntry] = Field(default_factory=list)
    missingCounts: dict[str, int] = Field(default_factory=dict)
    lastSeenAt: dict[str, str] = Field(default_factory=dict)


class PendingSummary(BaseModel):
    totalSuggestions: int = 0
    byAction: dict[str, int] = Field(default_factory=dict)
    byCategory: dict[str, int] = Field(default_factory=dict)
    byHitRule: dict[str, int] = Field(default_factory=dict)


class PendingState(BaseModel):
    version: int = 1
    createdAt: str
    summary: PendingSummary = Field(default_factory=PendingSummary)
    suggestions: list[PendingSuggestion] = Field(default_factory=list)


class LearningDecisionEntry(BaseModel):
    id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    scope: ScopeName
    suggestedAction: PendingAction
    decision: Literal["accepted", "rejected"]
    category: str | None = None
    hitRule: str | None = None
    hitRuleReason: str | None = None
    derivedFrom: str | None = None
    lastReason: str | None = None
    createdAt: str
    updatedAt: str


class LearningDecisionSummary(BaseModel):
    totalDecisions: int = 0
    acceptedCount: int = 0
    rejectedCount: int = 0
    byCategory: dict[str, int] = Field(default_factory=dict)
    byHitRule: dict[str, int] = Field(default_factory=dict)


class LearningDecisionState(BaseModel):
    version: int = 1
    updatedAt: str
    summary: LearningDecisionSummary = Field(default_factory=LearningDecisionSummary)
    decisions: list[LearningDecisionEntry] = Field(default_factory=list)


class CleanupPlanItem(BaseModel):
    targetId: str
    path: str
    scope: ScopeName
    deleteMode: DeleteMode
    category: str | None = None
    sizeBytes: int = Field(ge=0)
    allowed: bool
    reason: str
    riskLevel: RiskLevel
    requiresManualConfirm: bool
    action: Literal["skip", "dry-run", "quarantine", "delete"]


class CleanupPlan(BaseModel):
    mode: Literal["dry-run", "quarantine", "delete"]
    createdAt: str
    items: list[CleanupPlanItem] = Field(default_factory=list)


class CleanupExecutionItem(BaseModel):
    targetId: str
    path: str
    outcome: Literal["applied", "skipped", "failed"]
    detail: str
    quarantinePath: str | None = None
    quarantineRecordId: str | None = None


class CleanupExecutionResult(BaseModel):
    mode: Literal["quarantine", "delete"]
    createdAt: str
    items: list[CleanupExecutionItem] = Field(default_factory=list)


class QuarantineRecord(BaseModel):
    version: int = 1
    recordId: str = Field(min_length=1)
    targetId: str = Field(min_length=1)
    sourcePath: str = Field(min_length=1)
    sourceScope: ScopeName
    deleteMode: DeleteMode
    category: str | None = None
    sizeBytes: int = Field(default=0, ge=0)
    sourceName: str = Field(min_length=1)
    quarantinedAt: str
    status: Literal["active", "restored"] = "active"
    restoredAt: str | None = None


class RestoreExecutionItem(BaseModel):
    recordId: str
    sourcePath: str
    outcome: Literal["applied", "skipped", "failed"]
    detail: str
    quarantinePath: str | None = None


class RestoreExecutionResult(BaseModel):
    createdAt: str
    items: list[RestoreExecutionItem] = Field(default_factory=list)
