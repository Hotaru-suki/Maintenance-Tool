from pathlib import Path

from maintenancetool.core.config_audit import audit_config_directory
from maintenancetool.services.config import run_config_check_service
from tests.helpers.configuration import write_json, write_standard_config


def test_audit_config_directory_marks_learning_driven_initial_profile(tmp_path: Path) -> None:
    write_standard_config(tmp_path, fixed_targets=[])

    audit = audit_config_directory(tmp_path)

    assert audit.summary is not None
    assert audit.summary.profile == "learning-driven-initial"


def test_audit_config_directory_marks_empty_template_when_strategy_files_are_empty(tmp_path: Path) -> None:
    write_json(tmp_path / "fixedTargets.json", [])
    write_json(tmp_path / "denyRules.json", [])
    write_json(tmp_path / "discover.config.json", {})
    write_json(tmp_path / "learning.config.json", {})

    audit = audit_config_directory(tmp_path)

    assert audit.summary is not None
    assert audit.summary.profile == "empty-template"


def test_config_check_reports_discover_root_and_hit_rule_summary(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    write_standard_config(tmp_path, fixed_targets=[])

    result = run_config_check_service(tmp_path)

    assert result.ok is True
    assert result.summary is not None
    assert result.summary["discover_root_source"] == "system-drive-fallback"
    assert result.summary["discover_root_count"] >= 1
    assert result.summary["hit_rules_total"] >= 1
