from maintenancetool.cli.dev import app
from tests.helpers.cli import runner
from tests.helpers.configuration import write_standard_config
from tests.helpers.runtime_workspace import invoke_runtime_command


def test_feedback_command_outputs_issue_link_with_email_fallback(runtime_workspace) -> None:
    write_standard_config(runtime_workspace.config_dir, fixed_targets=[])
    (runtime_workspace.state_dir / "lastSnapshot.json").write_text(
        '{"version":1,"collectedAt":"2026-01-01T00:00:00Z","entries":[{"path":"C:\\\\Temp\\\\Cache","scope":"windows","sizeBytes":128,"entryType":"directory","collectedAt":"2026-01-01T00:00:00Z","category":"cache","hitRule":"name-browser-cache","hitRuleReason":"matched cache directory name","depth":1,"sourceRootId":"C:\\\\Temp"}],"missingCounts":{},"lastSeenAt":{}}',
        encoding="utf-8",
    )
    (runtime_workspace.state_dir / "pending.json").write_text(
        '{"version":1,"createdAt":"2026-01-01T00:00:00Z","summary":{"totalSuggestions":1,"byAction":{"addFixedTarget":1},"byCategory":{"cache":1},"byHitRule":{"name-browser-cache":1}},"suggestions":[{"id":"abc123","path":"C:\\\\Temp\\\\Cache","scope":"windows","suggestedAction":"addFixedTarget","reason":"new candidate discovered","category":"cache","hitRule":"name-browser-cache","hitRuleReason":"matched cache directory name","sizeBytes":128,"derivedFrom":"C:\\\\Temp","createdAt":"2026-01-01T00:00:00Z"}]}',
        encoding="utf-8",
    )
    (runtime_workspace.state_dir / "learningDecisions.json").write_text(
        '{"version":1,"updatedAt":"2026-01-01T00:00:00Z","summary":{"totalDecisions":0,"acceptedCount":0,"rejectedCount":0,"byCategory":{},"byHitRule":{}},"decisions":[]}',
        encoding="utf-8",
    )
    (runtime_workspace.report_dir / "cleanup-plan-dry-run.json").write_text('{"mode":"dry-run","createdAt":"2026-01-01T00:00:00Z","items":[]}', encoding="utf-8")

    result = invoke_runtime_command(
        runner,
        app,
        runtime_workspace,
        "feedback",
        "--category",
        "bug",
        "--title",
        "Menu issue",
        "--details",
        "Steps to reproduce go here",
        "--no-open-target",
        include_quarantine=False,
    )

    assert result.exit_code == 0
    assert "feedback_subject=MaintenanceTool [bug] Menu issue" in result.stdout
    assert "feedback_issue_url=https://github.com/Hotaru-suki/Maintenance-Tool/issues/new?" in result.stdout
    assert "feedback_email_url=mailto:siestakawaiis@gmail.com?" in result.stdout
    assert "feedback_channel=manual" in result.stdout
    assert "feedback_dispatched=" in result.stdout
