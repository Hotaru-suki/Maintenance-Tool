from __future__ import annotations

import os
import re
from typing import Any


WINDOWS_ENV_RE = re.compile(r"%([^%]+)%")


def expand_config_path(value: str) -> str:
    expanded = WINDOWS_ENV_RE.sub(_replace_windows_env_var, value)
    expanded = os.path.expandvars(expanded)
    expanded = os.path.expanduser(expanded)
    return expanded


def _replace_windows_env_var(match: re.Match[str]) -> str:
    name = match.group(1)
    return os.getenv(name, match.group(0))


def expand_path_field(item: dict[str, Any], field_name: str = "path") -> dict[str, Any]:
    current = dict(item)
    path_value = current.get(field_name)
    if isinstance(path_value, str) and path_value.strip():
        current[field_name] = expand_config_path(path_value)
    return current


def expand_allowed_roots(raw: dict[str, Any]) -> dict[str, Any]:
    current = dict(raw)
    safety_policy = current.get("safetyPolicy")
    if not isinstance(safety_policy, dict):
        return current

    allowed_roots = safety_policy.get("allowedRoots")
    if not isinstance(allowed_roots, list):
        return current

    current_safety_policy = dict(safety_policy)
    current_safety_policy["allowedRoots"] = [
        expand_path_field(item)
        if isinstance(item, dict)
        else item
        for item in allowed_roots
    ]
    current["safetyPolicy"] = current_safety_policy
    return current
