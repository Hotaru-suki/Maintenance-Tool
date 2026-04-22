from __future__ import annotations

from itertools import product

from maintenancetool.ui.workflow_guidance import (
    advanced_dryrun_next_step,
    advanced_quarantine_next_step,
    analyze_next_step,
    delete_safe_next_step,
    dryrun_next_step,
    restore_next_step,
    status_next_step,
)


def test_status_next_step_cartesian_matrix() -> None:
    for has_pending, has_learning in product((False, True), repeat=2):
        step = status_next_step(has_pending=has_pending, has_learning=has_learning)
        if has_pending:
            assert step.primary == "/review"
            assert step.aliases == ("/r", "/rev")
        elif has_learning:
            assert step.primary == "/dryrun"
            assert step.aliases == ("/d", "/dr")
        else:
            assert step.primary == "/analyze"
            assert step.aliases == ("/a", "/an")


def test_analyze_next_step_cartesian_matrix_with_pruning() -> None:
    for has_suggestions, reviewed_now in product((False, True), repeat=2):
        if reviewed_now and not has_suggestions:
            continue

        step = analyze_next_step(has_suggestions=has_suggestions, reviewed_now=reviewed_now)
        if has_suggestions and reviewed_now:
            assert step.primary == "/dryrun"
            assert "Review is complete" in step.note
        elif has_suggestions:
            assert step.primary == "/review"
            assert "Review them before cleanup" in step.note
        else:
            assert step.primary == "/dryrun"
            assert "No pending suggestions" in step.note


def test_dryrun_next_step_cartesian_matrix_with_pruning() -> None:
    for has_safe_candidates, has_any_candidates in product((False, True), repeat=2):
        if has_safe_candidates and not has_any_candidates:
            continue

        step = dryrun_next_step(
            has_safe_candidates=has_safe_candidates,
            has_any_candidates=has_any_candidates,
        )
        if has_safe_candidates:
            assert step.primary == "/delete-safe"
            assert step.alternate == "/report"
        elif has_any_candidates:
            assert step.primary == "/report"
            assert step.alternate == "/advanced-dryrun"
        else:
            assert step.primary == "/analyze"
            assert step.alternate == "/report"


def test_restore_next_step_binary_matrix() -> None:
    for has_records in (False, True):
        step = restore_next_step(has_records=has_records)
        if has_records:
            assert step.primary == "/report"
            assert step.alternate == "/dryrun"
        else:
            assert step.primary == "/dryrun"
            assert step.alternate == "/report"


def test_delete_safe_next_step_binary_matrix() -> None:
    for has_safe_candidates in (False, True):
        step = delete_safe_next_step(has_safe_candidates=has_safe_candidates)
        if has_safe_candidates:
            assert step.primary == "/report"
            assert step.alternate == "/restore"
        else:
            assert step.primary == "/dryrun"
            assert step.alternate == "/report"


def test_advanced_dryrun_next_step_binary_matrix() -> None:
    for has_allowed_candidates in (False, True):
        step = advanced_dryrun_next_step(has_allowed_candidates=has_allowed_candidates)
        if has_allowed_candidates:
            assert step.primary == "/advanced-quarantine"
            assert step.alternate == "/report"
        else:
            assert step.primary == "/report"
            assert step.alternate == "/analyze"


def test_advanced_quarantine_next_step_binary_matrix() -> None:
    for has_allowed_candidates in (False, True):
        step = advanced_quarantine_next_step(has_allowed_candidates=has_allowed_candidates)
        if has_allowed_candidates:
            assert step.primary == "/restore"
            assert step.alternate == "/report"
        else:
            assert step.primary == "/report"
            assert step.alternate == "/advanced-dryrun"
