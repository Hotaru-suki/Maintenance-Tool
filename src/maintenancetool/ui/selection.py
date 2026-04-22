from __future__ import annotations


def parse_selection(text: str, max_index: int) -> set[int]:
    raw = text.strip().lower()
    if raw in {"", "n"}:
        return set()
    if raw == "a":
        return set(range(1, max_index + 1))
    if raw == "q":
        raise ValueError("cancelled")

    selected: set[int] = set()
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if start > end:
                raise ValueError("invalid range")
            for value in range(start, end + 1):
                _validate_index(value, max_index)
                selected.add(value)
            continue
        value = int(token)
        _validate_index(value, max_index)
        selected.add(value)
    return selected


def _validate_index(value: int, max_index: int) -> None:
    if value < 1 or value > max_index:
        raise ValueError(f"selection index out of range: {value}")
