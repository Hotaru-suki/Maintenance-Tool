from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from maintenancetool.models.schemas import PendingState, PendingSummary


def load_pending_state(path: Path) -> PendingState | None:
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return None
    if raw == "[]":
        return None
    return PendingState.model_validate_json(raw)


def write_pending_state(path: Path, state: PendingState) -> None:
    state_with_summary = state.model_copy(update={"summary": build_pending_summary(state)})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state_with_summary.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_pending_summary(state: PendingState) -> PendingSummary:
    by_action = Counter(item.suggestedAction for item in state.suggestions)
    by_category = Counter(item.category or "uncategorized" for item in state.suggestions)
    by_hit_rule = Counter(item.hitRule or "unknown" for item in state.suggestions)
    return PendingSummary(
        totalSuggestions=len(state.suggestions),
        byAction=dict(sorted(by_action.items())),
        byCategory=dict(sorted(by_category.items())),
        byHitRule=dict(sorted(by_hit_rule.items())),
    )
