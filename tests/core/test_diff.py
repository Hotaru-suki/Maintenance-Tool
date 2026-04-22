from datetime import datetime, timezone

from maintenancetool.core.diff import (
    build_pending_suggestions,
    compute_last_seen_at,
    compute_missing_counts,
)
from maintenancetool.models.schemas import (
    FixedTarget,
    LearningConfig,
    SnapshotEntry,
    SnapshotState,
)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_build_pending_suggestions_for_new_candidate() -> None:
    learning = LearningConfig()
    fixed_targets = [
        FixedTarget(id="known", path="/sandbox/cache"),
    ]
    current_entries = [
        SnapshotEntry(
            path="/sandbox/cache",
            scope="wsl",
            sizeBytes=10,
            collectedAt=iso_now(),
            sourceRootId="known",
        ),
        SnapshotEntry(
            path="/sandbox/new-candidate",
            scope="wsl",
            sizeBytes=2048,
            collectedAt=iso_now(),
            sourceRootId="/sandbox",
        ),
    ]

    suggestions = build_pending_suggestions(
        fixed_targets=fixed_targets,
        current_entries=current_entries,
        previous_state=None,
        learning_config=learning,
        missing_counts={"known": 0},
    )

    assert len(suggestions) == 1
    assert suggestions[0].suggestedAction == "addFixedTarget"
    assert suggestions[0].path == "/sandbox/new-candidate"
    assert "new candidate discovered under /sandbox" in suggestions[0].reason


def test_compute_missing_counts_and_stale_suggestion() -> None:
    fixed_targets = [FixedTarget(id="gone", path="/sandbox/gone")]
    previous_state = SnapshotState(
        collectedAt=iso_now(),
        entries=[],
        missingCounts={"gone": 1},
        lastSeenAt={"gone": "2026-04-19T00:00:00+00:00"},
    )

    missing_counts = compute_missing_counts(
        fixed_targets=fixed_targets,
        current_entries=[],
        previous_state=previous_state,
    )
    suggestions = build_pending_suggestions(
        fixed_targets=fixed_targets,
        current_entries=[],
        previous_state=previous_state,
        learning_config=LearningConfig(),
        missing_counts=missing_counts,
    )

    assert missing_counts["gone"] == 2
    assert len(suggestions) == 1
    assert suggestions[0].suggestedAction == "retireFixedTarget"
    assert "target missing for 2 analyze runs" in suggestions[0].reason


def test_build_pending_suggestions_respects_promote_new_paths_flag() -> None:
    learning = LearningConfig(newItemPolicy={"minBytes": 1, "promoteNewPaths": False})
    suggestions = build_pending_suggestions(
        fixed_targets=[],
        current_entries=[
            SnapshotEntry(
                path="/sandbox/new-candidate",
                scope="wsl",
                sizeBytes=2048,
                collectedAt=iso_now(),
                sourceRootId="/sandbox",
            )
        ],
        previous_state=None,
        learning_config=learning,
        missing_counts={},
    )

    assert suggestions == []


def test_build_pending_suggestions_respects_grouping_policy_scope_and_category() -> None:
    learning = LearningConfig(groupingPolicy={"groupBy": ["scope", "category"]})
    suggestions = build_pending_suggestions(
        fixed_targets=[],
        current_entries=[
            SnapshotEntry(
                path="/sandbox/a",
                scope="wsl",
                sizeBytes=1024,
                collectedAt=iso_now(),
                category="cache",
                sourceRootId="/sandbox",
            ),
            SnapshotEntry(
                path="/sandbox/b",
                scope="wsl",
                sizeBytes=4096,
                collectedAt=iso_now(),
                category="cache",
                sourceRootId="/sandbox",
            ),
        ],
        previous_state=None,
        learning_config=learning,
        missing_counts={},
    )

    assert len(suggestions) == 1
    assert suggestions[0].path == "/sandbox/b"
    assert "grouped 2 similar candidate(s)" in suggestions[0].reason


def test_build_pending_suggestions_respects_last_seen_age_days() -> None:
    learning = LearningConfig(stalePolicy={"missingCountThreshold": 2, "lastSeenAgeDays": 3, "suggestOnly": True})
    previous_state = SnapshotState(
        collectedAt="2026-04-21T00:00:00+00:00",
        entries=[],
        missingCounts={"gone": 1},
        lastSeenAt={"gone": "2026-04-20T00:00:00+00:00"},
    )

    suggestions = build_pending_suggestions(
        fixed_targets=[FixedTarget(id="gone", path="/sandbox/gone")],
        current_entries=[],
        previous_state=previous_state,
        learning_config=learning,
        missing_counts={"gone": 2},
    )

    assert suggestions == []


def test_build_pending_suggestions_reports_size_change_reason() -> None:
    previous_state = SnapshotState(
        collectedAt="2026-04-20T00:00:00+00:00",
        entries=[
            SnapshotEntry(
                path="/sandbox/cache",
                scope="wsl",
                sizeBytes=1024,
                collectedAt="2026-04-20T00:00:00+00:00",
                sourceRootId="/sandbox",
            )
        ],
        missingCounts={},
        lastSeenAt={},
    )
    suggestions = build_pending_suggestions(
        fixed_targets=[],
        current_entries=[
            SnapshotEntry(
                path="/sandbox/cache",
                scope="wsl",
                sizeBytes=4096,
                collectedAt="2026-04-21T00:00:00+00:00",
                sourceRootId="/sandbox",
            )
        ],
        previous_state=previous_state,
        learning_config=LearningConfig(
            changePolicy={"sizeDeltaBytes": 10, "sizeDeltaRatio": 0.1}
        ),
        missing_counts={},
    )

    assert len(suggestions) == 1
    assert "from 1024 to 4096 bytes" in suggestions[0].reason


def test_build_pending_suggestions_reports_stale_age_context() -> None:
    suggestions = build_pending_suggestions(
        fixed_targets=[FixedTarget(id="gone", path="/sandbox/gone")],
        current_entries=[],
        previous_state=SnapshotState(
            collectedAt="2026-04-21T00:00:00+00:00",
            entries=[],
            missingCounts={"gone": 1},
            lastSeenAt={"gone": "2026-04-15T00:00:00+00:00"},
        ),
        learning_config=LearningConfig(
            stalePolicy={"missingCountThreshold": 2, "lastSeenAgeDays": 3, "suggestOnly": True}
        ),
        missing_counts={"gone": 2},
    )

    assert len(suggestions) == 1
    assert "last seen " in suggestions[0].reason
    assert "day(s) ago" in suggestions[0].reason


def test_compute_last_seen_at_tracks_seen_and_missing_targets() -> None:
    fixed_targets = [
        FixedTarget(id="seen", path="/sandbox/seen"),
        FixedTarget(id="missing", path="/sandbox/missing"),
    ]
    previous_state = SnapshotState(
        collectedAt="2026-04-20T00:00:00+00:00",
        entries=[],
        missingCounts={"missing": 1},
        lastSeenAt={"missing": "2026-04-18T00:00:00+00:00"},
    )
    current_entries = [
        SnapshotEntry(
            path="/sandbox/seen",
            scope="wsl",
            sizeBytes=1,
            collectedAt="2026-04-21T00:00:00+00:00",
            sourceRootId="seen",
        )
    ]

    last_seen_at = compute_last_seen_at(
        fixed_targets,
        current_entries,
        previous_state,
        collected_at="2026-04-21T00:00:00+00:00",
    )

    assert last_seen_at["seen"] == "2026-04-21T00:00:00+00:00"
    assert last_seen_at["missing"] == "2026-04-18T00:00:00+00:00"
