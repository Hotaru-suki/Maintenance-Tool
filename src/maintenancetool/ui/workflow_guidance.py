from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NextStepSpec:
    primary: str
    aliases: tuple[str, ...]
    note: str
    alternate: str | None = None
    alternate_aliases: tuple[str, ...] = ()


def status_next_step(*, has_pending: bool, has_learning: bool) -> NextStepSpec:
    if has_pending:
        return NextStepSpec(
            primary="/review",
            aliases=("/r", "/rev"),
            note="Pending learning suggestions already exist. Review them before cleanup.",
        )
    if has_learning:
        return NextStepSpec(
            primary="/dryrun",
            aliases=("/d", "/dr"),
            note="Learning state exists. Preview the cleanup plan before any action.",
        )
    return NextStepSpec(
        primary="/analyze",
        aliases=("/a", "/an"),
        note="No pending state yet. Start by scanning discover roots.",
    )


def analyze_next_step(*, has_suggestions: bool, reviewed_now: bool) -> NextStepSpec:
    if has_suggestions and reviewed_now:
        return NextStepSpec(
            primary="/dryrun",
            aliases=("/d", "/dr"),
            note="Review is complete. Preview the cleanup plan next.",
        )
    if has_suggestions:
        return NextStepSpec(
            primary="/review",
            aliases=("/r", "/rev"),
            note="Pending suggestions were found. Review them before cleanup.",
        )
    return NextStepSpec(
        primary="/dryrun",
        aliases=("/d", "/dr"),
        note="No pending suggestions were generated. You can preview the current cleanup plan.",
    )


def dryrun_next_step(*, has_safe_candidates: bool, has_any_candidates: bool) -> NextStepSpec:
    if has_safe_candidates:
        return NextStepSpec(
            primary="/delete-safe",
            aliases=("/del", "/ds"),
            note="Low-risk cleanup targets are available. Continue to safe delete or inspect /report.",
            alternate="/report",
            alternate_aliases=("/rep",),
        )
    if has_any_candidates:
        return NextStepSpec(
            primary="/report",
            aliases=("/rep",),
            note="Candidates exist but none are immediately safe-delete. Inspect reports before changing config or using advanced cleanup.",
            alternate="/advanced-dryrun",
            alternate_aliases=("/adr",),
        )
    return NextStepSpec(
        primary="/analyze",
        aliases=("/a", "/an"),
        note="No cleanup candidates were found. Refresh discovery state or adjust config and analyze again.",
        alternate="/report",
        alternate_aliases=("/rep",),
    )


def restore_next_step(*, has_records: bool) -> NextStepSpec:
    if has_records:
        return NextStepSpec(
            primary="/report",
            aliases=("/rep",),
            note="Active quarantine records are available. Inspect restore reports or return to cleanup preview if you need another pass.",
            alternate="/dryrun",
            alternate_aliases=("/d", "/dr"),
        )
    return NextStepSpec(
        primary="/dryrun",
        aliases=("/d", "/dr"),
        note="No active quarantine records were found. Return to cleanup preview to generate the next action set.",
        alternate="/report",
        alternate_aliases=("/rep",),
    )


def delete_safe_next_step(*, has_safe_candidates: bool) -> NextStepSpec:
    if has_safe_candidates:
        return NextStepSpec(
            primary="/report",
            aliases=("/rep",),
            note="Inspect the current reports, or run /dryrun again after config changes.",
            alternate="/restore",
            alternate_aliases=("/res", "/restore-quarantine"),
        )
    return NextStepSpec(
        primary="/dryrun",
        aliases=("/d", "/dr"),
        note="No immediately safe delete candidates were available. Re-check the preview or inspect reports.",
        alternate="/report",
        alternate_aliases=("/rep",),
    )


def advanced_dryrun_next_step(*, has_allowed_candidates: bool) -> NextStepSpec:
    if has_allowed_candidates:
        return NextStepSpec(
            primary="/advanced-quarantine",
            aliases=("/aq",),
            note="Advanced preview is ready. Quarantine is the next controlled action.",
            alternate="/report",
            alternate_aliases=("/rep",),
        )
    return NextStepSpec(
        primary="/report",
        aliases=("/rep",),
        note="No allowed advanced candidates were found. Inspect the generated reports before changing policy or config.",
        alternate="/analyze",
        alternate_aliases=("/a", "/an"),
    )


def advanced_quarantine_next_step(*, has_allowed_candidates: bool) -> NextStepSpec:
    if has_allowed_candidates:
        return NextStepSpec(
            primary="/restore",
            aliases=("/res", "/restore-quarantine"),
            note="If items are later quarantined, restore remains the rollback path.",
            alternate="/report",
            alternate_aliases=("/rep",),
        )
    return NextStepSpec(
        primary="/report",
        aliases=("/rep",),
        note="No allowed quarantine candidates were produced. Inspect reports before attempting another advanced pass.",
        alternate="/advanced-dryrun",
        alternate_aliases=("/adr",),
    )
